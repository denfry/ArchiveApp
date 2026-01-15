import logging

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel,
    QFrame
)

from edit_window import EditWindow
from registry_window import RegistryWindow
from view_window import ViewWindow
from ui_theme import AnimatedButton

logger = logging.getLogger(__name__)


class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        self.edit_window = EditWindow(main_menu=self)
        self.view_window = ViewWindow(main_menu=self)
        self.registry_window = RegistryWindow(main_menu=self)
        self.setWindowTitle("Архив документов")
        self.setWindowIcon(QIcon("icon.png"))
        self.resize(450, 400)
        self._setup_ui()
        self._setup_fade_in()

    def _setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        header = QLabel("📂 Архив документов")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        layout.addWidget(header)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #B0BEC5;")
        layout.addWidget(line)

        btn_view = AnimatedButton("📖 Просмотр архива")
        btn_edit = AnimatedButton("✏️ Редактирование")
        btn_registry = AnimatedButton("📋 Реестр")
        btn_exit = AnimatedButton("🚪 Выход")

        for btn in (btn_view, btn_edit, btn_registry, btn_exit):
            btn.setFixedSize(220, 48)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_view.clicked.connect(self.open_view)
        btn_edit.clicked.connect(self.open_edit)
        btn_registry.clicked.connect(self.open_registry)
        btn_exit.clicked.connect(self.close)

        footer = QLabel("© 2025 Юрков Д.А.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #90A4AE; font-size: 12px; margin-top: 20px;")
        layout.addWidget(footer)

        self.setCentralWidget(central)

    def _setup_fade_in(self):
        self.setWindowOpacity(0)
        self.fade = QPropertyAnimation(self, b"windowOpacity")
        self.fade.setDuration(700)
        self.fade.setStartValue(0)
        self.fade.setEndValue(1)
        self.fade.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade.start()

    def open_view(self):
        self.hide()
        self.view_window.show()

    def open_edit(self):
        self.hide()
        self.edit_window.show()

    def open_registry(self):
        self.hide()
        self.registry_window.show()
