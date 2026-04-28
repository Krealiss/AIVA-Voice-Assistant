@echo off
echo ========================================
echo AIVA - Stop Server
echo ========================================
echo.

echo Stopping AIVA server on port 8787...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8787') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)

echo.
echo Server stopped!
echo.
pause
