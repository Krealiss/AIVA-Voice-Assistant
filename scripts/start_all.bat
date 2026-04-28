@echo off
echo ========================================
echo AIVA - Starting Full System
echo ========================================
echo.

cd /d "%~dp0\.."

echo Checking ports...
echo Stopping any process on port 8787...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8787') do (
    taskkill /F /PID %%a 2>nul
)

timeout /t 2 /nobreak >nul

echo.
echo [1/3] Starting AIVA Backend (port 8787)...
start "AIVA Backend" cmd /k "python src\agent_main.py"

timeout /t 3 /nobreak >nul

echo [2/3] Starting Telegram Bot...
start "AIVA Telegram Bot" cmd /k "python src\telegram_bot.py"

timeout /t 2 /nobreak >nul

echo [3/3] Starting React Dashboard (port 3001)...
cd frontend
start "React Dashboard" cmd /k "npm run dev"

echo.
echo ========================================
echo System Starting!
echo ========================================
echo.
echo Backend:   http://127.0.0.1:8787
echo Telegram:  @aiva_anibase_bot
echo Dashboard: http://localhost:3001
echo.
echo Press any key to open dashboard in browser...
pause >nul

start http://localhost:3001

echo.
echo All services are running in separate windows.
echo Close those windows to stop the servers.
echo.
pause
