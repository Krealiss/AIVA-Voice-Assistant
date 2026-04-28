@echo off
REM запуск системи
cd C:\Users\Andrew\source\repos\AIVA\AIVA
echo [AIVA] Запусаю систему...
call env\Scripts\activate
python run_system.py
pause
