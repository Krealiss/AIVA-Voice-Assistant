@echo off
REM запуск локального агента FastAPI
cd /d "%~dp0"
echo [AIVA] Запускаю Local Agent...
call env\Scripts\activate
uvicorn agent_main:app --host 127.0.0.1 --port 8787
pause
