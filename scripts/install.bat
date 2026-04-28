@echo off
echo ========================================
echo AIVA 2.0 - Installation
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] Installing core dependencies...
pip install fastapi uvicorn[standard] pydantic python-dotenv requests
pip install pymorphy2 pymorphy2-dicts-uk rapidfuzz
pip install pytest pytest-asyncio pytest-cov

echo.
echo [2/3] Creating data directories...
if not exist "data" mkdir data
if not exist "data\screenshots" mkdir data\screenshots

echo.
echo [3/3] Creating .env file...
if not exist ".env" (
    echo OLLAMA_HOST=http://localhost:11434 > .env
    echo LOG_LEVEL=INFO >> .env
    echo DB_PATH=data/assistant.db >> .env
    echo. >> .env
    echo # Optional: Add your API keys >> .env
    echo # ANTHROPIC_API_KEY=sk-ant-... >> .env
    echo # BOT_TOKEN=your_telegram_token >> .env
    echo # TUYA_ACCESS_ID=your_tuya_id >> .env
    echo # TUYA_ACCESS_KEY=your_tuya_key >> .env
    echo .env file created!
) else (
    echo .env file already exists, skipping...
)

echo.
echo ========================================
echo Installation complete!
echo.
echo To start AIVA:
echo   python src\dashboard_lite.py
echo.
echo Then open: http://127.0.0.1:8787/dashboard
echo ========================================
echo.
pause
