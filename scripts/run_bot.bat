@echo off
REM запуск Telegram-бота
cd /d "%~dp0"
echo [AIVA] Запускаю Telegram-бота...
call env\Scripts\activate
python telegram_bot.py
pause
