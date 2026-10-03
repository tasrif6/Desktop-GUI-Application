from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLineEdit,
    QCheckBox,
    QScrollArea,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QDateTime, QRectF, QPointF, QAbstractTableModel, QModelIndex, QTimer
from PySide6.QtGui import QIcon, QPainter, QColor, QFont, QPen, QBrush, QCursor
import numpy as np
import pandas as pd
from app.gui.icons import get_vector_icon, create_badge_icon
from app.models.config import ExclusionRules

class CustomTitleBar(QFrame):
    """Custom dark navy title bar matching the top bar in the reference image."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(36)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 8, 0)
        lay.setSpacing(10)

        # App Logo
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_vector_icon("app_logo", "#38bdf8", 20).pixmap(20, 20))
        lay.addWidget(icon_lbl)

        # Title
        t_lbl = QLabel("Distributor Stock Rebate")
        t_lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700;")
        lay.addWidget(t_lbl)

        lay.addStretch()

        # Window controls
        btn_style = """
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #ffffff;
            }
        """
        min_btn = QPushButton("—")
        min_btn.setStyleSheet(btn_style)
        min_btn.clicked.connect(self.window().showMinimized)
        lay.addWidget(min_btn)

        max_btn = QPushButton("□")
        max_btn.setStyleSheet(btn_style)
        max_btn.clicked.connect(self._toggle_max)
        lay.addWidget(max_btn)

        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                font-size: 13px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.window().close)
        lay.addWidget(close_btn)

    def _toggle_max(self):
        w = self.window()
        if w.isMaximized():
            w.showNormal()
        else:
            w.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class StatCard(QFrame):
    """Modern KPI metric summary card with circular badge icon, title, large stat, and subtitle."""
    def __init__(self, title: str, initial_value: str, icon_name: str, badge_color: str, card_bg: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {card_bg};
                border-radius: 10px;
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)

        # Polished circular icon badge
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(44, 44)
        self.icon_label.setAttribute(Qt.WA_TranslucentBackground)
        self.icon_label.setStyleSheet(f"background-color: {card_bg};")
        self.icon_label.setPixmap(create_badge_icon(icon_name, badge_color, 44).pixmap(44, 44))
        lay.addWidget(self.icon_label)

        # Texts
        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        text_lay.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("background-color: transparent; color: #64748b; font-size: 16px; font-weight: 600;")
        text_lay.addWidget(self.title_lbl)

        self.value_lbl = QLabel(initial_value)
        self.value_lbl.setStyleSheet("background-color: transparent; color: #0f172a; font-size: 22px; font-weight: 700;")
        text_lay.addWidget(self.value_lbl)


        lay.addLayout(text_lay)
        lay.addStretch()

    def set_value(self, value: str):
        self.value_lbl.setText(value)


class ConfigActionCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, icon_key: str, icon_bg: str, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        # Badge
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setPixmap(create_badge_icon(icon_key, icon_bg, 36).pixmap(36, 36))
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(icon_lbl)

        # Texts
        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        text_lay.setContentsMargins(0, 0, 0, 0)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #0f172a; font-size: 12px; font-weight: 600;")
        t_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)


        text_lay.addWidget(t_lbl)
        lay.addLayout(text_lay)

        lay.addStretch()

        # Chevron >
        chev = QLabel("›")
        chev.setStyleSheet("color: #2563eb; font-size: 20px; font-weight: 700;")
        chev.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(chev)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class QuickActionCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, subtitle: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
            }
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(30, 30)
        icon_lbl.setPixmap(get_vector_icon(icon_name, "#0284c7", 24).pixmap(24, 24))
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(icon_lbl)

        t_lay = QVBoxLayout()
        t_lay.setSpacing(2)
        t_lay.setContentsMargins(0, 0, 0, 0)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #0f172a; font-size: 12px; font-weight: 600;")
        t_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        s_lbl = QLabel(subtitle)
        s_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        s_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        t_lay.addWidget(t_lbl)
        t_lay.addWidget(s_lbl)
        lay.addLayout(t_lay)
        lay.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ProgressStepper(QWidget):
    """Step progression widget with connected circular nodes and status message."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps = [
            "Stock Data",
            "Party Info",
            "Party Lifting",
            "Receivable",
            "Current/Prev Stock",
            "Exclusion",
            "Final Rebate",
        ]
        self.current_step = 0
        self.setFixedHeight(85)

    def set_step(self, step_idx: int):
        self.current_step = step_idx
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        n = len(self.steps)
        if n < 2: return

        margin = 35
        y = 22
        step_dist = (w - 2 * margin) / (n - 1)

        # Draw connecting lines
        for i in range(n - 1):
            x1 = margin + i * step_dist
            x2 = margin + (i + 1) * step_dist
            line_pen = QPen(QColor("#10b981") if (i + 1) < self.current_step else QColor("#e2e8f0"))
            line_pen.setWidth(3)
            p.setPen(line_pen)
            p.drawLine(x1, y, x2, y)

        # Draw step circles & labels
        for i, step_name in enumerate(self.steps):
            cx = margin + i * step_dist
            r = 12
            step_num = i + 1

            if step_num < self.current_step:
                # Completed: Green circle with checkmark
                p.setBrush(QBrush(QColor("#10b981")))
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(cx, y), r, r)
                p.setPen(QPen(QColor("#ffffff"), 2))
                p.drawLine(cx - 4, y, cx - 1, y + 4)
                p.drawLine(cx - 1, y + 4, cx + 5, y - 4)
            elif step_num == self.current_step:
                # Active: Vibrant Blue circle with step number
                p.setBrush(QBrush(QColor("#1677ff")))
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(cx, y), r + 2, r + 2)
                p.setPen(QPen(QColor("#ffffff")))
                p.setFont(QFont("Segoe UI", 9, QFont.Bold))
                p.drawText(QRectF(cx - r - 2, y - r - 2, (r + 2) * 2, (r + 2) * 2), Qt.AlignCenter, str(step_num))
            else:
                # Pending: Subtle light gray circle
                p.setBrush(QBrush(QColor("#f8fafc")))
                p.setPen(QPen(QColor("#cbd5e1"), 1.5))
                p.drawEllipse(QPointF(cx, y), r, r)
                p.setPen(QPen(QColor("#94a3b8")))
                p.setFont(QFont("Segoe UI", 8, QFont.Bold))
                p.drawText(QRectF(cx - r, y - r, r * 2, r * 2), Qt.AlignCenter, str(step_num))

            # Step title label underneath
            p.setFont(QFont("Segoe UI", 8, QFont.Bold if step_num == self.current_step else QFont.Normal))
            p.setPen(QPen(QColor("#0f172a") if step_num == self.current_step else QColor("#64748b")))
            p.drawText(QRectF(cx - 45, y + 15, 90, 26), Qt.AlignHCenter | Qt.AlignTop, step_name)

        p.end()


class ActivityLogWidget(QFrame):
    """Recent Activity & Logs feed with colored status dots and auto-scroll."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            ActivityLogWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Header
        top = QHBoxLayout()
        h_lbl = QLabel("Recent Activity / Logs")
        h_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        top.addWidget(h_lbl)
        top.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }
        """)
        clear_btn.clicked.connect(self.clear_logs)
        top.addWidget(clear_btn)
        root.addLayout(top)

        # Scroll Area for activities
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.entries_lay = QVBoxLayout(self.container)
        self.entries_lay.setContentsMargins(0, 0, 0, 0)
        self.entries_lay.setSpacing(8)
        self.entries_lay.addStretch()

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)

    def add_log(self, text: str, dot_type: str = "info"):
        time_str = QDateTime.currentDateTime().toString("hh:mm:ss")
        color = "#1677ff"  # blue
        if dot_type == "success" or "complete" in text.lower() or "saved" in text.lower():
            color = "#10b981"  # green
        elif dot_type == "warn" or "ready" in text.lower() or "waiting" in text.lower():
            color = "#f59e0b"  # amber
        elif dot_type == "error" or "error" in text.lower() or "fail" in text.lower():
            color = "#ef4444"  # red

        entry = QWidget()
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        # Dot
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 11px;")
        row.addWidget(dot)

        # Time
        t_lbl = QLabel(time_str)
        t_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-family: monospace;")
        row.addWidget(t_lbl)

        # Message
        msg_lbl = QLabel(text)
        msg_lbl.setStyleSheet("color: #1e293b; font-size: 12px;")
        msg_lbl.setWordWrap(True)
        row.addWidget(msg_lbl, 1)

        idx = max(0, self.entries_lay.count() - 1)
        self.entries_lay.insertWidget(idx, entry)

        QApplication.processEvents()
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def clear_logs(self):
        while self.entries_lay.count() > 1:
            item = self.entries_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ExclusionConfigDialog(QDialog):
    rules_saved = Signal(object)

    def __init__(self, current_rules: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Exclusion Conditions")
        self.setFixedSize(730, 480)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #1e3a5f;
                border-radius: 8px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Dark Navy Title Bar
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #1e3a5f; border-top-left-radius: 7px; border-top-right-radius: 7px;")
        title_lay = QHBoxLayout(title_bar)
        title_lay.setContentsMargins(14, 10, 14, 10)
        title_lay.setSpacing(10)

        gear_icon = QLabel()
        gear_icon.setPixmap(get_vector_icon("gear", "#ffffff", 18).pixmap(18, 18))
        title_lay.addWidget(gear_icon)

        t_lbl = QLabel("Configure Exclusion Conditions")
        t_lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700;")
        title_lay.addWidget(t_lbl)
        title_lay.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ffffff;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f87171;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_lay.addWidget(close_btn)
        root.addWidget(title_bar)

        # Body Container
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(20, 16, 20, 16)
        body_lay.setSpacing(14)

        desc = QLabel("Set the exclusion rules and thresholds to filter eligible parties for rebate calculation.")
        desc.setStyleSheet("color: #64748b; font-size: 12px;")
        body_lay.addWidget(desc)

        self.rows_data = [
            ("negative_balance_threshold", "Negative Balance Trigger", "Exclude parties with negative balance below this value"),
            ("walton_stock_threshold_normal", "Walton Minimum Stock", "Exclude parties with stock less than this value (Walton brands)"),
            ("marcel_stock_threshold_normal", "Marcel Minimum Stock", "Exclude parties with stock less than this value (Marcel brands)"),
            ("walton_stock_threshold_negative", "Negative Mode Threshold", "Exclude parties with negative mode beyond this threshold"),
            ("high_stock_multiplier", "High Stock Multiplier", "Identify unusually high stock levels (based on average)"),
            ("marcel_stock_threshold_negative", "Current Receiving Qty", "Exclude parties with receiving quantity less than this value"),
        ]

        self.controls = {}
        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(14)

        for i, (key, label_text, hint_text) in enumerate(self.rows_data):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #1e293b;")
            grid.addWidget(lbl, i, 0)

            chk = QCheckBox("Enable")
            chk.setChecked(True)
            chk.setStyleSheet("""
                QCheckBox { font-size: 12px; color: #475569; spacing: 8px; }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    background-color: #ffffff;
                }
                QCheckBox::indicator:checked {
                    background-color: #1677ff;
                    border-color: #1677ff;
                    image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAASUlEQVR4nO2PMQ4AIAgDW///57oSQBRHYzcIdynATzuSZOdxA1vJscBCJNkSrOBU4H+s4CDwP+5gAAhL36CCQ4PsuILLZE0ezQRLhS/6di1T+AAAAABJRU5ErkJggg==);
                }
            """)
            grid.addWidget(chk, i, 1)

            val_edit = QLineEdit(str(current_rules.get(key, 0.0)))
            val_edit.setFixedWidth(85)
            val_edit.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 6px; font-size: 12px; background: #ffffff;")
            grid.addWidget(val_edit, i, 2)

            hint = QLabel(hint_text)
            hint.setStyleSheet("color: #64748b; font-size: 11px;")
            grid.addWidget(hint, i, 3)

            self.controls[key] = (chk, val_edit)

        body_lay.addLayout(grid)
        body_lay.addStretch()

        # Footer Buttons
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 10, 0, 0)

        reset_btn = QPushButton(" Reset to Defaults")
        reset_btn.setIcon(get_vector_icon("refresh", "#2563eb", 14))
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #2563eb;
                border: 1px solid #bfdbfe;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #eff6ff;
            }
        """)
        reset_btn.clicked.connect(self.reset_defaults)
        footer.addWidget(reset_btn)

        footer.addStretch()

        save_btn = QPushButton(" Save Changes")
        save_btn.setIcon(get_vector_icon("save", "#ffffff", 14))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1677ff;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0958d9;
            }
        """)
        save_btn.clicked.connect(self.save)
        footer.addWidget(save_btn)

        cancel_btn = QPushButton(" Cancel")
        cancel_btn.setIcon(get_vector_icon("close", "#64748b", 12))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #475569;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)

        body_lay.addLayout(footer)
        root.addWidget(body)

        self.current_rules = current_rules

    def reset_defaults(self):
        from app.config.settings import DEFAULT_EXCLUSION_RULES
        for key, (_, edit) in self.controls.items():
            if key in DEFAULT_EXCLUSION_RULES:
                edit.setText(str(DEFAULT_EXCLUSION_RULES[key]))

    def save(self):
        try:
            d = {}
            for key, (chk, edit) in self.controls.items():
                d[key] = float(edit.text())
            d["negative_balance_mode"] = self.controls["negative_balance_threshold"][0].isChecked()
            d["apply_high_stock_rule"] = self.controls["high_stock_multiplier"][0].isChecked()
            self.rules_saved.emit(d)
            self.accept()
        except ValueError as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Input", f"Please ensure all thresholds are valid numbers: {e}")


class RebateConfigDialog(QDialog):
    rules_saved = Signal(object)

    def __init__(self, current_rules, parent=None):
        super().__init__(parent)
        from app.config.settings import DEFAULT_REBATE_RULES
        self.default_rules = [dict(rule) for rule in DEFAULT_REBATE_RULES]
        self.setWindowTitle("Configure Rebate Conditions")
        self.setFixedSize(620, 500)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(get_vector_icon("rebate", "#06b6d4", 22).pixmap(22, 22))
        header.addWidget(icon)
        title = QLabel("Configure Rebate Conditions")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        header.addWidget(title)
        header.addStretch()
        close = QPushButton("✕")
        close.setFixedSize(28, 28)
        close.clicked.connect(self.reject)
        header.addWidget(close)
        root.addLayout(header)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Minimum %", "Maximum %", "Rebate %"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        actions = QHBoxLayout()
        add = QPushButton("+ Add Rule")
        delete = QPushButton("Delete Rule")
        reset = QPushButton("Reset Defaults")
        save = QPushButton("Save Changes")
        actions.addWidget(add)
        actions.addWidget(delete)
        actions.addWidget(reset)
        actions.addStretch()
        actions.addWidget(save)
        root.addLayout(actions)
        add.clicked.connect(self.add_row)
        delete.clicked.connect(self.delete_row)
        reset.clicked.connect(lambda: self.render(self.default_rules))
        save.clicked.connect(self.save)
        self.render(current_rules or self.default_rules)

    def render(self, rules):
        self.table.setRowCount(0)
        for rule in rules:
            self.add_row(rule)

    def add_row(self, rule=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [
            "" if not rule or rule.get("min_percent") is None else rule["min_percent"],
            "" if not rule or rule.get("max_percent") is None else rule["max_percent"],
            "" if not rule else rule.get("rebate", ""),
        ]
        for column, value in enumerate(values):
            self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def delete_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def save(self):
        try:
            rules = []
            for row in range(self.table.rowCount()):
                value = lambda column: self.table.item(row, column).text().strip()
                rules.append({
                    "min_percent": float(value(0)) if value(0) else None,
                    "max_percent": float(value(1)) if value(1) else None,
                    "rebate": float(value(2)),
                })
            if not rules:
                raise ValueError("At least one rebate rule is required.")
            self.rules_saved.emit(rules)
            self.accept()
        except (TypeError, ValueError) as error:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Rebate Rule", str(error))


class DataFrameTableModel(QAbstractTableModel):
    def __init__(self, dataframe=None, parent=None):
        super().__init__(parent)
        self._raw_df = dataframe if isinstance(dataframe, pd.DataFrame) else pd.DataFrame()
        self._filtered_df = self._raw_df
        self._filter_text = ""
        self._columns = []
        self._data = np.empty((0, 0), dtype=object)
        self._rebuild_cache()

    @property
    def dataframe(self):
        return self._raw_df

    def _rebuild_cache(self):
        self._columns = [str(c) for c in self._filtered_df.columns]
        self._data = self._filtered_df.to_numpy()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        value = self._data[index.row(), index.column()]
        if pd.isna(value):
            return ""
        if isinstance(value, (float, np.floating)):
            return f"{value:,.2f}"
        return str(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._columns[section] if section < len(self._columns) else ""
        return str(section + 1)

    def set_dataframe(self, dataframe):
        self.beginResetModel()
        self._raw_df = dataframe if isinstance(dataframe, pd.DataFrame) else pd.DataFrame()
        if self._filter_text:
            self._apply_filter(self._filter_text)
        else:
            self._filtered_df = self._raw_df
            self._rebuild_cache()
        self.endResetModel()

    def set_df(self, df):
        self.set_dataframe(df)

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
        else:
            t = text.lower()
            masks = [
                self._raw_df[col].astype(str).str.lower().str.contains(t, regex=False, na=False)
                for col in self._raw_df.columns
            ]
            combined_mask = np.logical_or.reduce(masks)
            self._filtered_df = self._raw_df[combined_mask]
        self._rebuild_cache()


# class GroupedPartiesPlaceholderTab(QWidget):
#     """
#     Dedicated Grouped Parties tab as requested by the user:
#     'and for the group party data show I will implement that feature by myself later You just add the tab for now.'
#     """
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         lay = QVBoxLayout(self)
#         lay.setContentsMargins(16, 16, 16, 16)
#         lay.setSpacing(12)

#         # Header card
#         header_card = QFrame()
#         header_card.setStyleSheet("""
#             QFrame {
#                 background-color: #ffffff;
#                 border: 1px solid #e2e8f0;
#                 border-radius: 8px;
#                 padding: 12px 16px;
#             }
#         """)
#         h_lay = QHBoxLayout(header_card)
#         h_lay.setContentsMargins(0, 0, 0, 0)

#         t_lay = QVBoxLayout()
#         t_lbl = QLabel("Grouped Parties Management")
#         t_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
#         t_lay.addWidget(t_lbl)
#         h_lay.addLayout(t_lay)
#         h_lay.addStretch()
#         lay.addWidget(header_card)

#         # Search bar
#         search_row = QHBoxLayout()
#         self.search = QLineEdit()
#         self.search.setPlaceholderText("Search grouped parties (Group ID, Party Code, Zone)...")
#         self.search.setStyleSheet("""
#             QLineEdit {
#                 background-color: #ffffff;
#                 border: 1px solid #cbd5e1;
#                 border-radius: 6px;
#                 padding: 6px 12px;
#                 font-size: 12px;
#             }
#         """)
#         search_row.addWidget(self.search)
#         lay.addLayout(search_row)

#         # Table widget with standard grouped parties columns
#         self.model = DataFrameTableModel(parent=self)

#         self.table = QTableView()
#         self.table.setModel(self.model)
#         self.table.setSortingEnabled(True)
#         self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
#         self.table.horizontalHeader().setStretchLastSection(True)
#         self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
#         self.table.setAlternatingRowColors(True)

#         self.search_timer = QTimer(self)
#         self.search_timer.setSingleShot(True)
#         self.search_timer.setInterval(150)
#         self.search_timer.timeout.connect(lambda: self.model.filter_text(self.search.text()))
#         self.search.textChanged.connect(self.search_timer.start)
#         lay.addWidget(self.table)

#         # Bottom note
#         note = QLabel("ℹ This tab is scaffolded and ready for your custom data loading and display logic.")
#         note.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
#         lay.addWidget(note)
#         self.note = note
#         self.pending_df = None
#         self.has_pending_data = False

#     def set_data(self, data):
#         if data is None or not hasattr(data, "columns"):
#             self.pending_df = pd.DataFrame()
#             self.has_pending_data = True
#             self.note.setText("No grouped party data available.")
#             return

#         self.pending_df = data
#         self.has_pending_data = True
#         self.note.setText(f"Grouped party information ({len(data):,} rows) after stock, lifting, receivable, and inventory aggregation.")

#     def load_pending_data(self):
#         if self.has_pending_data:
#             self.model.set_dataframe(self.pending_df)
#             self.pending_df = None
#             self.has_pending_data = False
