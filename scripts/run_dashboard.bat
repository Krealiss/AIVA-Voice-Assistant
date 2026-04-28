@echo off
echo ========================================
echo AIVA Dashboard - Запуск
echo ========================================
echo.

echo Запуск AIVA сервера...
start "AIVA Server" python agent_main.py

timeout /t 3 /nobreak > nul

echo Відкриваю dashboard в браузері...
start http://127.0.0.1:8787/dashboard

echo.
echo ========================================
echo Dashboard запущено!
echo URL: http://127.0.0.1:8787/dashboard
echo ========================================
echo.
echo Натисни Ctrl+C в вікні сервера для зупинки
pause
