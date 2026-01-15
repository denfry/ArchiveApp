@echo off
echo ========================================
echo   Загрузка проекта на GitHub
echo ========================================
echo.

REM Проверка Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Git не установлен!
    echo Установите Git с https://git-scm.com/
    pause
    exit /b 1
)

echo [1/6] Инициализация Git репозитория...
if exist .git (
    echo Репозиторий уже инициализирован
) else (
    git init
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось инициализировать репозиторий
        pause
        exit /b 1
    )
    echo ✓ Репозиторий инициализирован
)

echo.
echo [2/6] Добавление файлов...
git add .
if errorlevel 1 (
    echo [ОШИБКА] Не удалось добавить файлы
    pause
    exit /b 1
)
echo ✓ Файлы добавлены

echo.
echo [3/6] Проверка статуса...
git status

echo.
echo [4/6] Создание коммита...
git commit -m "Initial commit: Archive management system with QR codes and mobile app"
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Возможно, нет изменений для коммита
)

echo.
echo [5/6] Подключение к GitHub...
git remote remove origin 2>nul
git remote add origin https://github.com/denfry/ArchiveApp.git
if errorlevel 1 (
    echo [ОШИБКА] Не удалось подключиться к GitHub
    pause
    exit /b 1
)
echo ✓ Подключено к GitHub

echo.
echo [6/6] Загрузка на GitHub...
git branch -M main
git push -u origin main
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось загрузить на GitHub
    echo.
    echo Возможные причины:
    echo 1. Нужна авторизация (используйте Personal Access Token)
    echo 2. Репозиторий не существует или нет доступа
    echo 3. Проблемы с интернетом
    echo.
    echo См. GITHUB_UPLOAD.md для подробных инструкций
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✓ Проект успешно загружен на GitHub!
echo ========================================
echo.
echo Откройте: https://github.com/denfry/ArchiveApp
echo.
pause
