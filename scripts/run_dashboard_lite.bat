@echo off
echo ========================================
echo AIVA Dashboard Lite - Запуск
echo ========================================
echo.

cd /d "%~dp0\.."

echo Запуск dashboard (без голосових функцій)...
start "AIVA Dashboard" python src\dashboard_lite.py

timeout /t 3 /nobreak > nul

echo Відкриваю dashboard в браузері...
start http://127.0.0.1:8787/dashboard

echo.
echo ========================================
echo Dashboard запущено!
echo URL: http://127.0.0.1:8787/dashboard
echo ========================================
echo.
pause
