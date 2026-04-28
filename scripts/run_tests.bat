@echo off
echo ========================================
echo AIVA - Запуск тестів
echo ========================================
echo.

cd /d "%~dp0\.."

REM Встановлення pytest якщо потрібно
pip install pytest pytest-cov pytest-asyncio --quiet

echo Запуск тестів...
echo.

REM Запуск всіх тестів з покриттям
pytest src\tests\ -v --cov=src --cov-report=term-missing --cov-report=html

echo.
echo ========================================
echo Тести завершено!
echo HTML звіт: htmlcov/index.html
echo ========================================
pause
