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

        # Создаем иконку 192x192
        icon_192 = img.resize((192, 192), Image.Resampling.LANCZOS)
        icon_192_path = os.path.join(app_dir, 'icon-192.png')
        icon_192.save(icon_192_path, 'PNG')
        print(f"✓ Создана иконка: icon-192.png")

        # Создаем иконку 512x512
        icon_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
        icon_512_path = os.path.join(app_dir, 'icon-512.png')
        icon_512.save(icon_512_path, 'PNG')
        print(f"✓ Создана иконка: icon-512.png")

        print("\n✓ Иконки PWA успешно созданы!")
        print("Теперь можно развернуть приложение в облаке.")

    except ImportError:
        print("Ошибка: Pillow не установлен")
        print("Установите: pip install Pillow")
    except Exception as e:
        print(f"Ошибка при создании иконок: {e}")

if __name__ == "__main__":
    create_pwa_icons()
