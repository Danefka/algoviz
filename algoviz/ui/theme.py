"""One neutral palette for the home screen, player and optional dialogs."""

STYLESHEET = """
QWidget { background: #FFFFFF; color: #24262B; font-size: 14px; }
QLabel#title { font-size: 30px; font-weight: 600; }
QLabel#section { font-size: 18px; font-weight: 600; }
QLabel#muted { color: #878C96; font-size: 12px; }
QLabel#speedValue { background: #F1F3F6; border-radius: 6px; padding: 3px 7px; font-weight: 600; }
QLabel#error { color: #AD3E3E; font-size: 12px; }
QPushButton, QToolButton { border: 1px solid #E4E6EA; background: #FFFFFF;
    border-radius: 7px; padding: 9px 14px; }
QPushButton:hover, QToolButton:hover { background: #F5F6F8; }
QPushButton:focus, QToolButton:focus { border-color: #929AA8; }
QPushButton#primary { background: #292D35; color: white; border-color: #292D35; }
QPushButton#primary:hover { background: #414752; }
QPushButton#quiet, QToolButton { border: none; color: #6D737D; }
QToolButton::menu-indicator { image: none; }
QPushButton#algorithm { text-align: left; padding: 20px; font-size: 16px; }
QPushButton:disabled { color: #B4B8C0; background: #F6F7F8; border-color: #ECEEF1; }
QLineEdit, QComboBox { border: 1px solid #E4E6EA; border-radius: 6px; padding: 10px; }
QLineEdit:focus { border-color: #929AA8; }
QMenu { background: white; border: 1px solid #E4E6EA; padding: 6px; }
QMenu::item { padding: 8px 28px 8px 20px; }
QMenu::item:selected { background: #F1F3F6; }
QMenu::separator { height: 1px; background: #ECEEF1; margin: 6px; }
QSlider::groove:horizontal { height: 3px; background: #ECEEF1; border-radius: 1px; }
QSlider::sub-page:horizontal { background: #929AA8; }
QSlider::handle:horizontal { background: #525A68; width: 11px; margin: -4px 0; border-radius: 5px; }
QProgressBar { border: 0; background: #ECEEF1; min-height: 5px; max-height: 5px; }
QProgressBar::chunk { background: #626D80; }
QPlainTextEdit { border: 1px solid #E4E6EA; padding: 8px; font-size: 11px; }
QToolTip { background: #292D35; color: white; border: 0; padding: 5px; }
"""
