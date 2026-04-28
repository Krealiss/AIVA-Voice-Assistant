@echo off
echo ========================================
echo AIVA - Крок 1: Створення структури
echo ========================================
echo.

cd /d "%~dp0"

echo Створення папок...
if not exist docs mkdir docs
if not exist scripts mkdir scripts
if not exist src mkdir src
if not exist legacy mkdir legacy
if not exist data mkdir data

echo.
echo ========================================
echo Структура створена!
echo ========================================
pause
