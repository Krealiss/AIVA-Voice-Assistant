@echo off
echo ========================================
echo AIVA React Dashboard - Setup
echo ========================================
echo.

cd /d "%~dp0\.."

echo Installing frontend dependencies...
cd frontend
call npm install

echo.
echo Building React app...
call npm run build

echo.
echo ========================================
echo Setup complete!
echo.
echo To start development:
echo   cd frontend
echo   npm run dev
echo.
echo To build for production:
echo   cd frontend
echo   npm run build
echo ========================================
pause
