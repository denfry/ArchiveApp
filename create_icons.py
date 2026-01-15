"""Скрипт для создания иконок PWA из существующего icon.png"""
import os
from PIL import Image

def create_pwa_icons():
    """Создание иконок для PWA из icon.png"""
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(app_dir, 'icon.png')

        if not os.path.exists(icon_path):
            print(f"Файл {icon_path} не найден!")
            print("Создайте icon.png размером не менее 512x512 пикселей")
            return

        # Открываем исходную иконку
        img = Image.open(icon_path)

        # Список всех необходимых размеров иконок
        icon_sizes = [72, 96, 128, 144, 192, 512]

        for size in icon_sizes:
            icon_resized = img.resize((size, size), Image.Resampling.LANCZOS)
            icon_path = os.path.join(app_dir, f'icon-{size}.png')
            icon_resized.save(icon_path, 'PNG')
            print(f"Создана иконка: icon-{size}.png")

        print("\nИконки PWA успешно созданы!")
        print("Теперь можно развернуть приложение в облаке.")

    except ImportError:
        print("Ошибка: Pillow не установлен")
        print("Установите: pip install Pillow")
    except Exception as e:
        print(f"Ошибка при создании иконок: {e}")

if __name__ == "__main__":
    create_pwa_icons()
