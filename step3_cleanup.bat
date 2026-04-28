@echo off
echo ========================================
echo AIVA - Крок 3: Очищення
echo ========================================
echo.

cd /d "%~dp0"

echo Видалення тимчасових файлів...
if exist __pycache__ rmdir /S /Q __pycache__
if exist src\__pycache__ rmdir /S /Q src\__pycache__
if exist .pytest_cache rmdir /S /Q .pytest_cache
if exist htmlcov rmdir /S /Q htmlcov
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if exist env rmdir /S /Q env
if exist indexer rmdir /S /Q indexer
if exist .coverage del /Q .coverage
if exist call del /Q call

echo.
echo ========================================
echo Очищення завершено!
echo ========================================
pause
