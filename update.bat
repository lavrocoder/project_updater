@echo off
chcp 65001 >nul
echo ========================================
echo    Обновление проекта
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python с https://www.python.org/
    pause
    exit /b 1
)

REM Установка необходимых библиотек
echo [1/4] Проверка зависимостей...
python -m pip install --quiet requests

REM Запуск скрипта обновления
echo [2/4] Проверка обновлений...
python updater.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Обновление не выполнено
    pause
    exit /b 1
)

echo.
echo [✓] Обновление завершено успешно!
pause