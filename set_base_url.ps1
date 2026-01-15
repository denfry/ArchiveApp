# Скрипт для настройки BASE_URL
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Настройка BASE_URL для QR-кодов" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Введите URL вашего развернутого сайта" -ForegroundColor Yellow
Write-Host "Например: https://your-app.railway.app" -ForegroundColor Gray
Write-Host ""

$baseUrl = Read-Host "URL"

if ([string]::IsNullOrWhiteSpace($baseUrl)) {
    Write-Host "[ОШИБКА] URL не может быть пустым!" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Установка переменной окружения для текущей сессии
$env:BASE_URL = $baseUrl

# Установка переменной окружения постоянно
[System.Environment]::SetEnvironmentVariable("BASE_URL", $baseUrl, "User")

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✓ BASE_URL установлен!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URL: $baseUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Теперь запустите приложение и сгенерируйте наклейки заново." -ForegroundColor Yellow
Write-Host ""
Read-Host "Нажмите Enter для выхода"
