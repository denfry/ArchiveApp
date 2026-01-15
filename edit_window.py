import logging
import os
import weakref

import psutil
from PyQt6.QtCore import Qt, QItemSelectionModel, QSortFilterProxyModel, QSettings, QPropertyAnimation, \
    QEasingCurve
from PyQt6.QtGui import QAction, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QTableView, QSplitter,
    QTreeView, QMessageBox, QMenu, QAbstractItemView, QHeaderView,
    QHBoxLayout, QLineEdit, QDialog, QLabel,
    QListWidget, QListWidgetItem, QCheckBox
)

from data_manager import DataManager, get_category_description
from dialogs import AddEditDialog
from models import ElementsTableModel
from ui_theme import AnimatedButton, apply_global_style

logger = logging.getLogger(__name__)


def log_memory_usage():
    """Логирование использования памяти."""
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        logger.info(f"Использование памяти: {mem_info.rss / 1024 / 1024:.2f} MB")
    except Exception as e:
        logger.warning(f"Не удалось получить данные о памяти: {e}")


class ImportFromRegistryDialog(QDialog):
    """Диалог выбора документов для импорта из реестра."""

    def __init__(self, registry_elements, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт из реестра")
        self.setModal(True)
        self.resize(700, 500)
        self.registry_elements = registry_elements
        self.selected_items = []
        layout = QVBoxLayout(self)
        header = QLabel(f"📥 Выберите документы для импорта ({len(registry_elements)} доступно)")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("✅ Выбрать все")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QPushButton("❌ Снять все")
        deselect_all_btn.clicked.connect(self._deselect_all)
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(deselect_all_btn)
        select_layout.addStretch()
        layout.addLayout(select_layout)
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        for reg_el in registry_elements:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            category = reg_el.get('Категория', '')
            category_icon = self._get_category_icon(category)
            title = QLabel(f"{category_icon} <b>{reg_el['Название']}</b>")
            title.setWordWrap(True)
            # Изменение: Используем get_category_description для множественных категорий
            category_display = get_category_description(category)
            info = QLabel(
                f"Тип: {reg_el.get('Тип', 'Документ')} | "
                f"Номер: {reg_el.get('Номер документа', 'Нет')} | "
                f"Дата: {reg_el.get('Дата подписания', 'Нет')} | "
                f"Категория: {category_display}"
            )
            info.setStyleSheet("color: #666; font-size: 11px;")
            row_layout = QHBoxLayout()
            row_layout.addWidget(checkbox)
            col_layout = QVBoxLayout()
            col_layout.addWidget(title)
            col_layout.addWidget(info)
            row_layout.addLayout(col_layout)
            row_layout.addStretch()
            item_layout.addLayout(row_layout)
            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, reg_el)
            list_item.setData(Qt.ItemDataRole.UserRole + 1, checkbox)
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
        layout.addWidget(self.list_widget)
        button_layout = QHBoxLayout()
        import_btn = QPushButton("📥 Импортировать выбранные")
        import_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("❌ Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(import_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        apply_global_style(self)

    def _get_category_icon(self, category):
        """Получение иконки для категории (берём первую, если несколько)."""
        icons = {
            "ТС": "🔥",
            "ВО": "🚽",
            "ВС": "💧",
            "ЛК": "🌧",
            "УУТЭ": "📏",
            "УУХВС": "🚰"
        }
        first_category = category.split(",")[0].strip() if category else ""
        return icons.get(first_category, "🔖")

    def _select_all(self):
        """Выбрать все элементы."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item).findChild(QCheckBox)
            checkbox.setChecked(True)

    def _deselect_all(self):
        """Снять выбор со всех элементов."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item).findChild(QCheckBox)
            checkbox.setChecked(False)

    def get_selected_items(self):
        """Получить выбранные элементы."""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = item.data(Qt.ItemDataRole.UserRole + 1)
            if checkbox.isChecked():
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected


class EditWindow(QMainWindow):
    """Окно редактирования архива."""

    def __init__(self, main_menu=None):
        super().__init__()
        self.main_menu = weakref.ref(main_menu) if main_menu else None
        self.setWindowTitle("Редактирование архива")
        self.resize(1200, 700)
        self.manager = DataManager()
        self._updating = False
        self._setup_styles()
        self._init_models()
        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_ui()
        self.refresh_data()
        self._animate_window()
        log_memory_usage()

    def _setup_styles(self):
        """Настройка стилей."""
        apply_global_style(self)

    def _init_models(self):
        """Инициализация моделей."""
        self.model = ElementsTableModel(self.manager)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Иерархия архива"])

    def _create_actions(self):
        """Создание действий для меню."""
        self.add_action = QAction("➕ Добавить", self)
        self.add_action.triggered.connect(self.add_element)
        self.edit_action = QAction("✏ Редактировать", self)
        self.edit_action.triggered.connect(self.edit_element)
        self.delete_action = QAction("🗑 Удалить", self)
        self.delete_action.triggered.connect(self.delete_element)
        self.import_action = QAction("📥 Импорт из реестра", self)
        self.import_action.triggered.connect(self.import_from_registry)
        self.refresh_action = QAction("🔄 Обновить", self)
        self.refresh_action.triggered.connect(self.refresh_data)
        self.back_action = QAction("⬅ Назад в меню", self)
        self.back_action.triggered.connect(self.back_to_menu)

    def _create_menu_bar(self):
        """Создание меню."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("📁 Файл")
        file_menu.addAction(self.import_action)
        file_menu.addSeparator()
        file_menu.addAction(self.back_action)
        edit_menu = menu_bar.addMenu("✏ Редактирование")
        edit_menu.addAction(self.add_action)
        edit_menu.addAction(self.edit_action)
        edit_menu.addAction(self.delete_action)
        view_menu = menu_bar.addMenu("🔍 Вид")
        view_menu.addAction(self.refresh_action)

    def _create_tool_bar(self):
        """Создание панели инструментов с AnimatedButton."""
        toolbar = self.addToolBar("Основная панель")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setStyleSheet("QToolBar { background-color: #E3F2FD; padding: 6px; }")

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        buttons = [
            ("➕ Добавить", self.add_element),
            ("✏ Редактировать", self.edit_element),
            ("🗑 Удалить", self.delete_element),
            ("📥 Импорт", self.import_from_registry),
            ("🔄 Обновить", self.refresh_data),
            ("⬅ Назад", self.back_to_menu)
        ]

        for text, slot in buttons:
            btn = AnimatedButton(text)
            btn.setFixedHeight(34)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-weight: bold;
                    color: #1976D2;
                }
                QPushButton:hover {
                    background-color: #BBDEFB;
                }
            """)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        toolbar.addWidget(container)

    def _create_ui(self):
        """Создание пользовательского интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию...")
        self.search_input.textChanged.connect(self._filter_table)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self.edit_element)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tree = QTreeView()
        self.tree.setModel(self.tree_model)
        self.tree.setAlternatingRowColors(True)
        self.tree.doubleClicked.connect(self._on_tree_double_click)
        splitter.addWidget(self.table)
        splitter.addWidget(self.tree)
        splitter.setSizes([800, 400])
        main_layout.addWidget(splitter)

    def _filter_table(self):
        """Фильтрация таблицы по поисковому запросу."""
        self.proxy_model.setFilterWildcard(self.search_input.text())

    def add_element(self):
        """Добавление нового элемента."""
        try:
            dialog = AddEditDialog(self.manager, parent=self)
            if dialog.exec():
                self.refresh_data()
                if dialog.new_element_id:
                    self._select_row_by_id(dialog.new_element_id)
                logger.info("Элемент успешно добавлен")
        except Exception as e:
            logger.error(f"Ошибка при добавлении элемента: {e}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def edit_element(self):
        """Редактирование выбранного элемента."""
        try:
            selected = self.table.selectionModel().selectedRows()
            if not selected:
                QMessageBox.warning(self, "Предупреждение", "Выберите элемент для редактирования")
                return
            row = self.proxy_model.mapToSource(selected[0]).row()
            el_id = self.model.get_id_by_row(row)
            if not el_id:
                QMessageBox.warning(self, "Ошибка", "Не удалось определить элемент")
                return
            element = self.manager.find_by_id(el_id)
            if not element:
                QMessageBox.warning(self, "Ошибка", "Элемент не найден")
                return
            dialog = AddEditDialog(self.manager, element, parent=self)
            if dialog.exec():
                self.refresh_data()
                self._select_row_by_id(el_id)
                logger.info(f"Элемент {el_id} отредактирован")
        except Exception as e:
            logger.error(f"Ошибка при редактировании элемента: {e}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def delete_element(self):
        """Удаление выбранного элемента."""
        try:
            selected = self.table.selectionModel().selectedRows()
            if not selected:
                QMessageBox.warning(self, "Предупреждение", "Выберите элемент для удаления")
                return
            row = self.proxy_model.mapToSource(selected[0]).row()
            el_id = self.model.get_id_by_row(row)
            if not el_id:
                QMessageBox.warning(self, "Ошибка", "Не удалось определить элемент")
                return
            element = self.manager.find_by_id(el_id)
            if not element:
                QMessageBox.warning(self, "Ошибка", "Элемент не найден")
                return
            subtree = self.manager.get_subtree(el_id)
            if len(subtree) > 1:
                reply = QMessageBox.question(
                    self,
                    "Подтверждение",
                    f"Элемент '{element['Название']}' содержит {len(subtree) - 1} дочерних элементов. Удалить их все?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.manager.delete_element(el_id)
            self.refresh_data()
            logger.info(f"Элемент {el_id} удален")
        except Exception as e:
            logger.error(f"Ошибка при удалении элемента: {e}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def import_from_registry(self):
        """Импорт документов из реестра."""
        try:
            registry_elements = self.manager.load_registry()
            if not registry_elements:
                QMessageBox.information(self, "Информация", "Реестр пуст")
                return
            dialog = ImportFromRegistryDialog(registry_elements, self)
            if dialog.exec():
                selected_items = dialog.get_selected_items()
                if not selected_items:
                    QMessageBox.warning(self, "Предупреждение", "Не выбраны элементы для импорта")
                    return
                for item in selected_items:
                    element = {
                        "Название": item["Название"],
                        "Тип": "Документ",
                        "Родитель ID": "",
                        "Стеллаж": "",
                        "Полка": "",
                        "Номер документа": item.get("Номер документа", ""),
                        "Дата подписания": item.get("Дата подписания", ""),
                        "Категория": item.get("Категория", "")
                    }
                    self.manager.add_element(element)
                    self.manager.delete_from_registry(item["ID"])
                self.refresh_data()
                logger.info(f"Импортировано {len(selected_items)} элементов из реестра")
        except Exception as e:
            logger.error(f"Ошибка при импорте из реестра: {e}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def refresh_data(self):
        """Обновление данных в таблице и дереве."""
        try:
            if self._updating:
                return
            self._updating = True
            self.model.refresh()
            self._populate_tree()
            self.table.resizeColumnsToContents()
            logger.info("Данные обновлены в EditWindow")
            self._updating = False
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных: {e}")
            QMessageBox.critical(self, "Ошибка", str(e))
            self._updating = False

    def _populate_tree(self):
        """Заполнение дерева иерархии."""
        self.tree_model.removeRows(0, self.tree_model.rowCount())
        elements = self.model.filtered_elements
        root_items = {}
        for el in elements:
            item = QStandardItem(f"{el['Тип']}: {el['Название']}")
            item.setData(el["ID"], Qt.ItemDataRole.UserRole)
            parent_id = el.get("Родитель ID")
            if not parent_id:
                root_items[el["ID"]] = item
                self.tree_model.appendRow(item)
            else:
                parent_item = self._find_item_by_id(parent_id, self.tree_model.invisibleRootItem())
                if parent_item:
                    parent_item.appendRow(item)
        self.tree.expandAll()

    def _find_item_by_id(self, el_id, parent_item):
        """Поиск элемента в дереве по ID."""
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row)
            if item.data(Qt.ItemDataRole.UserRole) == el_id:
                return item
            found = self._find_item_by_id(el_id, item)
            if found:
                return found
        return None

    def _select_row_by_id(self, el_id):
        """Выбор строки в таблице по ID."""
        try:
            for row in range(self.model.rowCount()):
                if self.model.get_id_by_row(row) == el_id:
                    index = self.proxy_model.index(row, 0)
                    self.table.selectionModel().select(
                        index,
                        QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows
                    )
                    self.table.scrollTo(index)
                    logger.info(f"Элемент с ID {el_id} выбран в таблице")
                    break
        except Exception as e:
            logger.error(f"Ошибка при выборе элемента в таблице: {e}")

    def _show_context_menu(self, position):
        """Показ контекстного меню."""
        menu = QMenu(self)
        menu.addAction(self.edit_action)
        menu.addAction(self.delete_action)
        menu.exec(self.table.mapToGlobal(position))

    def _on_tree_double_click(self, index):
        """Обработка двойного клика по дереву."""
        try:
            el_id = index.data(Qt.ItemDataRole.UserRole)
            if el_id:
                element = self.manager.find_by_id(el_id)
                if element:
                    self._show_element_details(element, el_id)
                    self._select_row_by_id(el_id)
        except Exception as e:
            logger.error(f"Ошибка обработки клика по дереву: {e}")

    def _show_element_details(self, element, el_id):
        """Отображение детальной информации об элементе."""
        icon = self._get_type_icon(element['Тип'])
        category = element.get('Категория', '')
        category_full = get_category_description(category)
        first_category = category.split(",")[0].strip() if category else ""
        category_icon = self._get_category_icon(first_category)
        details = (
            f"ID: {el_id}\n"
            f"{icon} Тип: {element['Тип']}\n"
            f"📝 Название: {element['Название']}\n"
            f"📂 Родитель: {self._get_parent_name(element.get('Родитель ID'))}\n"
            f"📚 Стеллаж: {element.get('Стеллаж') or 'Не указан'}\n"
            f"📊 Полка: {element.get('Полка') or 'Не указана'}\n"
            f"🔢 Номер документа: {element.get('Номер документа') or 'Не указан'}\n"
            f"📅 Дата подписания: {element.get('Дата подписания') or 'Не указана'}\n"
            f"{category_icon} Категория: {category_full}"
        )
        QMessageBox.information(self, f"{icon} Детали элемента", details)

    def _get_type_icon(self, el_type):
        """Получение иконки для типа элемента."""
        icons = {
            "Документ": "📄",
            "Коробка": "📦",
            "Папка": "📁",
            "Другое": "🗂"
        }
        return icons.get(el_type, "🗂")

    def _get_category_icon(self, category):
        """Получение иконки для категории."""
        icons = {
            "ТС": "🔥",
            "ВО": "🚽",
            "ВС": "💧",
            "ЛК": "🌧",
            "УУТЭ": "📏",
            "УУХВС": "🚰"
        }
        return icons.get(category, "🔖")

    def _get_parent_name(self, parent_id):
        """Получение имени родителя."""
        if not parent_id:
            return "Корень (нет родителя)"
        parent = self.manager.find_by_id(parent_id)
        return f"{parent['Тип']}: {parent['Название']}" if parent else "Не найден"

    def back_to_menu(self):
        """Возврат в главное меню."""
        if self.main_menu:
            main_menu = self.main_menu()
            if main_menu:
                main_menu.show()
        self.close()

    def _animate_window(self):
        """Анимация появления окна."""
        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(400)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def closeEvent(self, event):
        """Обработка закрытия окна."""
        try:
            self.manager.close()
            logger.info("EditWindow закрыто")
            QSettings().setValue("EditWindow/Geometry", self.saveGeometry())
        except Exception as e:
            logger.error(f"Ошибка при закрытии EditWindow: {e}")
        super().closeEvent(event)
