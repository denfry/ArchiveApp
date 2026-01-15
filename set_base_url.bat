@echo off
echo ========================================
echo   Настройка BASE_URL для QR-кодов
echo ========================================
echo.
echo Введите URL вашего развернутого сайта
echo Например: https://your-app.railway.app
echo.
set /p BASE_URL="URL: "

if "%BASE_URL%"=="" (
    echo [ОШИБКА] URL не может быть пустым!
    pause
    exit /b 1
)

REM Установка переменной окружения
setx BASE_URL "%BASE_URL%"
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить переменную окружения
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✓ BASE_URL установлен!
echo ========================================
echo.
echo URL: %BASE_URL%
echo.
echo Теперь запустите приложение и сгенерируйте наклейки заново.
echo.
echo Для текущей сессии также установлена временная переменная.
echo.
pause
