# Инструкция по развертыванию веб-сервера

## Варианты развертывания

### 1. Railway (Рекомендуется для Python)

Railway отлично подходит для Python приложений и автоматически определяет зависимости.

#### Шаги:

1. Установите Railway CLI:
   ```bash
   npm i -g @railway/cli
   ```

2. Войдите в Railway:
   ```bash
   railway login
   ```

3. Создайте новый проект:
   ```bash
   railway init
   ```

4. Установите переменную окружения:
   ```bash
   railway variables set BASE_URL=your-app-name.railway.app
   ```

5. Разверните:
   ```bash
   railway up
   ```

6. Railway автоматически определит Python и установит зависимости из `requirements.txt`

### 2. Render

1. Зарегистрируйтесь на [render.com](https://render.com)
2. Создайте новый Web Service
3. Подключите ваш GitHub репозиторий
4. Настройки:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python web_server.py`
   - **Environment**: Python 3
5. Добавьте переменную окружения `BASE_URL` = ваш URL от Render

### 3. Heroku

1. Установите Heroku CLI
2. Создайте файл `Procfile`:
   ```
   web: python web_server.py
   ```
3. Войдите в Heroku:
   ```bash
   heroku login
   ```
4. Создайте приложение:
   ```bash
   heroku create your-app-name
   ```
5. Установите переменную:
   ```bash
   heroku config:set BASE_URL=https://your-app-name.herokuapp.com
   ```
6. Разверните:
   ```bash
   git push heroku main
   ```

### 4. Локальный сервер с ngrok (для тестирования)

1. Установите ngrok: https://ngrok.com/
2. Запустите веб-сервер локально:
   ```bash
   python web_server.py
   ```
3. В другом терминале запустите ngrok:
   ```bash
   ngrok http 8080
   ```
4. Используйте URL от ngrok (например: `https://abc123.ngrok.io`)
5. Установите переменную окружения:
   ```bash
   set BASE_URL=https://abc123.ngrok.io  # Windows
   export BASE_URL=https://abc123.ngrok.io  # Linux/Mac
   ```

## Настройка QR-кодов

После развертывания обновите переменную окружения `BASE_URL` в вашем локальном приложении перед генерацией PDF с наклейками:

```python
# В view_window.py уже используется переменная окружения
# Просто установите её перед запуском:
import os
os.environ['BASE_URL'] = 'https://your-deployed-url.com'
```

## Установка PWA на телефон

1. Откройте развернутый сайт на телефоне
2. В браузере (Chrome/Safari) нажмите меню (три точки)
3. Выберите "Добавить на главный экран" или "Установить приложение"
4. Приложение появится на главном экране как нативное

## Создание иконок для PWA

Создайте иконки размером 192x192 и 512x512 пикселей и сохраните их как:
- `icon-192.png`
- `icon-512.png`

Можно использовать онлайн-генераторы:
- https://realfavicongenerator.net/
- https://www.pwabuilder.com/imageGenerator

## Проверка работы

1. Разверните сервер
2. Откройте `https://your-url.com/scanner` на телефоне
3. Разрешите доступ к камере
4. Отсканируйте QR-код с наклейки
5. Должна открыться страница с информацией о коробке
