@echo off
echo ========================================
echo AIVA - Запуск з Dashboard
echo ========================================
echo.

cd /d "%~dp0\.."

python src\run_system_dashboard.py

pause
