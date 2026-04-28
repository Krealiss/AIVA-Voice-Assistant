@echo off
echo Встановлення залежностей для AIVA v0.9.0...
echo.

pip install faster-whisper
pip install duckduckgo-search
pip install tuya-iot-py-sdk
pip install pymorphy2
pip install pymorphy2-dicts-uk

echo.
echo Готово! Тепер запусти: python test_performance.py
pause
