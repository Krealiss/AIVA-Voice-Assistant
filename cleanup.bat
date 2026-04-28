@echo off
echo ========================================
echo AIVA - Організація файлів
echo ========================================
echo.

echo Створення структури папок...
if not exist docs mkdir docs
if not exist scripts mkdir scripts
if not exist src mkdir src
if not exist legacy mkdir legacy
if not exist data mkdir data

echo.
echo Переміщення документації...
move /Y SUMMARY.md docs\ 2>nul
move /Y IMPROVEMENT_PLAN.md docs\ 2>nul
move /Y PERFORMANCE_IMPROVEMENTS.md docs\ 2>nul
move /Y QUICK_WINS.md docs\ 2>nul
move /Y UPDATE_GUIDE.md docs\ 2>nul
move /Y DASHBOARD_README.md docs\ 2>nul
move /Y QUICK_START_DASHBOARD.md docs\ 2>nul
move /Y CLEANUP_PLAN.md docs\ 2>nul

echo.
echo Переміщення скриптів...
move /Y run_*.bat scripts\ 2>nul
move /Y install_*.bat scripts\ 2>nul

echo.
echo Переміщення коду...
move /Y agent_main.py src\ 2>nul
move /Y ai_brain.py src\ 2>nul
move /Y asr_whisper.py src\ 2>nul
move /Y config.py src\ 2>nul
move /Y dashboard_api.py src\ 2>nul
move /Y dashboard_lite.py src\ 2>nul
move /Y db_manager.py src\ 2>nul
move /Y listener.py src\ 2>nul
move /Y smart_home.py src\ 2>nul
move /Y system_control.py src\ 2>nul
move /Y telegram_bot.py src\ 2>nul
move /Y tts_module.py src\ 2>nul
move /Y utils.py src\ 2>nul
move /Y weather.py src\ 2>nul
move /Y websocket_manager.py src\ 2>nul
move /Y run_system.py src\ 2>nul
move /Y run_system_dashboard.py src\ 2>nul

echo.
echo Переміщення старих файлів...
move /Y index.html legacy\ 2>nul
move /Y index_win.py legacy\ 2>nul
move /Y test.py legacy\ 2>nul
move /Y test_performance.py legacy\ 2>nul
move /Y run_system.spec legacy\ 2>nul

echo.
echo Переміщення даних...
move /Y assistant.db data\ 2>nul
if exist model_vosk move /Y model_vosk data\ 2>nul

echo.
echo Видалення тимчасових файлів...
if exist __pycache__ rmdir /S /Q __pycache__
if exist .pytest_cache rmdir /S /Q .pytest_cache
if exist htmlcov rmdir /S /Q htmlcov
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if exist .coverage del /Q .coverage
if exist call del /Q call

echo.
echo ========================================
echo Готово! Структура організована.
echo ========================================
echo.
echo Наступні кроки:
echo 1. Перевір що все на місці
echo 2. Оновіть імпорти в коді (src/)
echo 3. Створи README.md
echo.
pause
