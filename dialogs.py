import logging

from PyQt6.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QPushButton, QLineEdit, QComboBox, QHBoxLayout,
    QTextEdit, QCompleter, QSizePolicy, QDateEdit, QCheckBox, QVBoxLayout, QMessageBox,
    QGroupBox, QListWidget, QListWidgetItem, QLabel, QRadioButton, QButtonGroup
)

from data_manager import get_category_description
from ui_theme import apply_global_style

logger = logging.getLogger(__name__)


class AutoResizingTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.adjustHeight)
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def adjustHeight(self):
        try:
            doc_height = int(self.document().size().height()) + 10
            min_height = 60
            max_height = 500
            new_height = max(min_height, min(doc_height, max_height))
            self.setFixedHeight(new_height)
        except Exception as e:
            logger.error(f"Ошибка при настройке высоты AutoResizingTextEdit: {e}")


class AddEditDialog(QDialog):
    def __init__(self, manager, element=None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.element = element
        self.setWindowTitle("Редактировать элемент" if element else "Добавить элемент")
        self.setMinimumWidth(800)
        self.new_element_id = None
        try:
            logger.info("Начало инициализации AddEditDialog")
            apply_global_style(self)
            self.form_layout = QFormLayout()
            self.form_layout.setSpacing(12)
            self.name_input = AutoResizingTextEdit()
            self.name_input.setFont(QFont("Arial", 12))
            if element:
                self.name_input.setPlainText(element["Название"])
            self.name_input.setToolTip("Введите название элемента (обязательно)")
            self.form_layout.addRow("Название:", self.name_input)
            self.type_input = QComboBox()
            self.type_input.setFont(QFont("Arial", 12))
            self.type_input.addItems(["Документ", "Коробка", "Папка", "Другое"])
            if element:
                idx = self.type_input.findText(element["Тип"])
                self.type_input.setCurrentIndex(idx if idx >= 0 else 0)
            self.type_input.setToolTip("Выберите тип элемента")
            self.form_layout.addRow("Тип:", self.type_input)
            self.parent_input = QComboBox()
            self.parent_input.setEditable(True)
            self.parent_input.setFont(QFont("Arial", 12))
            self.parent_input.addItem("")
            self.update_parent_choices()
            if element and element.get("Родитель ID"):
                parent_name = self.get_parent_display_name(element["Родитель ID"])
                self.parent_input.setCurrentText(parent_name)
            self.parent_input.setToolTip("Выберите родительский элемент (нельзя выбрать потомка)")
            parent_layout = QHBoxLayout()
            parent_layout.addWidget(self.parent_input)
            self.clear_parent_btn = QPushButton("❌ Очистить")
            parent_layout.addWidget(self.clear_parent_btn)
            self.form_layout.addRow("Родитель:", parent_layout)
            self.shelf_input = QComboBox()
            self.shelf_input.setFont(QFont("Arial", 12))
            self.shelf_input.addItems(self.manager.shelves or ["Без стеллажа"])
            if element:
                idx = self.shelf_input.findText(element["Стеллаж"])
                self.shelf_input.setCurrentIndex(idx if idx >= 0 else 0)
            self.shelf_input.setToolTip("Выберите стеллаж")
            self.shelf_row = self.form_layout.addRow("Стеллаж:", self.shelf_input)
            self.rack_input = QLineEdit()
            self.rack_input.setFont(QFont("Arial", 12))
            if element:
                self.rack_input.setText(element["Полка"])
            self.rack_input.setToolTip("Введите номер полки (только цифры)")
            self.rack_row = self.form_layout.addRow("Полка:", self.rack_input)
            self.doc_number_input = QLineEdit()
            self.doc_number_input.setFont(QFont("Arial", 12))
            if element:
                self.doc_number_input.setText(element.get("Номер документа", ""))
            self.doc_number_input.setToolTip("Введите номер документа (только для типа Документ)")
            self.form_layout.addRow("Номер документа:", self.doc_number_input)
            self.date_layout = QVBoxLayout()
            self.no_date_checkbox = QCheckBox("Без даты")
            self.no_date_checkbox.setFont(QFont("Arial", 12))
            self.date_layout.addWidget(self.no_date_checkbox)
            self.year_only_checkbox = QCheckBox("Только год")
            self.year_only_checkbox.setFont(QFont("Arial", 12))
            self.date_layout.addWidget(self.year_only_checkbox)
            self.sign_date_input = QDateEdit()
            self.sign_date_input.setFont(QFont("Arial", 12))
            self.sign_date_input.setCalendarPopup(True)
            self.sign_date_input.setDisplayFormat("dd.MM.yyyy")
            self.sign_date_input.setDate(QDate.currentDate())
            self.sign_date_input.setToolTip("Выберите дату подписания документа (только для типа Документ)")
            self.date_layout.addWidget(self.sign_date_input)
            self.year_input = QLineEdit()
            self.year_input.setFont(QFont("Arial", 12))
            self.year_input.setPlaceholderText("Год (например, 2023)")
            self.year_input.setToolTip("Введите год подписания документа (например, 2023)")
            self.date_layout.addWidget(self.year_input)
            self.form_layout.addRow("Дата подписания:", self.date_layout)

            # Изменение: Вместо QComboBox используем группу чекбоксов для множественного выбора
            self.category_group = QGroupBox("Категории (можно выбрать несколько)")
            category_layout = QVBoxLayout()
            self.category_checkboxes = {}
            categories = [
                "ТС", "ВО", "ВС", "ЛК", "УУТЭ", "УУХВС"
            ]  # Коды категорий из вашего списка
            for cat in categories:
                full_desc = get_category_description(cat)
                cb = QCheckBox(full_desc)
                cb.setFont(QFont("Arial", 12))
                cb.setToolTip(f"Выберите категорию: {full_desc}")
                category_layout.addWidget(cb)
                self.category_checkboxes[cat] = cb

            if element:
                selected_cats = element.get("Категория", "").split(",")
                for cat in selected_cats:
                    cat = cat.strip()
                    if cat in self.category_checkboxes:
                        self.category_checkboxes[cat].setChecked(True)

            self.category_group.setLayout(category_layout)
            self.form_layout.addRow("Категории:", self.category_group)

            if element and element.get("Дата подписания"):
                sign_date = element["Дата подписания"]
                if sign_date == "":
                    self.no_date_checkbox.setChecked(True)
                elif len(sign_date) == 4 and sign_date.isdigit():
                    self.year_only_checkbox.setChecked(True)
                    self.year_input.setText(sign_date)
                else:
                    try:
                        date = QDate.fromString(sign_date, "dd.MM.yyyy")
                        self.sign_date_input.setDate(date)
                    except:
                        self.no_date_checkbox.setChecked(True)
            else:
                self.no_date_checkbox.setChecked(True)
            btn_layout = QHBoxLayout()
            self.save_btn = QPushButton("💾 Сохранить")
            self.save_btn.setEnabled(False)
            cancel_btn = QPushButton("❌ Отмена")
            btn_layout.addWidget(self.save_btn)
            btn_layout.addWidget(cancel_btn)
            self.form_layout.addRow(btn_layout)
            self.type_input.currentTextChanged.connect(self.toggle_doc_fields)
            self.no_date_checkbox.toggled.connect(self.toggle_date_fields)
            self.year_only_checkbox.toggled.connect(self.toggle_date_fields)
            self.parent_input.currentTextChanged.connect(
                lambda: self.update_field_availability(self.parent_input.currentText()))
            self.name_input.textChanged.connect(self.validate_inputs)
            self.type_input.currentTextChanged.connect(self.validate_inputs)
            self.rack_input.textChanged.connect(self.validate_inputs)
            self.year_input.textChanged.connect(self.validate_inputs)
            self.clear_parent_btn.clicked.connect(lambda: self.parent_input.setCurrentText(""))
            self.save_btn.clicked.connect(self.save)
            cancel_btn.clicked.connect(self.reject)
            self.toggle_doc_fields(self.type_input.currentText())
            self.update_field_availability(self.parent_input.currentText())
            self.validate_inputs()
            logger.info("Инициализация AddEditDialog завершена")

            # Новое: Установить layout на диалог (было забыто в оригинале, но теперь добавлено явно)
            self.setLayout(self.form_layout)
        except Exception as e:
            logger.error(f"Ошибка инициализации AddEditDialog: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициализировать диалог: {str(e)}")

    def update_parent_choices(self):
        try:
            containers = self.manager.get_containers(self.type_input.currentText())
            self.parent_input.clear()
            self.parent_input.addItem("")
            for el in containers:
                if not self.element or el["ID"] != self.element.get("ID"):
                    self.parent_input.addItem(f"{el['Тип']}: {el['Название']}")
            completer = QCompleter([self.parent_input.itemText(i) for i in range(self.parent_input.count())])
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.parent_input.setCompleter(completer)
        except Exception as e:
            logger.error(f"Ошибка в update_parent_choices: {e}")

    def get_parent_display_name(self, parent_id):
        try:
            parent = self.manager.find_by_id(parent_id)
            if parent:
                return f"{parent['Тип']}: {parent['Название']}"
            return ""
        except Exception as e:
            logger.error(f"Ошибка в get_parent_display_name: {e}")
            return ""

    def validate_inputs(self):
        try:
            is_valid = bool(self.name_input.toPlainText().strip())
            if self.type_input.currentText() == "Документ":
                if self.year_only_checkbox.isChecked():
                    year = self.year_input.text().strip()
                    is_valid = is_valid and (year.isdigit() and len(year) == 4 or not year)
            self.save_btn.setEnabled(is_valid)
        except Exception as e:
            logger.error(f"Ошибка в validate_inputs: {e}")

    def update_field_availability(self, parent_text):
        try:
            has_parent = bool(parent_text.strip())
            self.shelf_input.setEnabled(not has_parent)
            self.rack_input.setEnabled(not has_parent)
            if has_parent:
                self.shelf_input.setCurrentText("Без стеллажа")
                self.rack_input.clear()
                self.animate_field_visibility(False)
            else:
                self.animate_field_visibility(True)
            self.validate_inputs()
        except Exception as e:
            logger.error(f"Ошибка в update_field_availability: {e}")

    def animate_field_visibility(self, visible):
        try:
            target_height = 0 if not visible else 40
            if not hasattr(self, 'shelf_animation'):
                self.shelf_animation = QPropertyAnimation(self.shelf_input, b"maximumHeight")
                self.shelf_animation.setDuration(300)
                self.shelf_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.shelf_animation.setStartValue(self.shelf_input.maximumHeight())
            self.shelf_animation.setEndValue(target_height)
            self.shelf_animation.start()
            if not hasattr(self, 'rack_animation'):
                self.rack_animation = QPropertyAnimation(self.rack_input, b"maximumHeight")
                self.rack_animation.setDuration(300)
                self.rack_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.rack_animation.setStartValue(self.rack_input.maximumHeight())
            self.rack_animation.setEndValue(target_height)
            self.rack_animation.start()
            shelf_label = self.form_layout.labelForField(self.shelf_input)
            rack_label = self.form_layout.labelForField(self.rack_input)
            if shelf_label:
                shelf_label.setVisible(visible)
            if rack_label:
                rack_label.setVisible(visible)
        except Exception as e:
            logger.error(f"Ошибка в animate_field_visibility: {e}")

    def toggle_doc_fields(self, el_type):
        try:
            is_doc = el_type == "Документ"
            self.doc_number_input.setEnabled(is_doc)
            self.no_date_checkbox.setEnabled(is_doc)
            self.year_only_checkbox.setEnabled(is_doc)
            self.sign_date_input.setEnabled(
                is_doc and not self.no_date_checkbox.isChecked() and not self.year_only_checkbox.isChecked())
            self.year_input.setEnabled(is_doc and self.year_only_checkbox.isChecked())
            self.validate_inputs()
        except Exception as e:
            logger.error(f"Ошибка в toggle_doc_fields: {e}")

    def toggle_date_fields(self):
        try:
            self.sign_date_input.setEnabled(
                not self.no_date_checkbox.isChecked() and not self.year_only_checkbox.isChecked())
            self.year_input.setEnabled(self.year_only_checkbox.isChecked())
            self.validate_inputs()
        except Exception as e:
            logger.error(f"Ошибка в toggle_date_fields: {e}")

    def get_element_data(self):
        parent_text = self.parent_input.currentText().strip()
        parent_id = None
        if parent_text:
            containers = self.manager.get_containers(self.type_input.currentText())
            for el in containers:
                if f"{el['Тип']}: {el['Название']}" == parent_text:
                    parent_id = el["ID"]
                    break
        # Изменение: Собираем выбранные категории как строку с запятыми
        selected_categories = [cat for cat, cb in self.category_checkboxes.items() if cb.isChecked()]
        category = ",".join(selected_categories) if selected_categories else ""
        return {
            "Название": self.name_input.toPlainText().strip(),
            "Тип": self.type_input.currentText(),
            "Родитель ID": parent_id,
            "Стеллаж": self.shelf_input.currentText() if not parent_text else "",
            "Полка": self.rack_input.text().strip() if not parent_text else "",
            "Номер документа": self.doc_number_input.text().strip() if self.type_input.currentText() == "Документ" else "",
            "Дата подписания": (
                "" if self.no_date_checkbox.isChecked() else
                self.year_input.text().strip() if self.year_only_checkbox.isChecked() else
                self.sign_date_input.date().toString("dd.MM.yyyy")
            ),
            "Категория": category
        }

    def save(self):
        try:
            name = self.name_input.toPlainText().strip()
            if not name:
                QMessageBox.warning(self, "Ошибка", "Название обязательно")
                return
            parent_text = self.parent_input.currentText().strip()
            parent_id = None
            if parent_text:
                containers = self.manager.get_containers(self.type_input.currentText())
                for el in containers:
                    if f"{el['Тип']}: {el['Название']}" == parent_text:
                        parent_id = el["ID"]
                        break
                if not parent_id:
                    QMessageBox.warning(self, "Ошибка", "Недопустимый родительский элемент")
                    return
            if self.element and self.element.get("ID") == parent_id:
                QMessageBox.warning(self, "Ошибка", "Элемент не может быть своим собственным родителем")
                return
            if parent_id and self.element:
                if self.manager._would_create_cycle(self.element["ID"], parent_id):
                    QMessageBox.warning(self, "Ошибка", "Это создаст циклическую зависимость")
                    return
            rack = ""
            shelf = ""
            if not parent_id:
                rack = self.rack_input.text().strip()
                shelf = self.shelf_input.currentText() if self.shelf_input.currentText() != "Без стеллажа" else ""
                if rack and not rack.isdigit():
                    QMessageBox.warning(self, "Ошибка", "Номер полки должен быть числом")
                    return
            sign_date = ""
            if self.type_input.currentText() == "Документ":
                if self.no_date_checkbox.isChecked():
                    sign_date = ""
                elif self.year_only_checkbox.isChecked():
                    year = self.year_input.text().strip()
                    if not year.isdigit() or len(year) != 4:
                        QMessageBox.warning(self, "Ошибка", "Год должен быть четырехзначным числом")
                        return
                    sign_date = year
                else:
                    sign_date = self.sign_date_input.date().toString("dd.MM.yyyy")
            element = {
                "Название": name,
                "Тип": self.type_input.currentText(),
                "Родитель ID": parent_id,
                "Стеллаж": shelf,
                "Полка": rack,
                "Номер документа": self.doc_number_input.text().strip() if self.type_input.currentText() == "Документ" else "",
                "Дата подписания": sign_date,
                "Категория": self.get_element_data()["Категория"]  # Здесь берётся строка с запятыми
            }
            if self.element:
                self.manager.edit_element(self.element["ID"], element)
            else:
                self.new_element_id = self.manager.add_element(element)
            self.accept()
        except ValueError as ve:
            logger.error(f"Ошибка сохранения: {ve}")
            QMessageBox.warning(self, "Ошибка", str(ve))
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить элемент: {e}")


class PrintLabelsDialog(QDialog):
    """Диалог для настройки печати наклеек на коробки."""

    def __init__(self, boxes_data, parent=None):
        super().__init__(parent)
        self.boxes_data = boxes_data  # Список словарей с данными коробок
        self.selected_boxes = []
        self.setWindowTitle("Печать наклеек на коробки")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        apply_global_style(self)
        self._setup_ui()

    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Группа выбора формата
        format_group = QGroupBox("Формат наклеек")
        format_layout = QVBoxLayout()

        self.format_group = QButtonGroup(self)

        self.brief_format = QRadioButton("Краткий формат (название + расположение)")
        self.brief_format.setChecked(True)
        self.format_group.addButton(self.brief_format)

        self.full_format = QRadioButton("Полный формат (все данные)")
        self.format_group.addButton(self.full_format)

        self.custom_format = QRadioButton("Кастомный формат")
        self.format_group.addButton(self.custom_format)

        format_layout.addWidget(self.brief_format)
        format_layout.addWidget(self.full_format)
        format_layout.addWidget(self.custom_format)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Опции кастомного формата
        self.custom_options_group = QGroupBox("Опции кастомного формата")
        custom_layout = QVBoxLayout()

        self.show_name = QCheckBox("Показывать название")
        self.show_name.setChecked(True)
        custom_layout.addWidget(self.show_name)

        self.show_location = QCheckBox("Показывать расположение")
        self.show_location.setChecked(True)
        custom_layout.addWidget(self.show_location)

        self.show_category = QCheckBox("Показывать категорию")
        self.show_category.setChecked(True)
        custom_layout.addWidget(self.show_category)

        self.show_qr = QCheckBox("Показывать QR-код")
        self.show_qr.setChecked(True)
        custom_layout.addWidget(self.show_qr)

        self.custom_options_group.setLayout(custom_layout)
        self.custom_options_group.setEnabled(False)
        layout.addWidget(self.custom_options_group)

        # Подключение сигналов
        self.custom_format.toggled.connect(self.custom_options_group.setEnabled)

        # Группа выбора раскладки
        layout_group = QGroupBox("Раскладка на листе A4")
        layout_layout = QVBoxLayout()

        self.layout_combo = QComboBox()
        self.layout_combo.addItems([
            "4x6 (24 наклейки)",
            "5x7 (35 наклеек)",
            "6x8 (48 наклеек)",
            "7x9 (63 наклейки)",
            "8x10 (80 наклеек)",
            "3x4 (12 наклеек)",
            "2x3 (6 наклеек)"
        ])
        self.layout_combo.setCurrentText("6x8 (48 наклеек)")
        layout_layout.addWidget(QLabel("Количество наклеек на листе:"))
        layout_layout.addWidget(self.layout_combo)
        layout_group.setLayout(layout_layout)
        layout.addWidget(layout_group)

        # Группа выбора коробок
        boxes_group = QGroupBox("Выбор коробок для печати")
        boxes_layout = QVBoxLayout()

        self.selection_type_group = QButtonGroup(self)
        self.select_all = QRadioButton("Все коробки")
        self.select_all.setChecked(True)
        self.selection_type_group.addButton(self.select_all)

        self.select_manual = QRadioButton("Выбрать вручную")
        self.selection_type_group.addButton(self.select_manual)

        boxes_layout.addWidget(self.select_all)
        boxes_layout.addWidget(self.select_manual)

        self.boxes_list = QListWidget()
        self.boxes_list.setEnabled(False)
        for box in self.boxes_data:
            item = QListWidgetItem(f"{box['Название']} - {box.get('Стеллаж', '')}/{box.get('Полка', '')}")
            item.setData(Qt.ItemDataRole.UserRole, box['ID'])
            self.boxes_list.addItem(item)

        boxes_layout.addWidget(QLabel("Доступные коробки:"))
        boxes_layout.addWidget(self.boxes_list)
        boxes_group.setLayout(boxes_layout)
        layout.addWidget(boxes_group)

        # Подключение сигналов для списка
        self.select_manual.toggled.connect(self.boxes_list.setEnabled)

        # Кнопки
        buttons_layout = QHBoxLayout()
        self.print_btn = QPushButton("🖨️ Печатать")
        self.print_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.print_btn)
        layout.addLayout(buttons_layout)

        # Подсказка
        hint_label = QLabel("💡 Совет: Для экономии места используйте краткий формат с QR-кодами")
        hint_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(hint_label)

    def get_print_settings(self):
        """Получить настройки печати."""
        # Определение формата
        if self.brief_format.isChecked():
            format_type = "brief"
        elif self.full_format.isChecked():
            format_type = "full"
        else:
            format_type = "custom"

        # Получение раскладки
        layout_text = self.layout_combo.currentText()
        if "4x6" in layout_text:
            cols, rows = 4, 6
        elif "5x7" in layout_text:
            cols, rows = 5, 7
        elif "6x8" in layout_text:
            cols, rows = 6, 8
        elif "7x9" in layout_text:
            cols, rows = 7, 9
        elif "8x10" in layout_text:
            cols, rows = 8, 10
        elif "3x4" in layout_text:
            cols, rows = 3, 4
        elif "2x3" in layout_text:
            cols, rows = 2, 3
        else:  # по умолчанию
            cols, rows = 6, 8

        # Выбор коробок
        if self.select_all.isChecked():
            selected_boxes = self.boxes_data
        else:
            selected_boxes = []
            for item in self.boxes_list.selectedItems():
                box_id = item.data(Qt.ItemDataRole.UserRole)
                box = next((b for b in self.boxes_data if b['ID'] == box_id), None)
                if box:
                    selected_boxes.append(box)

        # Кастомные опции
        custom_options = {
            "show_name": self.show_name.isChecked(),
            "show_location": self.show_location.isChecked(),
            "show_category": self.show_category.isChecked(),
            "show_qr": self.show_qr.isChecked()
        }

        return {
            "format_type": format_type,
            "layout": {"cols": cols, "rows": rows},
            "selected_boxes": selected_boxes,
            "custom_options": custom_options
        }
