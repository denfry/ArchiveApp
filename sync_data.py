#!/usr/bin/env python3
"""
Скрипт для синхронизации данных между базой данных и JSON файлом.
Используется для синхронизации данных между локальной машиной и сайтом через git.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataManager, get_app_dir


def export_data():
    """Экспортирует данные из базы данных в JSON файл."""
    try:
        logger.info("Начинаем экспорт данных...")
        manager = DataManager()

        # Создаем директорию для данных, если её нет
        data_dir = get_app_dir()
        sync_file = os.path.join(data_dir, 'archive_data.json')

        if manager.export_to_json(sync_file):
            logger.info(f"✅ Данные успешно экспортированы в {sync_file}")
            return True
        else:
            logger.error("❌ Ошибка экспорта данных")
            return False

    except Exception as e:
        logger.error(f"❌ Критическая ошибка при экспорте: {e}")
        return False
    finally:
        if 'manager' in locals():
            manager.close()


def import_data():
    """Импортирует данные из JSON файла в базу данных."""
    try:
        logger.info("Начинаем импорт данных...")
        manager = DataManager()

        # Путь к файлу синхронизации
        data_dir = get_app_dir()
        sync_file = os.path.join(data_dir, 'archive_data.json')

        if not os.path.exists(sync_file):
            logger.warning(f"Файл синхронизации {sync_file} не найден")
            return False

        if manager.import_from_json(sync_file):
            logger.info(f"✅ Данные успешно импортированы из {sync_file}")
            return True
        else:
            logger.error("❌ Ошибка импорта данных")
            return False

    except Exception as e:
        logger.error(f"❌ Критическая ошибка при импорте: {e}")
        return False
    finally:
        if 'manager' in locals():
            manager.close()


def main():
    """Основная функция скрипта."""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python sync_data.py export  # Экспорт данных в JSON")
        print("  python sync_data.py import  # Импорт данных из JSON")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'export':
        success = export_data()
    elif command == 'import':
        success = import_data()
    else:
        print(f"Неизвестная команда: {command}")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()