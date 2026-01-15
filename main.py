import faulthandler
import logging
import os
import sys

import PyQt6

from main_menu import MainMenu
from ui_theme import GLOBAL_STYLE

faulthandler.enable()

if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

os.makedirs(os.path.join(app_dir, 'data'), exist_ok=True)
os.makedirs(os.path.join(app_dir, 'logs'), exist_ok=True)
os.makedirs(os.path.join(app_dir, 'exports'), exist_ok=True)

logging.basicConfig(
    filename=os.path.join(app_dir, 'logs', 'archive.log'),
    filemode="a",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Запуск приложения")
    app = PyQt6.QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)
    app.setQuitOnLastWindowClosed(True)
    menu = MainMenu()
    menu.show()
    sys.exit(app.exec())
