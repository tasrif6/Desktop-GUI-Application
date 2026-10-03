import calendar
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QObject,
    QAbstractTableModel,
    QModelIndex,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QStackedWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QGroupBox,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QFileDialog,
    QHeaderView,
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QScrollArea,
    QToolButton,
    QSizePolicy,
)
from PySide6.QtGui import QIcon, QFont

import numpy as np
import pandas as pd

from app.config.settings import DEFAULT_EXCLUSION_RULES, DEFAULT_REBATE_RULES, GROUP_FILE
from app.models.config import CalculationConfig, ExclusionRules, RebateRule
from app.services.workflow import Workflow
from app.services.exporter import export_excluded, export_results
from app.utils.dates import month_label

from app.gui.styles import MAIN_STYLESHEET
from app.gui.icons import get_vector_icon, create_badge_icon
from app.gui.widgets import (
    CustomTitleBar,
    StatCard,
    ConfigActionCard,
    QuickActionCard,
    ProgressStepper,
    ActivityLogWidget,
    ExclusionConfigDialog,
    RebateConfigDialog,
)


class DFModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._raw_df = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        self._filtered_df = self._raw_df
        self._filter_text = ""
        self._columns = []
        self._data = np.empty((0, 0), dtype=object)
        self._rebuild_cache()

    @property
    def df(self):
        return self._raw_df

    def _rebuild_cache(self):
        self._columns = [str(c) for c in self._filtered_df.columns]
        self._data = self._filtered_df.to_numpy()

    def rowCount(self, p=QModelIndex()):
        return 0 if p.isValid() else len(self._data)

    def columnCount(self, p=QModelIndex()):
        return 0 if p.isValid() else len(self._columns)

    ID_COLUMNS = {"PARTY_ID", "party_number", "customer_id", "Group_id", "item_code"}
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        v = self._data[index.row(), index.column()]
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            col_name = self._columns[index.column()]
            if col_name in self.ID_COLUMNS:
                return str(int(v))
            return f"{v:,.2f}"
        return str(v)
    

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._columns[section] if section < len(self._columns) else ""
            return str(section + 1)
        return None

    def set_df(self, df):
        self.beginResetModel()
        self._raw_df = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        if self._filter_text:
            self._apply_filter(self._filter_text)
        else:
            self._filtered_df = self._raw_df
            self._rebuild_cache()
        self.endResetModel()

    def sort(self, column, order=Qt.AscendingOrder):
        if self._filtered_df.empty or column < 0 or column >= len(self._filtered_df.columns):
            return
        self.beginResetModel()
        col = self._filtered_df.columns[column]
        ascending = (order == Qt.AscendingOrder)
        self._filtered_df = self._filtered_df.sort_values(
            by=col,
            ascending=ascending,
            kind="mergesort"
        )
        self._rebuild_cache()
        self.endResetModel()

    def filter_text(self, text):
        text = text.strip()
        if text == self._filter_text:
            return
        self._filter_text = text
        self.beginResetModel()
        self._apply_filter(text)
        self.endResetModel()

    def _apply_filter(self, text):
        if not text or self._raw_df.empty:
            self._filtered_df = self._raw_df
        elif "PARTY_ID" in self._raw_df.columns:
            t = text.lower()
            self._filtered_df = self._raw_df[
                self._raw_df["PARTY_ID"].astype(str).str.lower().str.contains(t, regex=False, na=False)
            ]
        else:
            self._filtered_df = self._raw_df.iloc[0:0]
        self._rebuild_cache()


class Worker(QObject):
    progress = Signal(str)
    done = Signal(object, int, bool)
    error = Signal(str)

    def __init__(self, cfg, workflow, step, run_all=False):
        super().__init__()
        self.cfg = cfg
        self.workflow = workflow
        self.step = step
        self.run_all = run_all

    def run(self):
        try:
            print(f"[PartyLifting] WORKER START step={self.step}, run_all={self.run_all}, thread={threading.get_ident()}", flush=True)
            self.workflow.progress = self.progress.emit
            print("[PartyLifting] WORKFLOW CALL START", flush=True)
            result = self.workflow.run() if self.run_all else self.workflow.run_step(self.step)
            for key in ("party_lefting_raw", "party_lefting", "effective_stock_detail"):
                value = result.get(key)
                if isinstance(value, pd.DataFrame):
                    print(f"[PartyLifting] WORKER RESULT {key} shape={value.shape}", flush=True)
            print(f"[PartyLifting] WORKER DONE; emitting result on thread={threading.get_ident()}", flush=True)
            self.done.emit(result, self.step, self.run_all)
        except Exception as e:
            import traceback
            print(f"[PartyLifting] WORKER ERROR: {type(e).__name__}: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            self.error.emit(traceback.format_exc())


class ExportWorker(QObject):
    done = Signal(object)
    error = Signal(str)

    def __init__(self, data, year, month_label_text):
        super().__init__()
        self.data = data
        self.year = year
        self.month_label_text = month_label_text

    def run(self):
        try:
            self.done.emit(export_results(self.data, self.year, self.month_label_text))
        except Exception as error:
            self.error.emit(str(error))


class DataTab(QWidget):
    def __init__(self, title):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 16px;
            }
        """)
        h_lay = QHBoxLayout(header_card)
        h_lay.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #0f172a;")
        h_lay.addWidget(self.title_label)
        h_lay.addStretch()

        self.label = QLabel("0 rows")
        self.label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 500;")
        h_lay.addWidget(self.label)
        lay.addWidget(header_card)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search all columns...")
        self.search.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        lay.addWidget(self.search)

        self.model = DFModel()
        self.pending_df = None
        self.has_pending_data = False

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(150)
        self.search_timer.timeout.connect(lambda: self.model.filter_text(self.search.text()))
        self.search.textChanged.connect(self.search_timer.start)
        self.model.modelReset.connect(self._sync_row_count)
        lay.addWidget(self.table)

    def _sync_row_count(self):
        total = len(self.model._raw_df)
        current = self.model.rowCount()
        if self.model._filter_text:
            self.label.setText(f"{current:,} of {total:,} rows")
        else:
            self.label.setText(f"{current:,} rows")

    def set_data(self, df):
        self.pending_df = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        self.has_pending_data = True
        self.label.setText(f"{len(self.pending_df):,} rows")

    def load_pending_data(self):
        if self.has_pending_data:
            self.model.set_df(self.pending_df)
            self.pending_df = None
            self.has_pending_data = False


class RebateTab(QWidget):
    rules_changed = Signal(list)

    def __init__(self, default):
        super().__init__()
        self.rules = [dict(x) for x in default]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        top = QHBoxLayout()
        header = QLabel("Rebate Tiers & Configuration")
        header.setStyleSheet("font-size: 14px; font-weight: 700; color: #0f172a;")
        top.addWidget(header)
        top.addStretch()

        badd = QPushButton("+ Add Rule")
        badd.setStyleSheet("background-color: #1677ff; color: #ffffff; border-radius: 6px; padding: 6px 12px; font-weight: 600;")
        bdel = QPushButton("Delete Rule")
        bdel.setStyleSheet("background-color: #ffffff; color: #ef4444; border: 1px solid #fca5a5; border-radius: 6px; padding: 6px 12px;")
        bsave = QPushButton("Save Rules")
        bsave.setStyleSheet("background-color: #ffffff; color: #475569; border-radius: 1px solid #1677ff;border-radius: 6px; padding: 6px 12px;")
        breset = QPushButton("Reset Default")
        breset.setStyleSheet("background-color: #ffffff; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px;")

        for b in (badd, bdel, bsave, breset):
            top.addWidget(b)

        top_widget = QWidget()
        top_widget.setLayout(top)
        lay.addWidget(top_widget)
        self.rule_controls = top_widget
        top_widget.setVisible(False)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Minimum %", "Maximum %", "Rebate %"])
        self.table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.table)
        self.rule_table = self.table
        self.table.setVisible(False)

        self.results_title = QLabel("Calculated Rebate Results")
        self.results_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0f172a; margin-top: 8px;")
        lay.addWidget(self.results_title)
        self.results_title.setVisible(False)

        actions = QHBoxLayout()
        self.result_search = QLineEdit()
        self.result_search.setPlaceholderText("Search rebate results...")
        self.result_search.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px;")
        actions.addWidget(self.result_search)

        # self.maximize_button = QPushButton("Show Data Only")
        # self.maximize_button.setStyleSheet("background-color: #ffffff; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 14px;")
        # self.maximize_button.clicked.connect(self.toggle_data_only)
        # actions.addWidget(self.maximize_button)
        lay.addLayout(actions)

        self.result_view = QTableView()
        self.result_model = DFModel()
        self.result_view.setModel(self.result_model)
        self.result_view.setSortingEnabled(True)
        lay.addWidget(self.result_view)

        self.result_search_timer = QTimer(self)
        self.result_search_timer.setSingleShot(True)
        self.result_search_timer.setInterval(150)
        self.result_search_timer.timeout.connect(lambda: self.result_model.filter_text(self.result_search.text()))
        self.result_search.textChanged.connect(self.result_search_timer.start)

        self.pending_df = None
        self.has_pending_data = False

        badd.clicked.connect(self.add_row)
        bdel.clicked.connect(self.delete_row)
        bsave.clicked.connect(self.save)
        breset.clicked.connect(self.reset)
        self.reset()

    def set_results(self, df):
        self.pending_df = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        self.has_pending_data = True

    def load_pending_data(self):
        if self.has_pending_data:
            self.result_model.set_df(self.pending_df)
            self.pending_df = None
            self.has_pending_data = False

    def set_rules(self, rules):
        self.rules = [dict(rule) for rule in rules]

    def reset(self):
        self.rules = [dict(x) for x in DEFAULT_REBATE_RULES]
        self.render()

    def render(self):
        self.table.setRowCount(0)
        for r in self.rules:
            self.add_row(r)

    def add_row(self, r=None):
        i = self.table.rowCount()
        self.table.insertRow(i)
        vals = [
            ("" if r is None or r.get("min_percent") is None else r["min_percent"]),
            ("" if r is None or r.get("max_percent") is None else r["max_percent"]),
            (0 if r is None else r.get("rebate", 0)),
        ]
        for j, v in enumerate(vals):
            self.table.setItem(i, j, QTableWidgetItem(str(v)))

    def delete_row(self):
        rows = sorted({x.row() for x in self.table.selectedItems()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def save(self):
        rules = []
        try:
            for i in range(self.table.rowCount()):
                a = self.table.item(i, 0).text().strip()
                b = self.table.item(i, 1).text().strip()
                c = self.table.item(i, 2).text().strip()
                rules.append({
                    "min_percent": None if a == "" else float(a),
                    "max_percent": None if b == "" else float(b),
                    "rebate": float(c),
                })
            self.rules_changed.emit(rules)
            QMessageBox.information(self, "Rebate Rules", "Rules saved for the next run.")
        except Exception as e:
            QMessageBox.critical(self, "Invalid Rule", str(e))

    def get_rules(self):
        rules = []
        for i in range(self.table.rowCount()):
            a = self.table.item(i, 0).text().strip()
            b = self.table.item(i, 1).text().strip()
            c = self.table.item(i, 2).text().strip()
            rules.append(RebateRule(None if a == "" else float(a), None if b == "" else float(b), float(c)))
        return rules

    # def toggle_data_only(self):
    #     show_data_only = self.maximize_button.text() == "Show Data Only"
    #     self.rule_controls.setVisible(not show_data_only)
    #     self.rule_table.setVisible(not show_data_only)
    #     self.results_title.setVisible(not show_data_only)
    #     self.maximize_button.setText("Show Full View" if show_data_only else "Show Data Only")


class ExclusionTab(QWidget):
    rules_changed = Signal(object)

    def __init__(self, defaults):
        super().__init__()
        self.defaults = dict(defaults)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        form = QFormLayout()
        self.fields = {}
        specs = [
            ("negative_balance_threshold", "Negative-balance trigger", False),
            ("walton_stock_threshold_normal", "Walton minimum stock (normal)", False),
            ("marcel_stock_threshold_normal", "Marcel minimum stock (normal)", False),
            ("walton_stock_threshold_negative", "Walton minimum stock (negative mode)", False),
            ("marcel_stock_threshold_negative", "Marcel minimum stock (negative mode)", False),
            ("high_stock_multiplier", "High-stock multiplier", False),
        ]
        for key, label, _ in specs:
            e = QLineEdit(str(defaults[key]))
            self.fields[key] = e
            form.addRow(label, e)

        self.neg = QCheckBox("Use negative-balance mode")
        self.neg.setChecked(defaults["negative_balance_mode"])
        form.addRow(self.neg)

        self.high = QCheckBox("Apply high-stock-without-receiving exclusion")
        self.high.setChecked(defaults["apply_high_stock_rule"])
        form.addRow(self.high)

        form_widget = QWidget()
        form_widget.setLayout(form)
        lay.addWidget(form_widget)
        self.rule_form = form_widget
        form_widget.setVisible(False)

        buttons = QHBoxLayout()
        self.saveb = QPushButton("Save Exclusion Conditions")
        self.saveb.setStyleSheet("background-color: #ffffff; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 14px;")
        self.resetb = QPushButton("Reset Default")
        self.resetb.setStyleSheet("background-color: #ffffff; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 14px;")
        self.expb = QPushButton("Download Excluded Parties Excel")
        self.expb.setStyleSheet("background-color: #10b981; color: #ffffff; border-radius: 6px; padding: 6px 14px; font-weight: 600;")

        buttons.addWidget(self.saveb)
        buttons.addWidget(self.resetb)
        buttons.addWidget(self.expb)
        buttons.addStretch()

        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons)
        lay.addWidget(buttons_widget)
        self.rule_buttons = buttons_widget
        buttons_widget.setVisible(False)

        self.summary = QLabel("Run the calculation to populate excluded parties.")
        self.summary.setStyleSheet("font-weight: 600; color: #64748b;")
        lay.addWidget(self.summary)

        actions = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search excluded parties...")
        self.search.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px;")
        actions.addWidget(self.search)

        # self.maximize_button = QPushButton("Show Data Only")
        # self.maximize_button.setStyleSheet("background-color: #ffffff; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 14px;")
        # self.maximize_button.clicked.connect(self.toggle_data_only)
        # actions.addWidget(self.maximize_button)
        lay.addLayout(actions)

        self.table = QTableView()
        self.model = DFModel()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        lay.addWidget(self.table)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(150)
        self.search_timer.timeout.connect(lambda: self.model.filter_text(self.search.text()))
        self.search.textChanged.connect(self.search_timer.start)

        self.saveb.clicked.connect(self.save)
        self.resetb.clicked.connect(self.reset)
        self.expb.clicked.connect(self.download)
        self.excluded = pd.DataFrame()
        self.pending_df = None
        self.has_pending_data = False

    def reset(self):
        for k, e in self.fields.items():
            e.setText(str(self.defaults[k]))
        self.neg.setChecked(self.defaults["negative_balance_mode"])
        self.high.setChecked(self.defaults["apply_high_stock_rule"])

    def save(self):
        try:
            d = {k: float(e.text()) for k, e in self.fields.items()}
            d["negative_balance_mode"] = self.neg.isChecked()
            d["apply_high_stock_rule"] = self.high.isChecked()
            self.rules_changed.emit(d)
            QMessageBox.information(self, "Exclusion Conditions", "Conditions saved for the next run.")
        except Exception as e:
            QMessageBox.critical(self, "Invalid Condition", str(e))

    def get_rules(self):
        d = {k: float(e.text()) for k, e in self.fields.items()}
        d["negative_balance_mode"] = self.neg.isChecked()
        d["apply_high_stock_rule"] = self.high.isChecked()
        return ExclusionRules(**d)

    def set_data(self, df):
        self.excluded = df if isinstance(df, pd.DataFrame) else pd.DataFrame()
        self.pending_df = self.excluded
        self.has_pending_data = True
        self.summary.setText(f"Excluded parties: {len(self.excluded):,}")

    def load_pending_data(self):
        if self.has_pending_data:
            self.model.set_df(self.pending_df)
            self.pending_df = None
            self.has_pending_data = False

    def download(self):
        if self.excluded.empty:
            QMessageBox.information(self, "Excluded Parties", "No excluded-party data is available yet.")
            return
        try:
            p = export_excluded(self.excluded, int(self.window().year.currentText()), self.window().month_label())
            QMessageBox.information(self, "Export Complete", f"CSV created:\n{p}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    # def toggle_data_only(self):
    #     show_data_only = self.maximize_button.text() == "Show Data Only"
    #     self.rule_form.setVisible(not show_data_only)
    #     self.rule_buttons.setVisible(not show_data_only)
    #     self.maximize_button.setText("Show Full View" if show_data_only else "Show Data Only")


class PartyExclusionTab(QWidget):
    def __init__(self, csv_path, parent=None):
        super().__init__(parent)
        self.csv_path = Path(csv_path)
        self.csv_columns = ["PARTY_ID", "party_name"]
        self.parties = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(get_vector_icon("excluded", "#1d4ed8", 22).pixmap(22, 22))
        header.addWidget(icon)
        title = QLabel("Excluded Parties Configuration")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Party ID", "Party Name", "Enable / Disable", "Delete"])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        self.status = QLabel()
        self.status.setStyleSheet("color: #64748b; font-weight: 500;")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search party ID or name...")
        self.search.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px;")
        self.add_button = QPushButton("+ Add Party")
        self.add_button.setStyleSheet("background-color: #1677ff; color: #ffffff; border-radius: 6px; padding: 6px 14px; font-weight: 600;")
        self.add_button.clicked.connect(self.add_party)
        self.search.textChanged.connect(self.filter_rows)

        top = QHBoxLayout()
        top.addWidget(self.status)
        top.addStretch()
        back_button = QPushButton("  Back to Dashboard")
        back_button.setIcon(get_vector_icon("close", "#64748b", 14))
        back_button.clicked.connect(lambda: self.window()._switch_view(0))
        top.addWidget(back_button)
        top.addWidget(self.add_button)

        lay.addLayout(top)
        lay.addWidget(self.search)
        lay.addWidget(self.table)
        self.load_csv()

    def load_csv(self):
        try:
            source = pd.read_csv(self.csv_path, usecols=["PARTY_ID", "party_name"])
            source["PARTY_ID"] = pd.to_numeric(source["PARTY_ID"], errors="coerce")
            source = source.dropna(subset=["PARTY_ID"]).drop_duplicates("PARTY_ID")
            self.parties = {int(row.PARTY_ID): str(row.party_name) for row in source.itertuples()}
        except Exception as error:
            self.status.setText(f"Could not load party file: {error}")
        self.render()

    def render(self):
        self.table.setRowCount(0)
        for party_id, party_name in self.parties.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(party_id)))
            self.table.setItem(row, 1, QTableWidgetItem(party_name))
            toggle = QPushButton("Enabled")
            toggle.setFixedSize(78, 24)
            toggle.setFlat(True)
            toggle.setStyleSheet("QPushButton, QPushButton:checked { background-color: transparent; }")
            toggle.setCheckable(True)
            toggle.setChecked(True)
            toggle.clicked.connect(lambda checked, button=toggle: button.setText("Enabled" if checked else "Disabled"))
            self.table.setCellWidget(row, 2, toggle)
            delete = QPushButton("Delete")
            delete.setFixedSize(78, 24)
            delete.clicked.connect(lambda checked=False, party_id=party_id: self.delete_party(party_id))
            self.table.setCellWidget(row, 3, delete)
        self.status.setText(f"{len(self.parties):,} parties loaded. Enabled parties will be excluded.")

    def delete_party(self, party_id):
        self.parties.pop(party_id, None)
        self.render()

    def filter_rows(self, text):
        text = text.casefold()
        for row in range(self.table.rowCount()):
            values = [self.table.item(row, column).text().casefold() for column in (0, 1)]
            self.table.setRowHidden(row, text not in values[0] and text not in values[1])

    def add_party(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Party")
        form = QFormLayout(dialog)
        party_id = QLineEdit()
        party_name = QLineEdit()
        form.addRow("Party ID", party_id)
        form.addRow("Party Name", party_name)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            new_id = int(party_id.text().strip())
            new_name = party_name.text().strip()
            if not new_name or new_id in self.parties:
                raise ValueError("Enter a new party ID and party name.")
            self.parties[new_id] = new_name
            self.render()
        except ValueError as error:
            QMessageBox.warning(self, "Invalid Party", str(error))

    def enabled_party_ids(self):
        enabled = []
        for row in range(self.table.rowCount()):
            toggle = self.table.cellWidget(row, 2)
            if toggle.isChecked():
                enabled.append(int(self.table.item(row, 0).text()))
        return enabled

class GroupPartyTab(QWidget):
    def __init__(self, csv_path, parent=None):
        super().__init__(parent)
        self.csv_path = Path(csv_path)
        self.rows = {}  # party_id -> {"group_id": int, "name": str, "enabled": bool}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
 
        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(get_vector_icon("grouped_parties", "#10b981", 22).pixmap(22, 22))
        header.addWidget(icon)
        title = QLabel("Group Parties Configuration")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Party ID", "Group ID", "Distributor Name", "Enable / Disable", "Delete"])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        # Unlike PartyExclusionTab, Party ID / Group ID / Distributor Name
        # cells stay editable (double-click) -- requested "editable rows".
        self.table.itemChanged.connect(self._cell_edited)
 
        self.status = QLabel()
        self.status.setStyleSheet("color: #64748b; font-weight: 500;")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search party ID, group ID or name...")
        self.search.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px;")
        self.add_button = QPushButton("+ Add Party")
        self.add_button.setStyleSheet("background-color: #1677ff; color: #ffffff; border-radius: 6px; padding: 6px 14px; font-weight: 600;")
        self.add_button.clicked.connect(self.add_party)
        self.search.textChanged.connect(self.filter_rows)
 
        top = QHBoxLayout()
        top.addWidget(self.status)
        top.addStretch()
        back_button = QPushButton("  Back to Dashboard")
        back_button.setIcon(get_vector_icon("close", "#64748b", 14))
        back_button.clicked.connect(lambda: self.window()._switch_view(0))
        top.addWidget(back_button)
        top.addWidget(self.add_button)
 
        lay.addLayout(top)
        lay.addWidget(self.search)
        lay.addWidget(self.table)
        self.load_csv()
 
    def load_csv(self):
        try:
            source = pd.read_csv(self.csv_path, usecols=["Party_ID", "Group_id", "Distributor_Name"])
            source["Party_ID"] = pd.to_numeric(source["Party_ID"], errors="coerce")
            source["Group_id"] = pd.to_numeric(source["Group_id"], errors="coerce")
            source = source.dropna(subset=["Party_ID", "Group_id"]).drop_duplicates("Party_ID")
            self.rows = {
                int(r.Party_ID): {"group_id": int(r.Group_id), "name": str(r.Distributor_Name), "enabled": True}
                for r in source.itertuples()
            }
        except Exception as error:
            self.status.setText(f"Could not load group file: {error}")
        self.render()
 
    def render(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for party_id, info in self.rows.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_item = QTableWidgetItem(str(party_id))
            id_item.setData(Qt.UserRole, party_id)  # stable original key for this row
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(str(info["group_id"])))
            self.table.setItem(row, 2, QTableWidgetItem(info["name"]))
            toggle = QPushButton("Enabled" if info["enabled"] else "Disabled")
            toggle.setFixedSize(78, 24)
            toggle.setFlat(True)
            toggle.setStyleSheet("QPushButton, QPushButton:checked { background-color: transparent; }")
            toggle.setCheckable(True)
            toggle.setChecked(info["enabled"])
            toggle.clicked.connect(lambda checked, row_widget=toggle: self._toggle(row_widget, checked))
            self.table.setCellWidget(row, 3, toggle)
            delete = QPushButton("Delete")
            delete.setFixedSize(78, 24)
            delete.clicked.connect(lambda checked=False, row_widget=toggle: self.delete_party(row_widget))
            self.table.setCellWidget(row, 4, delete)
        self.table.blockSignals(False)
        self.status.setText(f"{len(self.rows):,} mappings loaded. Enabled rows convert Party ID to Group ID before calculation.")
 
    def _row_of_widget(self, row_widget):
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, 3) is row_widget:
                return row
        return -1
 
    def _toggle(self, row_widget, checked):
        row = self._row_of_widget(row_widget)
        if row < 0:
            return
        party_id = self.table.item(row, 0).data(Qt.UserRole)
        self.rows[party_id]["enabled"] = checked
        row_widget.setText("Enabled" if checked else "Disabled")
 
    def _cell_edited(self, item):
        row = item.row()
        id_item = self.table.item(row, 0)
        group_item = self.table.item(row, 1)
        name_item = self.table.item(row, 2)
        if id_item is None or group_item is None or name_item is None:
            return
        original_id = id_item.data(Qt.UserRole)
        try:
            new_id = int(id_item.text())
            new_group = int(group_item.text())
        except (ValueError, TypeError):
            return
        info = self.rows.pop(original_id, {"enabled": True})
        info["group_id"] = new_group
        info["name"] = name_item.text()
        self.rows[new_id] = info
        id_item.setData(Qt.UserRole, new_id)  # keep this row's stable key in sync
 
    def delete_party(self, row_widget):
        row = self._row_of_widget(row_widget)
        if row < 0:
            return
        party_id = self.table.item(row, 0).data(Qt.UserRole)
        self.rows.pop(party_id, None)
        self.render()
 
    def filter_rows(self, text):
        text = text.casefold()
        for row in range(self.table.rowCount()):
            values = [self.table.item(row, column).text().casefold() for column in (0, 1, 2)]
            self.table.setRowHidden(row, not any(text in v for v in values))
 
    def add_party(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Group Mapping")
        form = QFormLayout(dialog)
        party_id = QLineEdit()
        group_id = QLineEdit()
        name = QLineEdit()
        form.addRow("Party ID", party_id)
        form.addRow("Group ID", group_id)
        form.addRow("Distributor Name", name)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            new_id = int(party_id.text().strip())
            new_group = int(group_id.text().strip())
            if new_id in self.rows:
                raise ValueError("This Party ID already has a mapping.")
            self.rows[new_id] = {"group_id": new_group, "name": name.text().strip(), "enabled": True}
            self.render()
        except ValueError as error:
            QMessageBox.warning(self, "Invalid Mapping", str(error))
 
    def enabled_group_map(self):
        return {pid: info["group_id"] for pid, info in self.rows.items() if info["enabled"]}


class PartySelector(QDialog):
    def __init__(self, party_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Exclusive Parties")
        self.resize(850, 600)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Select the parties to keep. Other parties will be excluded from this run."))
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.MultiSelection)
        for _, r in party_info.drop_duplicates("PARTY_ID").iterrows():
            item = QListWidgetItem(f'{r["PARTY_ID"]} | {r.get("party_name","")} | {r.get("sales_channel_code","")}')
            item.setData(Qt.UserRole, int(r["PARTY_ID"]))
            self.list.addItem(item)
        lay.addWidget(self.list)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        lay.addWidget(b)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)

    def ids(self):
        return [int(i.data(Qt.UserRole)) for i in self.list.selectedItems()]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Distributor Stock Rebate Application")
        self.resize(1350, 700)

        self.results = {}
        self.workflow = None
        self.workflow_step = 0
        self.exclusive_ids = []
        self.use_exclusive = False
        self.current_exclusion_rules = dict(DEFAULT_EXCLUSION_RULES)
        self.current_rebate_rules = [dict(rule) for rule in DEFAULT_REBATE_RULES]

        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.CustomizeWindowHint
        )
        self.setMenuBar(None)

        # Build widgets first
        self._build_ui()

        # Apply stylesheet after widgets/objectNames exist
        self.setStyleSheet(MAIN_STYLESHEET)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        root_vlay = QVBoxLayout(central)
        root_vlay.setContentsMargins(0, 0, 0, 0)
        root_vlay.setSpacing(0)

        # -------------------------------------------------------------
        # TOP CUSTOM TITLE BAR (Navy blue with logo, title, and min/max/close)
        # -------------------------------------------------------------
        self.title_bar = CustomTitleBar(self)
        root_vlay.addWidget(self.title_bar)

        # Main Body (Sidebar + Content)
        main_hlay = QHBoxLayout()
        main_hlay.setContentsMargins(0, 0, 0, 0)
        main_hlay.setSpacing(0)
        root_vlay.addLayout(main_hlay, 1)

        # -------------------------------------------------------------
        # 1. LEFT NAVIGATION SIDEBAR
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("SidebarContainer")
        sidebar.setFixedWidth(200)
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(10, 14, 10, 14)
        sidebar_lay.setSpacing(4)

        # Navigation Buttons (starts directly from top as in reference design)
        self.nav_buttons = []
        nav_items = [
            ("Dashboard", "dashboard", 0),
            ("Stock Data", "stock_data", 1),
            ("Party Info", "party_info", 2),
            ("Party Receivable", "party_receivable", 3),
            ("Excluded Parties", "excluded", 4),
            ("Final Rebate", "rebate", 5),
        ]

        for label, icon_key, idx in nav_items:
            btn = QPushButton(f"  {label}")
            btn.setProperty("class", "nav-btn")
            btn.setProperty("icon_key", icon_key)
            btn.setProperty("page_index", idx)
            btn.setIcon(get_vector_icon(icon_key, "#94a3b8", 18))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda checked=False, i=idx: self._switch_view(i))
            sidebar_lay.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_lay.addStretch()

        # About button at bottom of sidebar
        about_btn = QPushButton("  About")
        about_btn.setProperty("class", "nav-about-btn")
        about_btn.setIcon(get_vector_icon("about", "#94a3b8", 18))
        about_btn.clicked.connect(self._show_about)
        sidebar_lay.addWidget(about_btn)

        main_hlay.addWidget(sidebar)

        # -------------------------------------------------------------
        # 2. MAIN CONTENT AREA (Top Filter Bar + Stacked Pages)
        # -------------------------------------------------------------
        content_area = QWidget()
        content_area.setStyleSheet("background-color: #f1f5f9;")
        content_lay = QVBoxLayout(content_area)
        content_lay.setContentsMargins(16, 12, 16, 12)
        content_lay.setSpacing(12)

        # --- Top Filter & Action Bar ---
        top_bar = QFrame()
        top_bar.setObjectName("TopFilterBar")
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(14, 8, 14, 8)
        top_lay.setSpacing(16)

        self.date_badge = QLabel()
        self.date_badge.setProperty("class", "filter-label")
        top_lay.addWidget(self.date_badge)

        # Stock Year Dropdown
        year_group = QVBoxLayout()
        year_group.setSpacing(2)
        y_lbl = QLabel(" Stock Year")
        y_lbl.setProperty("class", "filter-label")
        year_group.addWidget(y_lbl)
        self.year = QComboBox()
        for y in range(2020, 2036):
            self.year.addItem(str(y))
        self.year.setCurrentText("2026")
        self.year.setFixedWidth(90)
        self.year.currentTextChanged.connect(self._update_date_badge)
        year_group.addWidget(self.year)
        top_lay.addLayout(year_group)

        # Stock Month Dropdown
        month_group = QVBoxLayout()
        month_group.setSpacing(2)
        m_lbl = QLabel(" Stock Month")
        m_lbl.setProperty("class", "filter-label")
        month_group.addWidget(m_lbl)
        self.month = QComboBox()
        self.month.addItem("Select Month", None)
        for i in range(1, 13):
            self.month.addItem(f"{calendar.month_name[i]}", i)
        self.month.setCurrentIndex(0)
        self.month.setFixedWidth(115)
        self.month.currentIndexChanged.connect(self._update_date_badge)
        month_group.addWidget(self.month)
        top_lay.addLayout(month_group)

        # Sales Channel Dropdown
        channel_group = QVBoxLayout()
        channel_group.setSpacing(2)
        c_lbl = QLabel(" Sales Channel")
        c_lbl.setProperty("class", "filter-label")
        channel_group.addWidget(c_lbl)
        self.channel_combo = QComboBox()
        self.channel_combo.addItem("All Channels", "All")
        self.channel_combo.addItem("WDN", "WDN")
        self.channel_combo.addItem("MDN", "MDN")
        self.channel_combo.addItem("Single Party", "Single Party")
        self.channel_combo.setFixedWidth(160)
        self.channel_combo.currentIndexChanged.connect(self._handle_channel_change)
        channel_group.addWidget(self.channel_combo)
        top_lay.addLayout(channel_group)

        # Single Party Selection
        party_group = QVBoxLayout()
        party_group.setSpacing(2)
        p_lbl = QLabel(" Single Party Selection")
        p_lbl.setProperty("class", "filter-label")
        party_group.addWidget(p_lbl)
        party_input_lay = QHBoxLayout()
        party_input_lay.setSpacing(4)
        self.single_party_edit = QLineEdit()
        self.single_party_edit.setPlaceholderText("Enter Party ID")
        self.single_party_edit.setFixedWidth(180)
        self.single_party_edit.hide()
        party_input_lay.addWidget(self.single_party_edit)
        self.single_party_btn = QPushButton("Submit")
        self.single_party_btn.setFixedHeight(30)
        self.single_party_btn.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 10px; background: #ffffff; color: #2563eb;")
        self.single_party_btn.hide()
        self.single_party_btn.clicked.connect(self._search_single_party)
        party_input_lay.addWidget(self.single_party_btn)
        party_group.addLayout(party_input_lay)
        top_lay.addLayout(party_group)

        top_lay.addStretch()


        # Action Buttons
        self.next_step_btn = QPushButton("▶  Next Step")
        self.next_step_btn.setStyleSheet("""
            QPushButton {
                background-color: #1677FF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0958D9; }
            QPushButton:pressed { background-color: #003EB3; }
            QPushButton:disabled { background-color: #93C5FD; color: #F8FAFC; }
        """)
        self.next_step_btn.clicked.connect(self.run_next_step)
        top_lay.addWidget(self.next_step_btn)

        self.run_all_btn = QPushButton(" Run All")
        self.run_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #059669; }
            QPushButton:pressed { background-color: #047857; }
            QPushButton:disabled { background-color: #6ee7b7; color: #f0fdf4; }
        """)
        self.run_all_btn.clicked.connect(self.run_all)
        top_lay.addWidget(self.run_all_btn)

        content_lay.addWidget(top_bar)

        # Progress bar (subtle banner, visible only during calculation)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("QProgressBar { border: none; background: #e2e8f0; } QProgressBar::chunk { background: #1677ff; }")
        self.progress.hide()
        content_lay.addWidget(self.progress)

        # --- Stacked Pages ---
        self.pages = QStackedWidget()
        content_lay.addWidget(self.pages, 1)

        # Create all views
        self._create_dashboard_page()
        self._create_data_pages()
        self._update_date_badge()

        # Set default active view to Dashboard
        self._switch_view(0)
        main_hlay.addWidget(content_area, 1)

    def _update_date_badge(self):
        m_name = self.month.currentText()
        yr = self.year.currentText()
        self.date_badge.setText(f"📅 Month & Year: {m_name} {yr}")
        self.run_info_month.setText(f"{m_name} {yr}")

    def _handle_channel_change(self, idx):
        channel = self.channel_combo.currentData()
        is_single_party = channel == "Single Party"
        self.single_party_edit.setVisible(is_single_party)
        self.single_party_btn.setVisible(is_single_party)
        if not is_single_party:
            self.use_exclusive = False
            self.exclusive_ids = []
            self.run_info_channel.setText(channel or "All Channels")
        else:
            self.run_info_channel.setText("Single Party: Not Selected")
        self._reset_workflow()

    def _search_single_party(self):
        if self.channel_combo.currentData() != "Single Party":
            return
        pid_text = self.single_party_edit.text().strip()
        if not pid_text:
            self.use_exclusive = False
            self.exclusive_ids = []
            self.run_info_party.setText("Not Selected")
            self.activity_log.add_log("Cleared single party filter.")
            return
        try:
            pid = int(pid_text)
            self.use_exclusive = True
            self.exclusive_ids = [pid]
            self.run_info_party.setText(f"Party ID: {pid}")
            self.activity_log.add_log(f"Filtered for single party ID: {pid}")
        except ValueError:
            QMessageBox.warning(self, "Invalid Party ID", "Party ID must be a numeric value.")

    def _create_dashboard_page(self):
        """Builds the comprehensive Dashboard view matching the reference design."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f1f5f9; }")

        dash = QWidget()
        dash.setObjectName("DashboardContainer")
        dash.setStyleSheet("QWidget#DashboardContainer { background-color: #f1f5f9; }")
        dash_lay = QVBoxLayout(dash)
        dash_lay.setContentsMargins(0, 0, 0, 0)
        dash_lay.setSpacing(12)

        # =========================================================
        # 1. Step 1: Configure Before Running Card
        # =========================================================
        step1_card = QFrame()
        step1_card.setObjectName("Step1Banner")
        s1_lay = QVBoxLayout(step1_card)
        s1_lay.setContentsMargins(16, 10, 16, 10)
        s1_lay.setSpacing(8)

        # Header Row with big blue gear circle
        h_row = QHBoxLayout()
        h_row.setSpacing(12)
        gear_lbl = QLabel()
        gear_lbl.setPixmap(create_badge_icon("gear", "#1677ff", 38).pixmap(38, 38))
        h_row.addWidget(gear_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(1)
        s1_title = QLabel("Configure Before Running")
        s1_title.setStyleSheet("color: #0f172a; font-size: 15px; font-weight: 700;")
        txt_col.addWidget(s1_title)
        h_row.addLayout(txt_col)
        h_row.addStretch()
        s1_lay.addLayout(h_row)

        # 4 Mini Action Cards in a row
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        # Card 1: Configure Exclusion Conditions
        c1 = ConfigActionCard("Configure Exclusion Conditions", "gear", "#10b981")
        c1.clicked.connect(self._open_exclusion_dialog)
        action_row.addWidget(c1)

        # Card 2: Configure Rebate Conditions
        c2 = ConfigActionCard("Configure Rebate Conditions", "gift", "#06b6d4")
        c2.clicked.connect(self._open_rebate_dialog)
        action_row.addWidget(c2)


        # Card 3: Configure Default Excluded Parties
        c3 = ConfigActionCard("Excluded Parties", "document", "#1d4ed8")
        c3.clicked.connect(lambda: self._switch_view(self.pages.indexOf(self.party_exclusions)))
        action_row.addWidget(c3)

        c4 = ConfigActionCard("Group Parties", "document", "#10b981")
        c4.clicked.connect(lambda: self._switch_view(self.pages.indexOf(self.group_parties)))
        action_row.addWidget(c4)
                           

        s1_lay.addLayout(action_row)
        dash_lay.addWidget(step1_card)


        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        self.stat_eligible = StatCard("Eligible Parties", "0", "eligible", "#10b981", "#bbf7d0")
        kpi_row.addWidget(self.stat_eligible)

        self.stat_excluded = StatCard("Excluded Parties", "0", "excluded", "#ef4444", "#fecdd3")
        kpi_row.addWidget(self.stat_excluded)

        dash_lay.addLayout(kpi_row)

        # =========================================================
        # 3. Middle Section (2 Columns: Progress & Info / Recent Logs)
        # =========================================================
        mid_row = QHBoxLayout()
        mid_row.setSpacing(10)

        # Left Column: Progress Card + Latest Run Info Card
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # Calculation Progress Card
        prog_card = QFrame()
        prog_card.setProperty("class", "card-panel")
        prog_card_lay = QVBoxLayout(prog_card)
        prog_card_lay.setContentsMargins(14, 8, 14, 8)
        prog_card_lay.setSpacing(6)

        cp_title = QLabel("Calculation Progress")
        cp_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        prog_card_lay.addWidget(cp_title)

        self.stepper = ProgressStepper()
        self.stepper.set_step(1)
        prog_card_lay.addWidget(self.stepper)

        # Execution banner
        self.step_info_box = QFrame()
        self.step_info_box.setObjectName("StepInfoBox")
        info_lay = QHBoxLayout(self.step_info_box)
        info_lay.setContentsMargins(10, 6, 10, 6)
        info_lay.setSpacing(8)

        info_icon = QLabel()
        info_icon.setPixmap(create_badge_icon("info", "#0284c7", 24).pixmap(24, 24))
        info_lay.addWidget(info_icon)

        self.step_info_title = QLabel("Ready to run")
        self.step_info_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #0f172a;")
        info_lay.addWidget(self.step_info_title)

        self.step_info_sub = QLabel("Select a calculation action to begin.")
        self.step_info_sub.setStyleSheet("font-size: 11px; color: #64748b;")
        self.step_info_sub.setWordWrap(True)
        self.step_info_sub.setMinimumWidth(0)
        self.step_info_sub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        info_lay.addWidget(self.step_info_sub, 1)

        prog_card_lay.addWidget(self.step_info_box)


        left_col.addWidget(prog_card)

        # Latest Run Information Card
        run_card = QFrame()
        run_card.setObjectName("RunInfoCard")
        run_lay = QVBoxLayout(run_card)
        run_lay.setContentsMargins(14, 6, 14, 6)
        run_lay.setSpacing(4)

        run_title = QLabel("Latest Run Information")
        run_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        run_lay.addWidget(run_title)

        grid = QGridLayout()
        grid.setVerticalSpacing(3)
        grid.setHorizontalSpacing(14)

        def add_info_row(row_idx, label_text, default_val):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #64748b; font-size: 12px;")
            val = QLabel(default_val)
            val.setStyleSheet("color: #0f172a; font-size: 12px; font-weight: 600;")
            grid.addWidget(lbl, row_idx, 0)
            grid.addWidget(QLabel(":"), row_idx, 1)
            grid.addWidget(val, row_idx, 2)
            return val

        self.run_info_month = add_info_row(0, "Month & Year", "July 2026")
        self.run_info_channel = add_info_row(1, "Sales Channel", "All Eligible Parties")
        self.run_info_party = add_info_row(2, "Single Party", "Not Selected")
        self.run_info_last_run = add_info_row(3, "Last Run", "-")
        self.run_info_status = add_info_row(4, "Status", "Waiting for next step...")

        run_lay.addLayout(grid)
        left_col.addWidget(run_card)

        mid_row.addLayout(left_col, 5)

        # Right Column: Recent Activity / Logs
        self.activity_log = ActivityLogWidget()
        self.activity_log.add_log("Application started", "info")
        self.activity_log.add_log("Loaded configuration", "success")
        self.activity_log.add_log("Ready to run. Please click 'Next Step' to proceed.", "warn")
        mid_row.addWidget(self.activity_log, 4)

        dash_lay.addLayout(mid_row)

        # =========================================================
        # 4. Quick Actions Bar (Bottom)
        # =========================================================
        qa_card = QFrame()
        qa_card.setProperty("class", "card-panel")
        qa_lay = QVBoxLayout(qa_card)
        qa_lay.setContentsMargins(14, 6, 14, 8)
        qa_lay.setSpacing(6)

        qa_header = QHBoxLayout()
        qa_header.setSpacing(8)
        qa_icon = QLabel()
        qa_icon.setPixmap(create_badge_icon("bolt", "#10b981", 22).pixmap(22, 22))
        qa_header.addWidget(qa_icon)
        qa_title = QLabel("Quick Actions")
        qa_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        qa_header.addWidget(qa_title)
        qa_header.addStretch()
        qa_lay.addLayout(qa_header)

        actions_grid = QHBoxLayout()
        actions_grid.setSpacing(12)

        q1 = QuickActionCard("View Stock Data", "Browse and analyze stock data", "stock_data")
        q1.clicked.connect(lambda: self._switch_view(1))
        actions_grid.addWidget(q1)

        q2 = QuickActionCard("View Final Rebate Reports", "Detailed party wise report", "results")
        q2.clicked.connect(lambda: self._switch_view(self.pages.indexOf(self.rebate)))
        actions_grid.addWidget(q2)

        qa_lay.addLayout(actions_grid)
        dash_lay.addWidget(qa_card)

        scroll.setWidget(dash)
        self.dashboard_page = scroll
        self.pages.addWidget(self.dashboard_page)

    def _create_data_pages(self):
        """Creates the other data pages (Stock, Party Info, Excluded, Rebate, Results, Logs)."""
        # 1. Stock Data
        self.stock = DataTab("Entered Stock Data")
        self.pages.addWidget(self.stock)

        # 2. Party Info
        self.party = DataTab("Party Information")
        self.pages.addWidget(self.party)

        # 3. Party Receivable
        self.receivable = DataTab("Party Receivable")
        self.pages.addWidget(self.receivable)

        # 5. Excluded Parties
        self.excluded = ExclusionTab(DEFAULT_EXCLUSION_RULES)
        self.pages.addWidget(self.excluded)

        # 6. Rebate
        self.rebate = RebateTab(DEFAULT_REBATE_RULES)
        self.pages.addWidget(self.rebate)

        # 7. Grouped Parties
        # self.grouped_parties_tab = GroupedPartiesPlaceholderTab()
        # self.pages.addWidget(self.grouped_parties_tab)

        # # 8. Final Results
        # self.results_tab = DataTab("Final Rebate Results")
        # self.pages.addWidget(self.results_tab)

        # # 9. Logs View
        self.logs_page = QWidget()
        log_lay = QVBoxLayout(self.logs_page)
        log_lay.setContentsMargins(16, 16, 16, 16)
        log_lay.setSpacing(12)

        self.logs = QTextEdit()
        self.logs.setProperty("class", "log-view")
        self.logs.setReadOnly(True)

        log_top = QHBoxLayout()
        l_title = QLabel("System Activity & Execution Logs")
        l_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0f172a;")
        log_top.addWidget(l_title)
        log_top.addStretch()

        copy_btn = QPushButton("Copy Logs")
        copy_btn.setProperty("class", "btn-secondary")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.logs.toPlainText()))
        log_top.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("class", "btn-outline")
        clear_btn.clicked.connect(self.logs.clear)
        log_top.addWidget(clear_btn)
        log_lay.addLayout(log_top)

        log_lay.addWidget(self.logs)
        self.pages.addWidget(self.logs_page)

        # Background references
        csv_path = Path(__file__).resolve().parents[2] / "EXCLUDE_&_GROUP_PARTY" / "EXCLUDE" / "Exclude_Party.csv"
        self.party_exclusions = PartyExclusionTab(csv_path, self)
        self.pages.addWidget(self.party_exclusions)

        group_csv_path = GROUP_FILE
        self.group_parties = GroupPartyTab(group_csv_path, self)
        self.pages.addWidget(self.group_parties)

    def _switch_view(self, index: int):
        self.pages.setCurrentIndex(index)
        current_page = self.pages.widget(index)
        if hasattr(current_page, "load_pending_data"):
            current_page.load_pending_data()
        nav_keys = ["dashboard", "stock_data", "party_info", "party_receivable", "excluded", "rebate"]
        for btn in self.nav_buttons:
            is_active = (btn.property("page_index") == index)
            btn.setChecked(is_active)
            btn.setIcon(get_vector_icon(btn.property("icon_key"), "#ffffff" if is_active else "#94a3b8", 18))

    def _open_exclusion_dialog(self):
        dlg = ExclusionConfigDialog(self.current_exclusion_rules, self)
        dlg.rules_saved.connect(self._on_exclusion_rules_saved)
        dlg.exec()

    def _open_rebate_dialog(self):
        dlg = RebateConfigDialog(self.current_rebate_rules, self)
        dlg.rules_saved.connect(self._on_rebate_rules_saved)
        dlg.exec()

    def _on_rebate_rules_saved(self, rules):
        self.current_rebate_rules = [dict(rule) for rule in rules]
        self.rebate.set_rules(rules)
        self.activity_log.add_log("Saved updated rebate rules.", "success")
        QMessageBox.information(self, "Configuration Saved", "Rebate conditions saved for subsequent runs.")

    def _on_exclusion_rules_saved(self, rules_dict):
        self.current_exclusion_rules = rules_dict
        for k, v in rules_dict.items():
            if k in self.excluded.fields:
                self.excluded.fields[k].setText(str(v))
        if "negative_balance_mode" in rules_dict:
            self.excluded.neg.setChecked(rules_dict["negative_balance_mode"])
        if "apply_high_stock_rule" in rules_dict:
            self.excluded.high.setChecked(rules_dict["apply_high_stock_rule"])
        self.activity_log.add_log("Saved updated exclusion rules and thresholds.", "success")
        QMessageBox.information(self, "Configuration Saved", "Exclusion conditions saved for subsequent runs.")

    def _show_about(self):
        QMessageBox.about(
            self,
            "Distributor Stock Rebate Calculation",
            "<h3>Distributor Stock Rebate Calculation</h3>"
            "<p>Version 2.0</p>"
            "<p>A high-performance distributor rebate management and calculation suite.</p>"
        )

    def _export_last_results(self):
        if not self.results:
            QMessageBox.information(self, "Export Results", "Run calculation first before exporting results.")
            return
        self._start_export(self.results, notify=True)

    def _start_export(self, data, notify):
        if getattr(self, "export_thread", None) and self.export_thread.isRunning():
            if notify:
                QMessageBox.information(self, "Export in Progress", "Report export is already running.")
            return
        self._export_notify = notify
        if hasattr(self, "export_action"):
            self.export_action.setEnabled(False)
        self.export_thread = QThread(self)
        self.export_worker = ExportWorker(data, int(self.year.currentText()), self.month_label())
        self.export_worker.moveToThread(self.export_thread)
        self.export_thread.started.connect(self.export_worker.run)
        self.export_worker.done.connect(self._export_finished)
        self.export_worker.error.connect(self._export_failed)
        self.export_worker.done.connect(self.export_thread.quit)
        self.export_worker.error.connect(self.export_thread.quit)
        self.export_thread.finished.connect(self.export_worker.deleteLater)
        self.export_thread.finished.connect(self._export_thread_finished)
        self.export_thread.start()

    def _export_finished(self, paths):
        self.log(f"Final CSV reports created: {paths}")
        self.activity_log.add_log(f"Final CSV reports created at {paths}", "success")
        if self._export_notify:
            QMessageBox.information(self, "Export Complete", f"CSV report files generated successfully:\n{paths}")

    def _export_failed(self, message):
        self.log(f"CSV export warning: {message}")
        if self._export_notify:
            QMessageBox.critical(self, "Export Error", message)

    def _export_thread_finished(self):
        if hasattr(self, "export_action"):
            self.export_action.setEnabled(True)
        self.export_worker = None
        self.export_thread = None

    def month_label(self):
        return month_label(int(self.year.currentText()), self.month.currentData())

    def configure_parties(self):
        if "party_info" not in self.results:
            QMessageBox.information(
                self,
                "Party Information",
                "Run the calculation once to load Party Information, then configure the exclusive list.",
            )
            return
        d = self.results["party_info"]
        dlg = PartySelector(d, self)
        if dlg.exec() == QDialog.Accepted:
            self.exclusive_ids = dlg.ids()
            self.use_exclusive = True
            self.run_info_channel.setText(f"Exclusive ({len(self.exclusive_ids):,} selected)")
            self.activity_log.add_log(f"Selected {len(self.exclusive_ids):,} exclusive parties.")

    def log(self, msg):
        if "partylefting" in msg.casefold() or "party lifting" in msg.casefold():
            print(f"[PartyLifting] GUI progress callback thread={threading.get_ident()}, gui_thread={QThread.currentThread() == self.worker_thread()}, message={msg}", flush=True)
        self.logs.append(msg)
        step_idx = 1
        m_lower = msg.lower()
        if "enteredstock" in m_lower or "group mapping" in m_lower:
            step_idx = 1
        elif "party information" in m_lower:
            step_idx = 2
        elif "lifting" in m_lower:
            step_idx = 3
        elif "receivable" in m_lower:
            step_idx = 4
        elif "receiving" in m_lower or "previous" in m_lower:
            step_idx = 5
        elif "exclusion" in m_lower:
            step_idx = 6
        elif "completed" in m_lower:
            step_idx = 7

        self.stepper.set_step(step_idx)
        self.step_info_title.setText(f"Executed step {step_idx} of 7")
        status_msg = msg if len(msg) <= 180 else f"{msg[:177]}..."
        self.step_info_sub.setText(status_msg)
        self.activity_log.add_log(msg)
        self.run_info_status.setText(msg[:40] + "..." if len(msg) > 40 else msg)

    def _build_config(self):
        if self.month.currentData() is None:
            QMessageBox.warning(self, "Select Month", "Please select a stock month before running the calculation.")
            return None
        try:
            rules = self.excluded.get_rules()
            rebate_rules = self.rebate.get_rules()
            return CalculationConfig(
                self.month.currentData(),
                int(self.year.currentText()),
                self.channel_combo.currentData() or "All",
                self.exclusive_ids,
                self.party_exclusions.enabled_party_ids(),
                self.use_exclusive,
                True,
                rules,
                rebate_rules,
                single_party_id=(int(self.single_party_edit.text()) if self.channel_combo.currentData() == "Single Party" and self.single_party_edit.text().strip() else None),
                group_map = self.group_parties.enabled_group_map(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", str(e))
            return None

    def run_next_step(self):
        if self.workflow_step >= 7:
            QMessageBox.information(self, "Workflow Complete", "All calculation steps are already complete. Use Run All to start a new run.")
            return
        cfg = self._build_config()
        if cfg is None:
            return
        if self.workflow is None:
            self.workflow = Workflow(cfg)
            self.workflow_step = 0
            self.results = {}
            self.logs.clear()
        self._start_worker(cfg, self.workflow_step + 1, False)

    def run_all(self):
        cfg = self._build_config()
        if cfg is None:
            return
        self.workflow = Workflow(cfg)
        self.workflow_step = 0
        self.results = {}
        self.logs.clear()
        self._start_worker(cfg, 7, True)

    def _start_worker(self, cfg, step, run_all):

        self.next_step_btn.setEnabled(False)
        self.run_all_btn.setEnabled(False)
        self.progress.show()
        self.activity_log.add_log("Starting rebate workflow execution...", "info")
        self.log("Starting workflow..." if run_all else f"Starting calculation step {step} of 8...")

        self.worker_thread = QThread(self)
        self.worker = Worker(cfg, self.workflow, step, run_all)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.log)
        self.worker.done.connect(self.finished)
        self.worker.error.connect(self.failed)
        self.worker.done.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)

        # self.worker_thread.finished.connect(lambda: self.next_step_btn.setEnabled(True))
        # self.worker_thread.finished.connect(lambda: self.run_all_btn.setEnabled(True))
        # self.worker_thread.finished.connect(self.progress.hide)
        
        self.worker_thread.finished.connect(self._on_worker_thread_finished)

        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()
    def _on_worker_thread_finished(self):
        self.next_step_btn.setEnabled(True)
        self.run_all_btn.setEnabled(True)
        self.progress.hide()
        
    def finished(self, data, step=7, run_all=True):
        print(f"[PartyLifting] GUI finished callback START thread={threading.get_ident()}, gui_thread={QThread.currentThread() == QApplication.instance().thread()}, step={step}", flush=True)
        for key in ("party_lefting_raw", "party_lefting", "effective_stock_detail"):
            value = data.get(key)
            if isinstance(value, pd.DataFrame):
                print(f"[PartyLifting] GUI result handoff {key} shape={value.shape}", flush=True)
        self.results = data
        mapping = {
            "entered_stock": self.stock,
            "party_info": self.party,
            "party_receivable_raw": self.receivable,
            "excluded_parties": self.excluded,
            "rebate_results": self.rebate,
        }
        for k, w in mapping.items():
            if k in data:
                if k == "rebate_results":
                    w.set_results(data[k])
                else:
                    w.set_data(data[k])

        self.workflow_step = 7 if run_all else step
        if self.workflow_step == 7:
            self.next_step_btn.hide()
            self.run_all_btn.hide()
        eligible_count = len(data.get("rebate_results", []))
        excluded_count = len(data.get("excluded_parties", []))
        self.stat_eligible.set_value(f"{eligible_count:,}")
        self.stat_excluded.set_value(f"{excluded_count:,}")

        self.stepper.set_step(8 if self.workflow_step == 7 else self.workflow_step)
        if self.workflow_step == 7:
            self._switch_view(self.pages.indexOf(self.rebate))
            self.step_info_title.setText("Calculation Completed Successfully")
            self.step_info_sub.setText(f"{eligible_count:,} eligible parties, {excluded_count:,} excluded parties.")
            self.run_info_last_run.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.run_info_status.setText("Completed")
            self.activity_log.add_log("Calculation completed successfully.", "success")
            self._start_export(data, notify=False)
        else:
            destination = {
                1: self.stock,
                2: self.party,
                3: self.dashboard_page,
                4: self.receivable,
                5: self.dashboard_page,
                6: self.excluded,
                7: self.rebate,
            }[self.workflow_step]
            self._switch_view(self.pages.indexOf(destination))
            self.step_info_title.setText(f"Step {self.workflow_step} of 8 completed")
            if self.workflow_step == 3:
                self.step_info_sub.setText("Party Lifting data fetched. Click Next Step to continue.")
            else:
                self.step_info_sub.setText("Review the displayed data, then click Next Step to continue.")
            self.run_info_status.setText(f"Step {self.workflow_step} completed")
            self.activity_log.add_log(f"Calculation step {self.workflow_step} completed.", "success")

        # Automatically load data for the currently active view
        current_page = self.pages.currentWidget()
        if hasattr(current_page, "load_pending_data"):
            current_page.load_pending_data()
        print("[PartyLifting] GUI finished callback DONE", flush=True)

    def failed(self, msg):
        self.log("ERROR - workflow failed")
        self.logs.append(msg)
        self.activity_log.add_log("Workflow execution encountered an error.", "error")
        self.step_info_title.setText("Workflow Failed")
        self.step_info_sub.setText(msg[:60])
        self.run_info_status.setText("Error")
        QMessageBox.critical(self, "Workflow Error", msg)

    def closeEvent(self, event):
        # Without this, closing the window leaves any still-running
        # QThreads (calculation worker, export worker) and the Trino/
        # Oracle DB engine/connections alive in the background. Qt/Python
        # will then refuse to fully exit the process until those resources
        # are released on their own -- which is exactly what "the app
        # closes but the process is still running" looks like.
        for thread_attr in ("worker_thread", "export_thread"):
            th = getattr(self, thread_attr, None)
            if th is not None and th.isRunning():
                th.quit()
                if not th.wait(5000):
                    # Did not stop cleanly in 5s (e.g. stuck on a slow
                    # network call) -- force it rather than let the
                    # process hang indefinitely on exit.
                    th.terminate()
                    th.wait()

        if self.workflow is not None and getattr(self.workflow, "db", None) is not None:
            try:
                self.workflow.db.close()
            except Exception:
                pass

        super().closeEvent(event)

    def _reset_workflow(self):
        self.workflow = None
        self.workflow_step = 0
        self.next_step_btn.show()
        self.run_all_btn.show()

    def _update_date_badge(self):
        m_name = self.month.currentText()
        yr = self.year.currentText()
        self.date_badge.setText(f"📅 Month & Year: {m_name} {yr}")
        self.run_info_month.setText(f"{m_name} {yr}")
        self._reset_workflow()

def launch():
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.show()
    return app.exec()
