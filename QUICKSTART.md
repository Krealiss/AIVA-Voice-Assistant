# 🚀 AIVA - Quick Start Guide

## Швидкий старт (5 хвилин)

### 1. Встановлення базових залежностей

```bash
# Основні модулі (обов'язково)
pip install fastapi uvicorn[standard] pydantic python-dotenv
pip install faster-whisper requests
pip install pymorphy2 rapidfuzz

# Audio (для голосу)
pip install pyaudio pygame

# Testing
pip install pytest pytest-asyncio pytest-cov
```

### 2. Налаштування .env

```bash
# Створити .env файл
copy .env.example .env

# Мінімальна конфігурація
OLLAMA_HOST=http://localhost:11434
LOG_LEVEL=INFO
DB_PATH=data/assistant.db
```

### 3. Запуск

```bash
# Базова версія (без голосу, без smart home)
python src/dashboard_lite.py

# Відкрити в браузері
http://127.0.0.1:8787/dashboard
```

---

## Повна версія (опціонально)

### Додаткові залежності

```bash
# Smart Home (Tuya)
pip install tuya-connector

# TTS (Text-to-Speech)
pip install edge-tts

# Search (оновлена версія)
pip install ddgs

# Vision (Screen Understanding)
pip install Pillow pytesseract anthropic

# Telegram Bot
pip install pyTelegramBotAPI
```

### Додаткові налаштування .env

```bash
# Smart Home
TUYA_ACCESS_ID=your_access_id
TUYA_ACCESS_KEY=your_access_key

# Telegram
BOT_TOKEN=your_bot_token

# Vision (Claude API)
ANTHROPIC_API_KEY=sk-ant-...

# Weather
WEATHER_API_KEY=your_openweather_key
```

### Запуск повної версії

```bash
python src/agent_main.py
```

---

## Помилки та рішення

### ModuleNotFoundError: tuya_connector

**Рішення 1:** Встановити модуль
```bash
pip install tuya-connector
```

**Рішення 2:** Використати lite версію
```bash
python src/dashboard_lite.py
```

### ModuleNotFoundError: edge_tts

**Рішення:** Встановити або використати без TTS
```bash
pip install edge-tts
```

### duckduckgo_search deprecated

**Рішення:** Оновити на ddgs
```bash
pip uninstall duckduckgo-search
pip install ddgs
```

### Logger not defined

**Виправлено:** Оновіть agent_main.py (logger тепер визначається до імпортів)

---

## Тестування

```bash
# Запустити всі тести
pytest src/tests/ -v

# Тільки базові (без learning)
pytest src/tests/test_utils.py src/tests/test_ai_brain.py -v

# З покриттям
pytest src/tests/ --cov=src
```

---

## React Dashboard (опціонально)

```bash
# Setup
cd frontend
npm install

# Development
npm run dev
# Відкрити: http://localhost:3000

# Build для production
npm run build
# Файли в: ../static/react/
```

---

## Мінімальна конфігурація (працює без інтернету)

**Що потрібно:**
- Python 3.10+
- FastAPI + Uvicorn
- SQLite (вбудований)

**Що працює:**
- ✅ Web Dashboard
- ✅ Command execution
- ✅ History tracking
- ✅ Database management

**Що НЕ працює без додаткових модулів:**
- ❌ Голосове управління (потрібен Whisper)
- ❌ AI відповіді (потрібен Ollama)
- ❌ Smart Home (потрібен Tuya)
- ❌ Vision (потрібен Anthropic API)

---

## Рекомендована конфігурація

**Для розробки:**
```bash
pip install -r requirements.txt
# Закоментувати optional модулі які не потрібні
```

**Для production:**
```bash
# Тільки те що використовується
pip install fastapi uvicorn pydantic python-dotenv
pip install faster-whisper requests pymorphy2 rapidfuzz
pip install pyaudio pygame
```

---

## Перевірка роботи

### 1. Базовий тест

```bash
# Запустити dashboard lite
python src/dashboard_lite.py

# Відкрити http://127.0.0.1:8787/dashboard
# Ввести команду: "привіт"
# Має відповісти AI
```

### 2. API тест

```bash
# Запустити сервер
python src/agent_main.py

# В іншому терміналі
curl http://127.0.0.1:8787/api/health
# Має повернути: {"ok": true, "version": "2.0.0"}
```

### 3. Learning тест

```bash
# Перевірити analytics
curl http://127.0.0.1:8787/api/learning/analytics/stats

# Перевірити habits
curl http://127.0.0.1:8787/api/learning/habits
```

---

## Troubleshooting

### Порт 8787 зайнятий

```bash
# Змінити порт в agent_main.py
uvicorn.run(app, host="127.0.0.1", port=8888)
```

### Ollama не запущений

```bash
# Встановити Ollama
# https://ollama.ai

# Запустити модель
ollama run llama3.2
```

### Whisper модель не завантажується

```bash
# Перший запуск завантажує модель (~150MB)
# Зачекайте 2-3 хвилини
```

---

## Наступні кроки

1. ✅ Запустити базову версію
2. ✅ Перевірити dashboard
3. ⬜ Додати Ollama для AI
4. ⬜ Налаштувати голосове управління
5. ⬜ Додати Vision API (опціонально)
6. ⬜ Налаштувати Smart Home (опціонально)

---

**Потрібна допомога?**
- Документація: `docs/`
- Issues: GitHub Issues
- Telegram: @aiva_support (якщо є)

**Готово!** 🎉
