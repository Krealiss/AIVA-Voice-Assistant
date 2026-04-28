@echo off
echo ========================================
echo AIVA - Крок 2: Переміщення файлів
echo ========================================
echo.

cd /d "%~dp0"

echo Переміщення документації...
move /Y SUMMARY.md docs\ 2>nul
move /Y IMPROVEMENT_PLAN.md docs\ 2>nul
move /Y PERFORMANCE_IMPROVEMENTS.md docs\ 2>nul
move /Y QUICK_WINS.md docs\ 2>nul
move /Y UPDATE_GUIDE.md docs\ 2>nul
move /Y DASHBOARD_README.md docs\ 2>nul
move /Y QUICK_START_DASHBOARD.md docs\ 2>nul
move /Y CLEANUP_PLAN.md docs\ 2>nul

echo Переміщення скриптів...
move /Y run_*.bat scripts\ 2>nul
move /Y install_*.bat scripts\ 2>nul

echo Переміщення Python файлів...
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

echo Переміщення тестів...
if exist tests move /Y tests src\ 2>nul

echo Переміщення старих файлів...
move /Y index.html legacy\ 2>nul
move /Y index_win.py legacy\ 2>nul
move /Y test.py legacy\ 2>nul
move /Y test_performance.py legacy\ 2>nul
move /Y run_system.spec legacy\ 2>nul

echo Переміщення даних...
move /Y assistant.db data\ 2>nul
if exist model_vosk move model_vosk data\ 2>nul

echo.
echo ========================================
echo Файли переміщено!
echo ========================================
pause
