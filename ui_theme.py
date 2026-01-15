from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtWidgets import QPushButton, QGraphicsOpacityEffect

# Единые цвета и стили для всего приложения
PRIMARY = "#2563EB"
PRIMARY_HOVER = "#3B82F6"
PRIMARY_PRESSED = "#1E3A8A"
BACKGROUND = "#F5F7FB"
CARD = "#FFFFFF"
TEXT = "#1F2937"
BORDER = "#E5E7EB"

# Базовый глобальный стиль: применяется ко всем окнам и виджетам
GLOBAL_STYLE = f"""
* {{
    font-family: 'Segoe UI', 'Arial', sans-serif;
}}
QMainWindow, QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-size: 14px;
}}
QLabel {{
    color: {TEXT};
}}
QLineEdit, QComboBox, QTextEdit, QDateEdit {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    padding: 10px;
    border-radius: 10px;
    selection-background-color: #DBEAFE;
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDateEdit:focus {{
    border: 1px solid {PRIMARY};
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}}
QPushButton {{
    background-color: {PRIMARY};
    color: white;
    border: none;
    padding: 10px 18px;
    border-radius: 10px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton:pressed {{
    background-color: {PRIMARY_PRESSED};
}}
QGroupBox {{
    border: none;
    border-radius: 12px;
    margin-top: 8px;
    padding: 16px;
    background-color: {CARD};
    box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.05);
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: {PRIMARY};
}}
QTableView, QListWidget {{
    gridline-color: {BORDER};
    background-color: {CARD};
    alternate-background-color: #F8FAFC;
    selection-background-color: #DBEAFE;
    selection-color: {TEXT};
    border-radius: 12px;
    border: none;
}}
QListWidget::item {{
    padding: 8px 10px;
}}
QHeaderView::section {{
    background-color: #E3F2FD;
    padding: 10px;
    border: none;
    border-right: 1px solid #B3E5FC;
    border-bottom: 2px solid {PRIMARY};
    font-weight: 600;
}}
QTreeView {{
    background-color: {CARD};
    alternate-background-color: #F8FAFC;
    selection-background-color: #DBEAFE;
    border-radius: 12px;
    border: none;
}}
QToolBar {{
    background-color: #E3F2FD;
    padding: 6px;
    border: none;
}}
QMenu {{
    background-color: {CARD};
    border: 1px solid {BORDER};
}}
QMenu::item {{
    padding: 8px 14px;
}}
QMenu::item:selected {{
    background-color: #EFF6FF;
}}
"""


def apply_global_style(widget, extra: str = "") -> None:
    """Применить единый стиль к окну/виджету с опциональным дополнением."""
    widget.setStyleSheet(GLOBAL_STYLE + (extra or ""))


class AnimatedButton(QPushButton):
    """Кнопка с плавной анимацией наведения/нажатия в едином стиле."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)

        self.hover_animation = QPropertyAnimation(self.effect, b"opacity")
        self.hover_animation.setDuration(180)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._pressed_timer = QTimer(self)
        self._pressed_timer.setSingleShot(True)
        self._pressed_timer.timeout.connect(self._reset_press_effect)

    # Hover effects removed as requested
    # def enterEvent(self, event):
    #     self.hover_animation.stop()
    #     self.hover_animation.setStartValue(self.effect.opacity())
    #     self.hover_animation.setEndValue(0.85)
    #     self.hover_animation.start()
    #     super().enterEvent(event)

    # def leaveEvent(self, event):
    #     self.hover_animation.stop()
    #     self.hover_animation.setStartValue(self.effect.opacity())
    #     self.hover_animation.setEndValue(1.0)
    #     self.hover_animation.start()
    #     super().leaveEvent(event)

    def mousePressEvent(self, event):
        # Небольшой визуальный отклик при нажатии
        base_style = self.styleSheet()
        self.setStyleSheet(base_style + "filter: brightness(0.9);")
        self._pressed_timer.start(140)
        super().mousePressEvent(event)

    def _reset_press_effect(self):
        self.setStyleSheet(self.styleSheet().replace("filter: brightness(0.9);", ""))

