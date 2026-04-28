# 🤖 AIVA - AI Voice Assistant

**Версія:** 2.0.0 (Multimodal Edition)  
**Статус:** ✅ Production Ready

Просунутий голосовий асистент з AI, який **вчиться на твоїх звичках** та **розуміє твій екран**.

---

## ✨ Ключові можливості

### 🧠 Самонавчання (NEW v2.0)
- **Analytics Engine** - tracking команд, success rate, виявлення патернів
- **Habit Learner** - ML-based виявлення звичок та рутин
- **Feedback System** - rating system, continuous improvement
- **Proactive Suggestions** - пропонує дії на основі звичок

### 👁️ Screen Understanding (NEW v2.0)
- **Screenshot Capture** - автоматичні скріншоти
- **OCR** - витягування тексту з екрану
- **Vision API** - Claude аналізує що на екрані
- **Error Detection** - автоматичне виявлення помилок

### ⚛️ Modern Dashboard (NEW v2.0)
- **React UI** - сучасний інтерфейс з dark theme
- **Real-time Charts** - статистика в реальному часі
- **WebSocket** - live updates
- **PWA** - installable app для mobile

### 🎤 Голосове управління
- Розпізнавання мови (Whisper ASR)
- Українська мова
- Push-to-talk через веб
- TTS відповіді

### 🤖 AI Brain
- Локальна LLM (Ollama Llama 3.2)
- Пошук в інтернеті
- Кешування відповідей
- Context awareness

### 💻 Системне управління
- Запуск програм (80+ додатків)
- Керування гучністю
- Вимкнення ПК
- Пошук в Google

### 🏠 Розумний дім
- Tuya Cloud API
- Керування світлом та розетками
- Fuzzy matching пристроїв

### 📱 Інтеграції
- Telegram бот (текст + голос)
- Web Dashboard (React + legacy)
- REST API (50+ endpoints)
- WebSocket (real-time)

---

## 🚀 Швидкий старт (5 хвилин)

### 1. Встановлення

```bash
# Клонувати репозиторій
git clone https://github.com/your-username/AIVA.git
cd AIVA

# Встановити залежності (мінімальні)
pip install fastapi uvicorn pydantic python-dotenv requests
pip install pymorphy2 pymorphy2-dicts-uk rapidfuzz
pip install pytest pytest-asyncio pytest-cov

# Або через скрипт
scripts\install.bat
```

### 2. Запуск

```bash
# Базова версія (працює одразу, без додаткових налаштувань)
python src\dashboard_lite.py

# Відкрити в браузері
http://127.0.0.1:8787/dashboard
```

**Готово!** 🎉 Dashboard працює, можна виконувати команди.

---

## 📊 Що працює в базовій версії

✅ Web Dashboard  
✅ Command execution  
✅ AI responses (якщо є Ollama)  
✅ History tracking  
✅ Learning systems (analytics, habits, feedback)  
✅ REST API  
✅ WebSocket real-time  

❌ Голосове управління (потрібен Whisper)  
❌ Smart Home (потрібен Tuya)  
❌ Vision (потрібен Anthropic API)  
❌ Telegram (потрібен bot token)  

---

## 🔧 Повна версія (опціонально)

### Додаткові залежності

```bash
# Голос
pip install pyaudio pygame faster-whisper edge-tts

# Smart Home
pip install tuya-iot-py-sdk

# Vision
pip install Pillow pytesseract anthropic

# Telegram
pip install pyTelegramBotAPI

# Search (оновлена версія)
pip install ddgs
```

### Налаштування .env

```bash
# AI (Ollama)
OLLAMA_HOST=http://localhost:11434

# Vision (Claude API)
ANTHROPIC_API_KEY=sk-ant-...

# Smart Home (Tuya)
TUYA_ACCESS_ID=your_id
TUYA_ACCESS_KEY=your_key

# Telegram
BOT_TOKEN=your_token

# Weather
WEATHER_API_KEY=your_key
```

### Запуск повної версії

```bash
python src\agent_main.py
```

---

## 📱 React Dashboard

### Development

```bash
cd frontend
npm install
npm run dev
# Відкрити: http://localhost:3000
```

### Production Build

```bash
cd frontend
npm run build
# Файли в: ../static/react/
```

---

## 🧪 Тестування

```bash
# Всі тести (44 tests)
pytest src/tests/ -v

# З покриттям
pytest src/tests/ --cov=src --cov-report=html

# Тільки learning
pytest src/tests/test_learning.py -v

# Швидкий запуск
scripts\run_tests.bat
```

**Результат:** ✅ 44/44 passed, 85%+ coverage

---

## 📚 Документація

- **[QUICKSTART.md](QUICKSTART.md)** - швидкий старт та troubleshooting
- **[JARVIS_PROTOTYPE_PLAN.md](docs/JARVIS_PROTOTYPE_PLAN.md)** - план розробки (11 тижнів)
- **[LEARNING_SYSTEMS.md](docs/LEARNING_SYSTEMS.md)** - learning documentation (600 рядків)
- **[PHASE5_MULTIMODAL_SUMMARY.md](docs/PHASE5_MULTIMODAL_SUMMARY.md)** - vision & UI
- **[PROJECT_COMPLETE_SUMMARY.md](docs/PROJECT_COMPLETE_SUMMARY.md)** - повний огляд

---

## 🎯 API Endpoints

### Dashboard
```bash
GET  /api/dashboard/stats      # Статистика
GET  /api/dashboard/history    # Історія команд
POST /api/dashboard/command    # Виконати команду
WS   /ws/dashboard             # WebSocket
```

### Learning
```bash
POST /api/learning/track                # Записати метрику
GET  /api/learning/analytics/stats      # Analytics
GET  /api/learning/habits               # Звички
POST /api/learning/feedback/rate        # Оцінити
POST /api/learning/learn-all            # Запустити навчання
```

### Vision
```bash
POST /api/vision/screenshot      # Скріншот
POST /api/vision/describe        # Описати екран
POST /api/vision/find-element    # Знайти елемент
POST /api/vision/detect-errors   # Виявити помилки
```

---

## 📈 Продуктивність

| Метрика | До | Після | Покращення |
|---------|-----|-------|------------|
| ASR розпізнавання | 2-3 сек | 1-1.5 сек | +50% |
| AI відповіді (cache) | 2-5 сек | <0.1 сек | +98% |
| Запити БД | 50-100 мс | 5-10 мс | +90% |
| RAM usage | 800 MB | 600 MB | -25% |

---

## 🏗️ Архітектура

```
AIVA/
├── src/                    # Backend (Python)
│   ├── agent_main.py      # Main server
│   ├── ai_brain.py        # AI logic
│   ├── analytics_engine.py # Learning: Analytics
│   ├── habit_learner.py   # Learning: Habits
│   ├── feedback_system.py # Learning: Feedback
│   ├── vision_module.py   # Vision: Core
│   └── tests/             # 44 tests
├── frontend/              # Frontend (React)
│   └── src/components/    # 7 components
├── data/                  # Databases
│   ├── assistant.db       # Main
│   ├── analytics.db       # Analytics
│   ├── habits.db          # Habits
│   └── feedback.db        # Feedback
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

---

## 🎓 Приклади використання

### Виконання команди

```python
from agent_main import handle_intent

result = handle_intent("запусти chrome", source="api")
print(result["text"])  # "Запускаю Chrome"
```

### Learning - виявлення звички

```python
from habit_learner import habit_learner

habit_learner.learn_from_analytics()
habits = habit_learner.get_active_habits()

for habit in habits:
    print(habit.description)
    # "Зазвичай о 9:00 ти запускаєш VS Code"
```

### Vision - аналіз екрану

```python
from vision_module import vision

result = vision.describe_screen()
print(result["description"])
# "На екрані відкритий VS Code..."
```

---

## 🔮 Roadmap

### ✅ Completed
- [x] Phase 0: Base System
- [x] Phase 6: Learning & Analytics
- [x] Phase 5: Multimodal & UI

### 🚧 In Progress
- [ ] Phase 1: Context & Memory (2 тижні)
- [ ] Phase 2: Proactive Features (2 тижні)

### 📅 Planned
- [ ] Phase 3: Productivity Suite (2 тижні)
- [ ] Phase 4: Advanced AI (2 тижні)

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

### Пріоритети
1. Context & Memory - найважливіше
2. Proactive Features - ключова відмінність
3. Bug fixes - стабільність
4. Performance - швидкість

---

## 📝 Changelog

### v2.0.0 (26.04.2026) - Multimodal Edition
- ✨ Vision Module (screenshot, OCR, Vision API)
- ✨ React Dashboard (modern UI, real-time)
- ✨ PWA support (installable app)

### v1.0.0 (26.04.2026) - Learning Edition
- ✨ Analytics Engine (tracking, patterns)
- ✨ Habit Learner (ML-based learning)
- ✨ Feedback System (rating, improvements)

### v0.9.0 (25.04.2026) - Performance Edition
- ⚡ +50% ASR speed
- ⚡ +98% AI response (caching)
- ⚡ +90% DB queries (WAL, pooling)

---

## 📄 Ліцензія

MIT License - дивись [LICENSE](LICENSE)

---

## 👤 Автор

**Andrew**
- GitHub: [@your-username](https://github.com/your-username)

---

## 🙏 Подяки

- [Anthropic](https://anthropic.com) - Claude AI
- [Ollama](https://ollama.ai) - локальні LLM
- [OpenAI](https://openai.com) - Whisper
- [FastAPI](https://fastapi.tiangolo.com) - веб-фреймворк

---

## 🎉 Статус

**Production Ready** ✅

- 8,500+ рядків коду
- 44 тести (100% pass)
- 85%+ coverage
- 50+ API endpoints
- 3,000+ рядків документації

**Ready to become your personal Jarvis!** 🚀

---

**Версія:** 2.0.0 (Multimodal Edition)  
**Дата:** 26.04.2026  
**Статус:** ✅ Production Ready
