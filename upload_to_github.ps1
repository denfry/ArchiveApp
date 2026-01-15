# Скрипт для загрузки проекта на GitHub
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Загрузка проекта на GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка Git
try {
    $gitVersion = git --version
    Write-Host "[OK] Git установлен: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "[ОШИБКА] Git не установлен!" -ForegroundColor Red
    Write-Host "Установите Git с https://git-scm.com/" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Шаг 1: Инициализация
Write-Host ""
Write-Host "[1/6] Инициализация Git репозитория..." -ForegroundColor Yellow
if (Test-Path .git) {
    Write-Host "Реопозиторий уже инициализирован" -ForegroundColor Gray
} else {
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ОШИБКА] Не удалось инициализировать репозиторий" -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
    Write-Host "✓ Репозиторий инициализирован" -ForegroundColor Green
}

# Шаг 2: Добавление файлов
Write-Host ""
Write-Host "[2/6] Добавление файлов..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ОШИБКА] Не удалось добавить файлы" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}
Write-Host "✓ Файлы добавлены" -ForegroundColor Green

# Шаг 3: Статус
Write-Host ""
Write-Host "[3/6] Проверка статуса..." -ForegroundColor Yellow
git status

# Шаг 4: Коммит
Write-Host ""
Write-Host "[4/6] Создание коммита..." -ForegroundColor Yellow
git commit -m "Initial commit: Archive management system with QR codes and mobile app"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Возможно, нет изменений для коммита" -ForegroundColor Yellow
}

# Шаг 5: Подключение к GitHub
Write-Host ""
Write-Host "[5/6] Подключение к GitHub..." -ForegroundColor Yellow
git remote remove origin 2>$null
git remote add origin https://github.com/denfry/ArchiveApp.git
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ОШИБКА] Не удалось подключиться к GitHub" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}
Write-Host "✓ Подключено к GitHub" -ForegroundColor Green

# Шаг 6: Загрузка
Write-Host ""
Write-Host "[6/6] Загрузка на GitHub..." -ForegroundColor Yellow
git branch -M main
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ОШИБКА] Не удалось загрузить на GitHub" -ForegroundColor Red
    Write-Host ""
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "1. Нужна авторизация (используйте Personal Access Token)" -ForegroundColor Yellow
    Write-Host "2. Репозиторий не существует или нет доступа" -ForegroundColor Yellow
    Write-Host "3. Проблемы с интернетом" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "См. GITHUB_UPLOAD.md для подробных инструкций" -ForegroundColor Cyan
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✓ Проект успешно загружен на GitHub!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Откройте: https://github.com/denfry/ArchiveApp" -ForegroundColor Cyan
Write-Host ""
Read-Host "Нажмите Enter для выхода"
