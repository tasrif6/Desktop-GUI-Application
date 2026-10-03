MAIN_STYLESHEET = """
/* Global Settings */
QWidget {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif;
    font-size: 13px;
    color: #1e293b;
}

QMainWindow, QDialog {
    background-color: #f1f5f9;
}

#CentralWidget {
    background-color: #f1f5f9;
}

#MainContentArea {
    background-color: #f1f5f9;
}

/* Custom Title Bar */
#CustomTitleBar {
    background-color: #0b1727;
    border-bottom: 1px solid #1e293b;
}

#CustomTitleBar QLabel {
    background-color: transparent;
    color: #ffffff;
}

#CustomTitleBar QPushButton {
    background-color: transparent;
}

/* Left Navigation Sidebar */
#SidebarContainer {
    background-color: #0b1727;
    border-right: 1px solid #1e293b;
}

#SidebarLogoTitle {
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
}

#SidebarContainer QPushButton.nav-btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 500;
}

#SidebarContainer QPushButton.nav-btn:hover {
    background-color: #1e293b;
    color: #f8fafc;
}

#SidebarContainer QPushButton.nav-btn:checked {
    background-color: #1677ff;
    color: #ffffff;
    font-weight: 600;
}

#SidebarContainer QPushButton.nav-about-btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 8px 14px;
    font-size: 13px;
}

#SidebarContainer QPushButton.nav-about-btn:hover {
    background-color: #1e293b;
    color: #f8fafc;
}

/* Top Filter / Control Bar */
#TopFilterBar {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 14px;
}

QLabel.filter-label {
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 2px;
}

QComboBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 20px;
    color: #0f172a;
}

QComboBox:focus, QLineEdit:focus {
    border: 1px solid #1677ff;
    background-color: #ffffff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: none;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    selection-background-color: #e0f2fe;
    selection-color: #0369a1;
    border-radius: 6px;
    padding: 4px;
}

/* Buttons */
QPushButton[class="btn-primary"] {
    background-color: #1677FF;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 22px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton[class="btn-primary"]:hover {
    background-color: #0958D9;
}

QPushButton[class="btn-primary"]:pressed {
    background-color: #003EB3;
}

QPushButton[class="btn-primary"]:disabled {
    background-color: #93C5FD;
    color: #F8FAFC;
}


QPushButton.btn-secondary {
    background-color: #e2e8f0;
    color: #475569;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.btn-secondary:hover {
    background-color: #cbd5e1;
    color: #1e293b;
}

QPushButton.btn-secondary:pressed {
    background-color: #94a3b8;
}


QPushButton[class="btn-success"] {
    background-color: #10b981;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton[class="btn-success"]:hover {
    background-color: #059669;
}

QPushButton[class="btn-success"]:pressed {
    background-color: #047857;
}

QPushButton[class="btn-success"]:disabled {
    background-color: #6ee7b7;
    color: #f0fdf4;
}

QPushButton.btn-outline {
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton.btn-outline:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
}

/* Card Panels */
QFrame.card-panel {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}

/* Step 1 Configuration Banner */
#Step1Banner {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 16px;
}

/* Stepper info box */
#StepInfoBox {
    background-color: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 8px;
    padding: 8px 12px;
}

/* Latest Run info */
#RunInfoCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 14px;
}

/* Table Views */
QTableView, QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #e0f2fe;
    selection-color: #0f172a;
    alternate-background-color: #f8fafc;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-size: 12px;
    font-weight: 600;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    border-right: 1px solid #f1f5f9;
    padding: 8px 10px;
}

QScrollBar:vertical {
    background: #f1f5f9;
    width: 8px;
    border-radius: 4px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #f1f5f9;
    height: 8px;
    border-radius: 4px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #cbd5e1;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    color: #334155;
    font-size: 13px;
}

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
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiI+PHBhdGggZD0iTTMgOC41TDYuNSAxMkwxMyA0LjUiIGZpbGw9Im5vbmUiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMi4yIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
}

/* Log Box */
QTextEdit.log-view {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    color: #334155;
}
"""
