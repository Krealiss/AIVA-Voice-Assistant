@echo off
echo ========================================
echo AIVA Vision - Setup and Test
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] Installing Vision dependencies...
echo.

echo Installing Pillow (screenshot capture)...
pip install Pillow

echo.
echo Installing pytesseract (OCR)...
pip install pytesseract

echo.
echo Installing anthropic (Claude Vision API)...
pip install anthropic

echo.
echo ========================================
echo [2/3] Checking Tesseract OCR...
echo ========================================
echo.

where tesseract >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ Tesseract OCR found in PATH
    tesseract --version
) else (
    echo ❌ Tesseract OCR not found
    echo.
    echo Please download and install Tesseract OCR:
    echo https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo After installation, add to PATH or set in code:
    echo pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)

echo.
echo ========================================
echo [3/3] Running Vision System Test...
echo ========================================
echo.

python scripts\test_vision.py

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Add ANTHROPIC_API_KEY to .env file
echo 2. Run: python src\agent_main.py
echo 3. Test: curl -X POST http://127.0.0.1:8787/api/vision/describe
echo.
pause
