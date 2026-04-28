@echo off
echo ========================================
echo AIVA - Запуск з Learning Systems
echo ========================================
echo.

cd /d "%~dp0\.."

echo Перевірка залежностей...
pip install -q pytest

echo.
echo Запуск AIVA з системами самонавчання...
echo - Analytics Engine: Tracking команд
echo - Habit Learner: Виявлення звичок
echo - Feedback System: Зворотний зв'язок
echo.

python src\agent_main.py

pause
