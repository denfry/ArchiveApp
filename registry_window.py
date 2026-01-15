import logging
import uuid
import weakref

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSortFilterProxyModel
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QTableView,
    QMessageBox, QHBoxLayout, QLineEdit, QHeaderView, QDialog,
    QFormLayout, QDialogButtonBox, QTextEdit, QDateEdit, QLabel, QComboBox
)
from PyQt6.QtCore import QDate

from data_manager import DataManager
from models import QAbstractTableModel
from ui_theme import apply_global_style

logger = logging.getLogger(__name__)


class AddDocumentDialog(QDialog):
    """Диалог для удобного добавления документа с несколькими полями."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить документ в реестр")
        self.setModal(True)
        self.resize(500, 400)
        apply_global_style(self)

        layout = QFormLayout(self)

        # Название документа (многострочное поле)
        name_label = QLabel("Название документа:")
        name_label.setStyleSheet("font-weight: bold;")
        self.name_edit = QTextEdit()
        self.name_edit.setPlaceholderText("Введите полное название документа...\n(можно использовать несколько строк)")
        self.name_edit.setMaximumHeight(100)
        self.name_edit.setFont(QFont("Arial", 11))
        layout.addRow(name_label, self.name_edit)

        # Тип документа
        type_label = QLabel("Тип документа:")
        self.type_edit = QLineEdit()
        self.type_edit.setText("Документ")
        self.type_edit.setPlaceholderText("Тип документа")
        layout.addRow(type_label, self.type_edit)

        # Номер документа
        doc_number_label = QLabel("Номер документа:")
        self.doc_number_edit = QLineEdit()
        self.doc_number_edit.setPlaceholderText("Например: №123-ФЗ")
        layout.addRow(doc_number_label, self.doc_number_edit)

        # Дата подписания
        sign_date_label = QLabel("Дата подписания:")
        self.sign_date_edit = QDateEdit()
        self.sign_date_edit.setCalendarPopup(True)
        self.sign_date_edit.setDate(QDate.currentDate())
        self.sign_date_edit.setDisplayFormat("dd.MM.yyyy")
        layout.addRow(sign_date_label, self.sign_date_edit)

        # Статус
        status_label = QLabel("Статус:")
        self.status_edit = QLineEdit()
        self.status_edit.setText("Ожидает размещения")
        self.status_edit.setPlaceholderText("Статус документа")
        layout.addRow(status_label, self.status_edit)

        # Категория инженерных систем
        category_label = QLabel("Категория:")
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Не указана",
            "ТС - Теплосеть",
            "ВО - Хоз. бытовая канализация",
            "ВС - Водоснабжение",
            "ЛК - Ливневая канализация",
            "УУТЭ",
            "УУХВС"
        ])
        layout.addRow(category_label, self.category_combo)

        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def get_data(self):
        """Возвращает введенные данные."""
        category_text = self.category_combo.currentText()
        # Извлекаем только код категории (до " -")
        category = category_text.split(" -")[0].strip() if category_text != "Не указана" else ""

        return {
            'name': self.name_edit.toPlainText().strip(),
            'type': self.type_edit.text().strip(),
            'doc_number': self.doc_number_edit.text().strip(),
            'sign_date': self.sign_date_edit.date().toString("dd.MM.yyyy"),
            'status': self.status_edit.text().strip(),
            'category': category
        }


class RegistryWindow(QMainWindow):
    """Window for managing incoming documents before archiving."""

    def __init__(self, main_menu=None):
        super().__init__()
        self.main_menu = weakref.ref(main_menu) if main_menu else None
        self.setWindowTitle("Реестр принесенных документов")
        self.resize(1200, 700)
        logger.info("Инициализация RegistryWindow начата")

        self.manager = DataManager()
        self._create_registry_table()
        self._setup_ui()
        self.refresh_data()
        self._animate_window()

    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        apply_global_style(self)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Поле поиска с улучшенным дизайном
        search_container = QHBoxLayout()
        search_label = QLabel("🔍 Поиск:")
        search_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Поиск по названию, номеру, типу, статусу...")
        self.search_line.textChanged.connect(self.filter_table)
        self.search_line.setClearButtonEnabled(True)
        search_container.addWidget(search_label)
        search_container.addWidget(self.search_line)
        layout.addLayout(search_container)

        # Таблица
        self.table = QTableView()
        self.model = RegistryTableModel(self.manager)
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)  # Поиск по всем колонкам
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.table.setModel(self.proxy_model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setFont(QFont("Arial", 12))
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        layout.addWidget(self.table)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.add_btn = QPushButton("➕ Добавить документ")
        self.add_btn.setToolTip("Добавить новый документ в реестр")
        self.add_btn.setFixedSize(180, 45)

        self.edit_btn = QPushButton("✏️ Редактировать")
        self.edit_btn.setToolTip("Редактировать выбранный документ")
        self.edit_btn.setFixedSize(160, 45)

        self.del_btn = QPushButton("🗑️ Удалить")
        self.del_btn.setToolTip("Удалить выбранный документ")
        self.del_btn.setFixedSize(140, 45)

        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setToolTip("Обновить данные таблицы")
        self.refresh_btn.setFixedSize(140, 45)

        self.back_btn = QPushButton("⬅️ Главное меню")
        self.back_btn.setToolTip("Вернуться в главное меню")
        self.back_btn.setFixedSize(160, 45)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.back_btn)
        layout.addLayout(btn_layout)

        # Подключение сигналов
        self.add_btn.clicked.connect(self.add_document)
        self.edit_btn.clicked.connect(self.edit_document)
        self.del_btn.clicked.connect(self.delete_document)
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.back_btn.clicked.connect(self.back_to_menu)

        self.setCentralWidget(central)

    def _create_registry_table(self):
        """Создание таблицы реестра в БД."""
        try:
            cursor = self.manager.conn.cursor()
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS registry
                           (
                               id
                               TEXT
                               PRIMARY
                               KEY,
                               name
                               TEXT
                               NOT
                               NULL,
                               type
                               TEXT
                               DEFAULT
                               'Документ',
                               doc_number
                               TEXT,
                               sign_date
                               TEXT,
                               status
                               TEXT
                               DEFAULT
                               'Ожидает размещения',
                               category
                               TEXT
                           )
                           """)

            # Проверяем, существует ли колонка category, если нет - добавляем
            cursor.execute("PRAGMA table_info(registry)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'category' not in columns:
                cursor.execute("ALTER TABLE registry ADD COLUMN category TEXT")
                logger.info("Добавлена колонка 'category' в таблицу registry")

            self.manager.conn.commit()
            logger.info("Таблица реестра создана/проверена")
        except Exception as e:
            logger.error(f"Ошибка создания таблицы реестра: {e}")

    def refresh_data(self):
        """Обновление данных в таблице."""
        self.model.refresh()
        QTimer.singleShot(100, self.table.resizeColumnsToContents)
        logger.info("Данные реестра обновлены")

    def add_document(self):
        """Добавление нового документа через диалог."""
        dialog = AddDocumentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['name']:
                QMessageBox.warning(self, "Ошибка", "Название документа обязательно!")
                return

            try:
                el_id = str(uuid.uuid4())
                cursor = self.manager.conn.cursor()
                cursor.execute(
                    """INSERT INTO registry (id, name, type, doc_number, sign_date, status, category)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (el_id, data['name'], data['type'], data['doc_number'],
                     data['sign_date'], data['status'], data['category'])
                )
                self.manager.conn.commit()
                self.refresh_data()
                logger.info(f"Документ добавлен в реестр: {data['name']}")
                QMessageBox.information(self, "Успех", "Документ успешно добавлен!")
            except Exception as e:
                logger.error(f"Ошибка добавления в реестр: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить документ:\n{str(e)}")

    def edit_document(self):
        """Редактирование выбранного документа."""
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "Ошибка", "Выберите документ для редактирования")
            return

        proxy_index = indexes[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        el_id = self.model.get_id_by_row(source_index.row())

        # Получаем текущие данные
        try:
            cursor = self.manager.conn.cursor()
            cursor.execute("SELECT name, type, doc_number, sign_date, status, category FROM registry WHERE id=?",
                           (el_id,))
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Ошибка", "Документ не найден")
                return

            dialog = AddDocumentDialog(self)
            dialog.setWindowTitle("Редактировать документ")
            dialog.name_edit.setPlainText(row[0])
            dialog.type_edit.setText(row[1] or "Документ")
            dialog.doc_number_edit.setText(row[2] or "")
            if row[3]:
                date = QDate.fromString(row[3], "dd.MM.yyyy")
                if date.isValid():
                    dialog.sign_date_edit.setDate(date)
            dialog.status_edit.setText(row[4] or "Ожидает размещения")

            # Установка категории
            category = row[5] or ""
            if category:
                # Ищем соответствующий пункт в комбобоксе
                for i in range(dialog.category_combo.count()):
                    if dialog.category_combo.itemText(i).startswith(category):
                        dialog.category_combo.setCurrentIndex(i)
                        break

            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if not data['name']:
                    QMessageBox.warning(self, "Ошибка", "Название документа обязательно!")
                    return

                cursor.execute(
                    """UPDATE registry
                       SET name=?,
                           type=?,
                           doc_number=?,
                           sign_date=?,
                           status=?,
                           category=?
                       WHERE id = ?""",
                    (data['name'], data['type'], data['doc_number'],
                     data['sign_date'], data['status'], data['category'], el_id)
                )
                self.manager.conn.commit()
                self.refresh_data()
                logger.info(f"Документ обновлен: {el_id}")
                QMessageBox.information(self, "Успех", "Документ успешно обновлен!")
        except Exception as e:
            logger.error(f"Ошибка редактирования документа: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить документ:\n{str(e)}")

    def delete_document(self):
        """Удаление выбранного документа."""
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "Ошибка", "Выберите документ для удаления")
            return

        proxy_index = indexes[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        el_id = self.model.get_id_by_row(source_index.row())

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить этот документ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.manager.delete_from_registry(el_id)
                self.refresh_data()
                logger.info(f"Документ удален из реестра: {el_id}")
                QMessageBox.information(self, "Успех", "Документ удален!")
            except Exception as e:
                logger.error(f"Ошибка удаления из реестра: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить документ:\n{str(e)}")

    def filter_table(self):
        """Фильтрация таблицы по поисковому запросу."""
        search_text = self.search_line.text().strip()
        self.proxy_model.setFilterRegularExpression(search_text)

    def back_to_menu(self):
        """Возврат в главное меню."""
        self.hide()
        if self.main_menu and self.main_menu():
            self.main_menu().show()

    def _animate_window(self):
        """Анимация появления окна."""
        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(400)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()


class RegistryTableModel(QAbstractTableModel):
    """Модель таблицы для реестра документов."""

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.headers = ["ID", "Название", "Тип", "Номер документа", "Дата подписания", "Статус", "Категория"]
        self.filtered_elements = []
        self.refresh()

    def rowCount(self, parent=None):
        return len(self.filtered_elements)

    def columnCount(self, parent=None):
        return len(self.headers)

    def get_id_by_row(self, row):
        if 0 <= row < len(self.filtered_elements):
            return self.filtered_elements[row].get("ID")
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self.filtered_elements):
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            key = self.headers[index.column()]
            value = self.filtered_elements[index.row()].get(key, "")
            return str(value) if value else ""
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Arial", 12)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    def refresh(self):
        """Обновление данных модели."""
        self.beginResetModel()
        self.filtered_elements = self.manager.load_registry()
        self.endResetModel()
