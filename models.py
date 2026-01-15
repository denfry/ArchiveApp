from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QFont

from data_manager import get_category_description


class SQLiteTableModel(QAbstractTableModel):
    """Model for SQLite table view."""

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.headers = ["ID", "Название", "Тип", "Родитель ID", "Стеллаж", "Полка", "Номер документа",
                        "Дата подписания", "Расположение", "Категория"]
        self.elements = []
        self.all_elements = {}
        self._cache_all_elements()

    def rowCount(self, parent=None):
        return len(self.elements)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self.elements):
            return None
        row_data = self.elements[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            value = row_data[index.column()] if index.column() < len(row_data) else ""
            return str(value) if value else ""
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Arial", 12)
        elif role == Qt.ItemDataRole.ToolTipRole:
            row = self.elements[index.row()]
            name = row[1] if len(row) > 1 else ""
            location = row[8] if len(row) > 8 else ""
            category = row[9] if len(row) > 9 else ""
            return f"Название: {name}\nРасположение: {location}\nКатегория: {category}"
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    def flags(self, index):
        """Return item flags."""
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        # Make all columns except ID and location editable
        if index.column() in [0, 8]:  # ID and location columns are not editable
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """Set data for the given index."""
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        column = index.column()

        if row >= len(self.elements):
            return False

        # Get the element ID
        el_id = self.elements[row][0]

        # Map column to database field
        column_to_field = {
            1: "name",           # Название
            2: "type",           # Тип
            3: "parent_id",      # Родитель ID
            4: "shelf",          # Стеллаж
            5: "rack",           # Полка
            6: "doc_number",     # Номер документа
            7: "sign_date",      # Дата подписания
            9: "category"        # Категория
        }

        if column not in column_to_field:
            return False

        field = column_to_field[column]

        try:
            cursor = self.conn.cursor()
            # Handle empty strings for parent_id and other fields
            if field == "parent_id" and (value == "" or value is None):
                value = None
            elif value == "":
                value = None

            cursor.execute(f"UPDATE elements SET {field} = ? WHERE id = ?", (value, el_id))
            self.conn.commit()

            # Update the local data
            self.elements[row] = list(self.elements[row])
            self.elements[row][column] = value or ""
            self.elements[row] = tuple(self.elements[row])

            # Rebuild location path if necessary
            if column in [2, 3, 4, 5]:  # Type, parent_id, shelf, rack
                location = self._build_location_path(el_id)
                self.elements[row] = list(self.elements[row])
                self.elements[row][8] = location
                self.elements[row] = tuple(self.elements[row])

            self.dataChanged.emit(index, index)
            return True

        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления данных: {e}")
            return False

    def _build_location_path(self, el_id):
        path_parts = []
        current_id = el_id
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            current = self.all_elements.get(current_id)
            if not current:
                break
            if current["Стеллаж"] and current["Тип"] == "Коробка" and not any("Стеллаж" in s for s in path_parts):
                path_parts.append(f"Стеллаж {current['Стеллаж']}")
            if current["Полка"] and not any("Полка" in s for s in path_parts):
                path_parts.append(f"Полка {current['Полка']}")
            if current["Тип"] in ["Коробка", "Папка"]:
                path_parts.append(f"{current['Тип']} '{current['Название']}'")
            current_id = current.get("Родитель ID")
        path = " / ".join(reversed(path_parts))
        doc = self.all_elements.get(el_id)
        if doc and doc['Тип'] == 'Документ':
            doc_location = []
            if doc['Стеллаж']: doc_location.append(f"Стеллаж {doc['Стеллаж']}")
            if doc['Полка']: doc_location.append(f"Полка {doc['Полка']}")
            if doc_location and not path:
                path = " / ".join(doc_location)
        return path or "Без расположения"

    def refresh_cache(self):
        """Fully reload cache and data."""
        self._cache_all_elements()
        self.load_data()

    def _cache_all_elements(self):
        """Cache all elements for quick lookup."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, type, parent_id, shelf, rack, category FROM elements")
            self.all_elements = {r[0]: {
                "ID": r[0], "Название": r[1], "Тип": r[2], "Родитель ID": r[3] or None,
                "Стеллаж": r[4] or "", "Полка": r[5] or "", "Категория": r[6] or ""
            } for r in cursor.fetchall()}
        except Exception as e:
            import logging
            logging.error(f"Ошибка кэширования элементов: {e}")
            self.all_elements = {}

    def load_data(self, filters=None):
        """Load data with filters."""
        try:
            query = "SELECT id, name, type, parent_id, shelf, rack, doc_number, sign_date, category FROM elements"
            conditions = []
            params = []
            if filters:
                if filters.get("name"):
                    conditions.append("name LIKE ?")
                    params.append(f"%{filters['name']}%")
                if filters.get("type") and filters["type"] != "Все":
                    conditions.append("type = ?")
                    params.append(filters["type"])
                if filters.get("shelf") and filters["shelf"] != "Все":
                    conditions.append("shelf = ?")
                    params.append(filters["shelf"])
                if filters.get("rack"):
                    conditions.append("rack LIKE ?")
                    params.append(f"%{filters['rack']}%")
                if filters.get("doc_number"):
                    conditions.append("doc_number LIKE ?")
                    params.append(f"%{filters['doc_number']}%")
                if filters.get("category"):
                    conditions.append("category LIKE ?")
                    params.append(f"%{filters['category']}%")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            self.elements.clear()
            for row in rows:
                el_id, name, el_type, parent_id, shelf, rack, doc_number, sign_date, category = row
                location = self._build_location_path(el_id)
                extended_row = (el_id, name, el_type, parent_id or "", shelf or "", rack or "",
                                doc_number or "", sign_date or "", location, category or "")
                self.elements.append(extended_row)
            self.layoutChanged.emit()
        except Exception as e:
            import logging
            logging.error(f"Ошибка загрузки данных: {e}")


class ElementsTableModel(QAbstractTableModel):
    """Model for elements table."""

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.headers = ["ID", "Название", "Тип", "Родитель ID", "Стеллаж", "Полка", "Номер документа",
                        "Дата подписания", "Категория"]
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
            element = self.filtered_elements[index.row()]
            if key == "Категория":
                # Изменение: Преобразуем коды категорий в полные описания
                return get_category_description(element.get("Категория", ""))
            value = element.get(key, "")
            # Для "Родитель ID" показываем название родителя вместо ID
            if key == "Родитель ID" and value:
                parent = self.manager.find_by_id(value)
                return f"{parent['Тип']}: {parent['Название']}" if parent else "Корень"
            return str(value) if value else "Не указан"
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Arial", 12)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    def refresh(self):
        """Refresh data from manager."""
        try:
            self.beginResetModel()
            elements = self.manager.load_elements()
            self.filtered_elements.clear()
            self.filtered_elements = elements.copy()
            self.layoutChanged.emit()
            self.endResetModel()
        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления ElementsTableModel: {e}")