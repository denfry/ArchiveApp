import json
import logging
import os
import sqlite3
import sys
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def get_app_dir():
    """Получение директории приложения (для PyInstaller или разработки)."""
    if getattr(sys, 'frozen', False):
        # Если запущено через PyInstaller
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_category_description(category_code):
    """Получение полного описания категории по коду или кодам (с разделителями запятыми)."""
    categories = {
        "ТС": "ТС - Теплосеть (отопление + ГВС или перегретая вода)",
        "ВО": "ВО - Хоз. бытовая канализация",
        "ВС": "ВС - Водоснабжение (ХВС)",
        "ЛК": "ЛК - Ливневая канализация",
        "УУТЭ": "УУТЭ - Узел учета тепловой энергии",
        "УУХВС": "УУХВС - Узел учета холодного водоснабжения"
    }
    if not category_code:
        return "Не указана"
    codes = category_code.split(",")
    descriptions = [categories.get(code.strip(), code.strip() or "Не указана") for code in codes]
    return ", ".join(descriptions)


class DataManager:
    def __init__(self, db_file=None):
        app_dir = get_app_dir()
        self.data_dir = os.path.join(app_dir, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_file = db_file or os.path.join(self.data_dir, 'archive.db')
        logger.info(f"Используется БД: {self.db_file}")
        self.conn = sqlite3.connect(self.db_file)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()
        self.migrate_schema()
        self.shelves = ["А", "Б", "В", "Г"]
        self.elements = []
        self._elements_loaded = False
        logger.info("Инициализация DataManager завершена")

    def create_tables(self):
        try:
            logger.info("Создание таблиц в базе данных")
            cursor = self.conn.cursor()
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS elements
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
                               NOT
                               NULL,
                               parent_id
                               TEXT,
                               shelf
                               TEXT,
                               rack
                               TEXT,
                               doc_number
                               TEXT,
                               sign_date
                               TEXT,
                               category
                               TEXT,
                               FOREIGN
                               KEY
                           (
                               parent_id
                           ) REFERENCES elements
                           (
                               id
                           )
                               )
                           """)
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
            self.conn.commit()
            logger.info("Таблицы успешно созданы")
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            raise

    def migrate_schema(self):
        try:
            logger.info("Проверка и миграция схемы базы данных")
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(elements)")
            columns = [col[1] for col in cursor.fetchall()]
            if "sign_date" not in columns:
                cursor.execute("ALTER TABLE elements ADD COLUMN sign_date TEXT")
                logger.info("Добавлен столбец sign_date в таблицу elements")
            if "category" not in columns:
                cursor.execute("ALTER TABLE elements ADD COLUMN category TEXT")
                logger.info("Добавлен столбец category в таблицу elements")
            cursor.execute("PRAGMA table_info(registry)")
            columns = [col[1] for col in cursor.fetchall()]
            if "category" not in columns:
                cursor.execute("ALTER TABLE registry ADD COLUMN category TEXT")
                logger.info("Добавлен столбец category в таблицу registry")
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при миграции схемы: {e}")
            raise

    def load_elements(self):
        """Загрузка всех элементов из БД с поддержкой категорий."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                           SELECT id,
                                  name,
                                  type,
                                  parent_id,
                                  shelf,
                                  rack,
                                  doc_number,
                                  sign_date,
                                  category
                           FROM elements
                           """)
            return [
                {
                    "ID": row[0],
                    "Название": row[1],
                    "Тип": row[2],
                    "Родитель ID": row[3],
                    "Стеллаж": row[4],
                    "Полка": row[5],
                    "Номер документа": row[6],
                    "Дата подписания": row[7],
                    "Категория": row[8] or ""
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            logger.error(f"Ошибка загрузки элементов: {e}")
            return []

    def load_registry(self):
        """Загрузка данных из таблицы реестра с поддержкой категорий."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, type, doc_number, sign_date, status, category FROM registry")
            return [
                {
                    "ID": row[0],
                    "Название": row[1],
                    "Тип": row[2],
                    "Номер документа": row[3],
                    "Дата подписания": row[4],
                    "Статус": row[5],
                    "Категория": row[6] or ""
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            logger.error(f"Ошибка загрузки реестра: {e}")
            return []

    def delete_from_registry(self, el_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM registry WHERE id = ?", (el_id,))
            self.conn.commit()
            logger.info(f"Документ удален из реестра: {el_id}")
        except Exception as e:
            logger.error(f"Ошибка удаления из реестра: {e}")
            raise

    def _ensure_elements_loaded(self):
        if not self._elements_loaded:
            self.elements = self.load_elements()
            self._elements_loaded = True

    def find_by_id(self, el_id):
        """Находит элемент по ID с принудительным обновлением данных из БД."""
        try:
            logger.debug(f"Поиск элемента по ID: {el_id}")
            self.elements = self.load_elements()
            self._elements_loaded = True

            for el in self.elements:
                if str(el["ID"]) == str(el_id):
                    logger.debug(f"Элемент найден: {el}")
                    return el

            logger.warning(f"Элемент с ID {el_id} не найден в базе данных")
            return None
        except Exception as e:
            logger.error(f"Ошибка в find_by_id: {e}")
            return None

    def _would_create_cycle(self, el_id, new_parent_id):
        if new_parent_id == el_id:
            return True
        temp = new_parent_id
        while temp:
            if temp == el_id:
                return True
            parent = self.find_by_id(temp)
            temp = parent.get("Родитель ID") if parent else None
        return False

    def add_element(self, element):
        try:
            el_id = str(uuid.uuid4())
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO elements (id, name, type, parent_id, shelf, rack, doc_number, sign_date, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    el_id,
                    element["Название"],
                    element["Тип"],
                    element["Родитель ID"] or None,
                    element["Стеллаж"] or None,
                    element["Полка"] or None,
                    element.get("Номер документа") or None,
                    element.get("Дата подписания") or None,
                    element.get("Категория") or None
                )
            )
            self.conn.commit()
            self._add_to_cache(el_id, element)
            logger.info(f"Элемент добавлен: {element['Название']} (ID: {el_id})")
            return el_id
        except Exception as e:
            logger.error(f"Ошибка добавления элемента: {e}")
            raise

    def _add_to_cache(self, el_id, element):
        if self._elements_loaded:
            new_element = {
                "ID": el_id,
                "Название": element["Название"],
                "Тип": element["Тип"],
                "Родитель ID": element["Родитель ID"] or "",
                "Стеллаж": element["Стеллаж"] or "",
                "Полка": element["Полка"] or "",
                "Номер документа": element["Номер документа"] or "",
                "Дата подписания": element["Дата подписания"] or "",
                "Категория": element.get("Категория") or ""
            }
            self.elements.append(new_element)

    def edit_element(self, el_id, element):
        try:
            logger.info(f"Редактирование элемента с ID: {el_id}")
            new_parent = element["Родитель ID"]
            if new_parent and self._would_create_cycle(el_id, new_parent):
                raise ValueError("Это создаст циклическую зависимость в иерархии")
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE elements SET name = ?, type = ?, parent_id = ?, shelf = ?, rack = ?, doc_number = ?, sign_date = ?, category = ? WHERE id = ?",
                (
                    element["Название"],
                    element["Тип"],
                    new_parent or None,
                    element["Стеллаж"] or None,
                    element["Полка"] or None,
                    element["Номер документа"] or None,
                    element["Дата подписания"] or None,
                    element.get("Категория") or None,
                    el_id
                )
            )
            self.conn.commit()
            self._update_cache(el_id, element)
            logger.info(f"Элемент с ID {el_id} успешно отредактирован")
        except ValueError as ve:
            logger.warning(f"Предотвращена циклическая зависимость: {ve}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при редактировании элемента: {e}")
            raise

    def _update_cache(self, el_id, element):
        if self._elements_loaded:
            for i, el in enumerate(self.elements):
                if el["ID"] == el_id:
                    self.elements[i].update({
                        "Название": element["Название"],
                        "Тип": element["Тип"],
                        "Родитель ID": element["Родитель ID"] or "",
                        "Стеллаж": element["Стеллаж"] or "",
                        "Полка": element["Полка"] or "",
                        "Номер документа": element["Номер документа"] or "",
                        "Дата подписания": element["Дата подписания"] or "",
                        "Категория": element.get("Категория") or ""
                    })
                    break

    def delete_element(self, el_id):
        try:
            logger.info(f"Удаление элемента с ID: {el_id}")
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM elements WHERE id = ?", (el_id,))
            cursor.execute("UPDATE elements SET parent_id = NULL WHERE parent_id = ?", (el_id,))
            self.conn.commit()
            self._remove_from_cache(el_id)
            logger.info(f"Элемент с ID {el_id} успешно удален")
        except Exception as e:
            logger.error(f"Ошибка при удалении элемента: {e}")
            raise

    def _remove_from_cache(self, el_id):
        if self._elements_loaded:
            self.elements = [el for el in self.elements if el["ID"] != el_id]
            for el in self.elements:
                if el["Родитель ID"] == el_id:
                    el["Родитель ID"] = ""

    def get_containers(self, el_type):
        try:
            self._ensure_elements_loaded()
            return [
                el for el in self.elements
                if el["Тип"] in (["Коробка", "Папка"] if el_type in ["Документ", "Папка"] else ["Коробка"])
            ]
        except Exception as e:
            logger.error(f"Ошибка в get_containers: {e}")
            return []

    def get_subtree(self, parent_id):
        try:
            self._ensure_elements_loaded()
            subtree = []
            parent = self.find_by_id(parent_id)
            if parent:
                subtree.append(parent)

            def collect_children(current_id):
                for el in self.elements:
                    if el["Родитель ID"] == current_id:
                        subtree.append(el)
                        collect_children(el["ID"])

            collect_children(parent_id)
            logger.debug(f"Поддерево для {parent_id}: {len(subtree)} элементов")
            return subtree
        except Exception as e:
            logger.error(f"Ошибка в get_subtree: {e}")
            return []

    def export_to_json(self, json_file):
        """Экспорт всех данных в JSON файл для синхронизации."""
        try:
            logger.info(f"Экспорт данных в JSON: {json_file}")
            elements = self.load_elements()
            registry = self.load_registry()

            data = {
                "elements": elements,
                "registry": registry,
                "export_timestamp": str(uuid.uuid4()),
                "version": "1.0"
            }

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Экспорт завершен: {len(elements)} элементов, {len(registry)} записей реестра")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта в JSON: {e}")
            return False

    def import_from_json(self, json_file):
        """Импорт данных из JSON файла с полной заменой."""
        try:
            logger.info(f"Импорт данных из JSON: {json_file}")
            if not Path(json_file).exists():
                logger.warning(f"JSON файл {json_file} не существует")
                return False

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            cursor = self.conn.cursor()

            # Очищаем существующие данные
            cursor.execute("DELETE FROM elements")
            cursor.execute("DELETE FROM registry")

            # Импортируем элементы
            elements = data.get("elements", [])
            for el in elements:
                cursor.execute(
                    "INSERT INTO elements (id, name, type, parent_id, shelf, rack, doc_number, sign_date, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        el["ID"],
                        el["Название"],
                        el["Тип"],
                        el["Родитель ID"] or None,
                        el["Стеллаж"] or None,
                        el["Полка"] or None,
                        el["Номер документа"] or None,
                        el["Дата подписания"] or None,
                        el["Категория"] or None
                    )
                )

            # Импортируем реестр
            registry = data.get("registry", [])
            for reg in registry:
                cursor.execute(
                    "INSERT INTO registry (id, name, type, doc_number, sign_date, status, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        reg["ID"],
                        reg["Название"],
                        reg["Тип"],
                        reg["Номер документа"] or None,
                        reg["Дата подписания"] or None,
                        reg["Статус"] or None,
                        reg["Категория"] or None
                    )
                )

            self.conn.commit()
            self.elements = []
            self._elements_loaded = False
            logger.info(f"Импорт завершен: {len(elements)} элементов, {len(registry)} записей реестра")
            return True
        except Exception as e:
            logger.error(f"Ошибка импорта из JSON: {e}")
            return False

    def migrate_from_json(self, json_file):
        try:
            logger.info(f"Миграция данных из JSON: {json_file}")
            if not Path(json_file).exists():
                logger.warning(f"JSON файл {json_file} не существует")
                return False
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cursor = self.conn.cursor()
            for el in data:
                el_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO elements (id, name, type, parent_id, shelf, rack, doc_number, sign_date, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        el_id,
                        el["name"],
                        el["type"],
                        el.get("parent_id"),
                        el.get("shelf", ""),
                        el.get("rack", ""),
                        el.get("doc_number", ""),
                        el.get("sign_date", ""),
                        el.get("category", "")
                    )
                )
            self.conn.commit()
            self.elements = []
            self._elements_loaded = False
            logger.info(f"Миграция данных из {json_file} завершена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при миграции из JSON: {e}")
            return False

    def get_documents_in_box(self, box_id):
        """Получить все документы в коробке (рекурсивно, включая документы в папках)."""
        try:
            documents = []
            cursor = self.conn.cursor()

            # Рекурсивный поиск всех документов в коробке
            def find_documents_recursive(parent_id):
                # Найти все элементы с указанным родителем
                cursor.execute("SELECT id, name, type, doc_number, sign_date, category FROM elements WHERE parent_id = ?", (parent_id,))
                children = cursor.fetchall()

                for child in children:
                    child_id, name, el_type, doc_number, sign_date, category = child

                    if el_type == "Документ":
                        # Это документ - добавляем в список
                        documents.append({
                            "ID": child_id,
                            "Название": name,
                            "Номер документа": doc_number or "",
                            "Дата подписания": sign_date or "",
                            "Категория": category or ""
                        })
                    elif el_type in ["Папка", "Коробка"]:
                        # Это папка или вложенная коробка - ищем документы внутри
                        find_documents_recursive(child_id)

            # Начинаем поиск с коробки
            find_documents_recursive(box_id)

            logger.info(f"Найдено {len(documents)} документов в коробке {box_id}")
            return documents

        except Exception as e:
            logger.error(f"Ошибка получения документов в коробке: {e}")
            return []

    def close(self):
        try:
            logger.info("Закрытие соединения с базой данных")
            self.elements.clear()
            self._elements_loaded = False
            if self.conn:
                self.conn.close()
            logger.info("Соединение с базой данных закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения: {e}")

    def __del__(self):
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
        except Exception:
            pass
