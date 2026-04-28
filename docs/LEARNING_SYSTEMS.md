# 🧠 Learning Systems - Документація

**Версія:** 1.0.0  
**Дата:** 26.04.2026

---

## Огляд

AIVA тепер має три інтегровані системи самонавчання:

1. **Analytics Engine** - збір та аналіз метрик використання
2. **Habit Learner** - виявлення звичок та патернів поведінки
3. **Feedback System** - зворотний зв'язок та continuous improvement

---

## 📊 Analytics Engine

### Можливості

- Tracking всіх команд (час, успішність, тривалість)
- Success rate по типах intent
- Performance metrics (avg/min/max duration)
- Топ команд
- Розподіл використання по годинах та днях
- Автоматичне виявлення патернів

### API Endpoints

```bash
# Записати метрику
POST /api/learning/track
{
  "command": "запусти chrome",
  "intent_type": "run",
  "success": true,
  "duration_ms": 150.5,
  "source": "voice"
}

# Отримати статистику
GET /api/learning/analytics/stats

# Success rate
GET /api/learning/analytics/success-rate?hours=24

# Performance
GET /api/learning/analytics/performance?hours=24

# Топ команд
GET /api/learning/analytics/top-commands?limit=10

# Запустити аналіз патернів
POST /api/learning/analytics/analyze
```

### Використання в коді

```python
from analytics_engine import analytics, CommandMetric
from datetime import datetime

# Записати команду
analytics.track_command(CommandMetric(
    command="запусти steam",
    intent_type="run",
    success=True,
    duration_ms=120.0,
    timestamp=datetime.now(),
    source="voice"
))

# Отримати статистику
stats = analytics.get_success_rate(hours=24)
print(f"Success rate: {stats['success_rate']}%")

# Топ команд
top = analytics.get_top_commands(limit=5)
for cmd, count in top:
    print(f"{cmd}: {count} разів")
```

---

## 🎯 Habit Learner

### Можливості

- Виявлення рутин (команди в певний час)
- Виявлення послідовностей (команда A → команда B)
- Виявлення вподобань (улюблені програми)
- Проактивні пропозиції
- Навчання на прийнятті/відхиленні

### Типи звичок

**1. Routine (рутина)**
```
Тригер: Час доби (година)
Приклад: "Зазвичай о 9:00 ти запускаєш VS Code"
```

**2. Trigger (послідовність)**
```
Тригер: Попередня команда
Приклад: "Після 'запусти steam' ти часто запускаєш CS 2"
```

**3. Preference (вподобання)**
```
Тип: Улюблені програми, час активності
Приклад: "Твої топ-3 програми: Chrome, VS Code, Steam"
```

### API Endpoints

```bash
# Отримати звички
GET /api/learning/habits?min_confidence=0.5

# Запустити навчання
POST /api/learning/habits/learn

# Записати взаємодію (accepted/rejected/ignored)
POST /api/learning/habits/interact
{
  "habit_id": 1,
  "action": "accepted"
}

# Отримати пропозиції
GET /api/learning/habits/suggestions?last_command=запусти%20steam

# Отримати вподобання
GET /api/learning/preferences?preference_type=favorite_app
```

### Використання в коді

```python
from habit_learner import habit_learner

# Навчання на analytics даних
habit_learner.learn_from_analytics()

# Отримати активні звички
habits = habit_learner.get_active_habits(min_confidence=0.6)
for habit in habits:
    print(f"{habit.description} (confidence: {habit.confidence})")

# Перевірити тригери
context = {"last_command": "запусти steam"}
triggered = habit_learner.check_triggers(context)

# Отримати пропозицію
suggestion = habit_learner.get_suggestion(context)
if suggestion:
    print(f"💡 {suggestion}")

# Записати взаємодію
habit_learner.record_interaction(habit_id=1, action="accepted")
```

### Життєвий цикл звички

```
1. Виявлення (3+ спостережень) → confidence: 0.3-0.5
2. Підтвердження (користувач приймає) → confidence: +0.05
3. Відхилення (користувач відхиляє) → confidence: -0.1
4. Деактивація (3+ відхилення) → active: False
```

---

## 💬 Feedback System

### Можливості

- Оцінка відповідей (1-5 зірок)
- Повідомлення про помилки
- Позитивні відгуки
- Виправлення від користувача
- Аналіз низькорейтингових команд
- Автоматичне навчання

### Типи feedback

- **RATING** - оцінка відповіді (1-5)
- **CORRECTION** - виправлення
- **COMPLAINT** - скарга на помилку
- **PRAISE** - позитивний відгук
- **SUGGESTION** - пропозиція покращення

### API Endpoints

```bash
# Подати feedback
POST /api/learning/feedback
{
  "feedback_type": "rating",
  "command": "запусти chrome",
  "response": "Запускаю Chrome",
  "user_input": "",
  "rating": 5,
  "comment": "Відмінно!"
}

# Оцінити відповідь
POST /api/learning/feedback/rate
{
  "command": "запусти chrome",
  "response": "Запускаю Chrome",
  "rating": 5,
  "comment": "Швидко і точно"
}

# Статистика
GET /api/learning/feedback/stats

# Середня оцінка
GET /api/learning/feedback/average-rating?days=7

# Навчання на feedback
POST /api/learning/feedback/learn

# Аналіз виправлень
GET /api/learning/feedback/corrections
```

### Використання в коді

```python
from feedback_system import feedback_system

# Оцінити відповідь
feedback_system.rate_response(
    command="запусти chrome",
    response="Запускаю Chrome",
    rating=5,
    comment="Швидко!"
)

# Повідомити про помилку
feedback_system.report_error(
    command="запусти хром",
    response="Не знайдено",
    error_description="Не розпізнав 'хром' як Chrome"
)

# Позитивний відгук
feedback_system.praise_response(
    command="погода",
    response="Зараз +15°C",
    comment="Корисна інформація"
)

# Статистика
stats = feedback_system.get_feedback_stats()
print(f"Середня оцінка: {stats['average_rating']}")

# Команди з низькими оцінками
low_rated = feedback_system.get_low_rated_commands(threshold=2)
for cmd in low_rated:
    print(f"{cmd['command']}: {cmd['avg_rating']} ⭐")
```

---

## 🔄 Інтеграція

### Автоматичний tracking

Всі команди через `handle_intent()` автоматично записуються в analytics:

```python
# agent_main.py
def handle_intent(text: str, source: str = "voice") -> Optional[Dict]:
    start_time = time.time()
    
    # ... обробка команди ...
    
    # Автоматичний tracking
    duration_ms = (time.time() - start_time) * 1000
    if LEARNING_ENABLED:
        analytics.track_command(CommandMetric(
            command=text,
            intent_type=verb_type or "unknown",
            success=True,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            source=source
        ))
```

### Проактивні пропозиції

```python
# Перевірка тригерів після кожної команди
context = {"last_command": last_executed_command}
suggestion = habit_learner.get_suggestion(context)

if suggestion:
    # Показати користувачу
    print(f"💡 {suggestion}")
    # Або через WebSocket
    await ws_manager.broadcast_suggestion(suggestion)
```

### Періодичне навчання

```python
# Запускати раз на день (через cron або APScheduler)
def daily_learning():
    # 1. Аналіз патернів
    analytics.analyze_and_update_patterns()
    
    # 2. Навчання на звичках
    habit_learner.learn_from_analytics()
    
    # 3. Обробка feedback
    feedback_system.learn_from_feedback()
```

---

## 📈 Dashboard Integration

### Нові секції dashboard

**1. Analytics**
- Success rate chart
- Performance metrics
- Top commands
- Usage heatmap (по годинах)

**2. Habits**
- Список активних звичок
- Confidence bars
- Accept/Reject buttons
- Suggestions panel

**3. Feedback**
- Average rating
- Rating distribution
- Recent feedback
- Low-rated commands

### WebSocket events

```javascript
// Нова пропозиція
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'suggestion') {
    showSuggestion(data.text, data.habit_id);
  }
  
  if (data.type === 'habit_learned') {
    updateHabitsList();
  }
}
```

---

## 🧪 Тестування

```bash
# Запуск тестів
pytest src/tests/test_learning.py -v

# З покриттям
pytest src/tests/test_learning.py --cov=src --cov-report=html
```

### Тестові сценарії

- ✅ Analytics tracking
- ✅ Success rate calculation
- ✅ Performance stats
- ✅ Pattern detection
- ✅ Habit learning (routines, sequences)
- ✅ Habit interactions (accept/reject)
- ✅ Preferences learning
- ✅ Feedback submission
- ✅ Rating system
- ✅ Low-rated commands detection

---

## 🗄️ База даних

### Структура

**analytics.db**
```sql
command_metrics (id, command, intent_type, success, duration_ms, timestamp, source, user_id, error)
usage_patterns (id, pattern_type, description, confidence, occurrences, last_seen, metadata, active)
```

**habits.db**
```sql
habits (id, habit_type, description, trigger_condition, suggested_action, confidence, times_observed, times_accepted, times_rejected, last_triggered, created_at, active)
preferences (id, preference_type, key, value, confidence, learned_from, updated_at)
habit_interactions (id, habit_id, action, timestamp)
```

**feedback.db**
```sql
feedback (id, feedback_type, command, response, user_input, rating, comment, timestamp, processed, applied)
corrections (id, original_command, original_response, corrected_response, correction_type, timestamp, applied)
improvements (id, improvement_type, description, before_value, after_value, confidence, applied_at, source_feedback_id)
```

---

## 🚀 Запуск

### З learning системами

```bash
# Повна версія з learning
python src/agent_main.py

# Або через скрипт
scripts\run_with_learning.bat
```

### Без learning (fallback)

Якщо модулі не встановлені, система працює без learning features:

```python
try:
    from analytics_engine import analytics
    LEARNING_ENABLED = True
except ImportError:
    LEARNING_ENABLED = False
```

---

## 📊 Приклади використання

### Сценарій 1: Виявлення ранкової рутини

```
День 1-5: Користувач щодня о 9:00 запускає VS Code
День 6: Система виявляє патерн (confidence: 0.6)
День 7 о 9:00: "Зазвичай в цей час ти запускаєш VS Code. Хочеш?"
Користувач: "Так" → confidence: 0.65
```

### Сценарій 2: Послідовність команд

```
Користувач часто: "запусти steam" → "запусти cs 2"
Після 3+ спостережень:
  Користувач: "запусти steam"
  Система: "Може також запустити CS 2?"
```

### Сценарій 3: Навчання на помилках

```
Користувач: "запусти хром"
Система: "Не знайдено"
Користувач: ⭐ (1 зірка) "Не розпізнав Chrome"
Система: Додає "хром" → "chrome" в aliases
```

---

## 🔧 Налаштування

### Параметри навчання

```python
# analytics_engine.py
MIN_OCCURRENCES = 3  # Мінімум спостережень для патерну
CONFIDENCE_THRESHOLD = 0.5  # Мінімальна впевненість

# habit_learner.py
MIN_CONFIDENCE = 0.5  # Показувати звички з confidence >= 0.5
REJECTION_LIMIT = 3  # Деактивувати після 3 відхилень

# feedback_system.py
LOW_RATING_THRESHOLD = 2  # Оцінки <= 2 вважаються низькими
```

---

## 📝 Best Practices

1. **Не спамити пропозиціями** - показувати максимум 1-2 на день
2. **Поважати відхилення** - якщо користувач відхилив 3 рази, більше не пропонувати
3. **Прозорість** - показувати, чому система щось пропонує
4. **Контроль** - дати можливість вимкнути learning
5. **Приватність** - всі дані локально, не відправляти в cloud

---

## 🎯 Метрики успіху

- **Acceptance rate** - % прийнятих пропозицій (ціль: >50%)
- **Average rating** - середня оцінка (ціль: >4.0)
- **Pattern accuracy** - точність виявлених патернів (ціль: >80%)
- **Response time** - час відповіді (ціль: <100ms для local)

---

## 🔮 Майбутні покращення

- [ ] ML моделі для кращого prediction
- [ ] Semantic similarity для команд (embeddings)
- [ ] Multi-user support (профілі)
- [ ] Cloud sync (опціонально)
- [ ] Voice feedback ("це було корисно?")
- [ ] A/B testing для різних підходів

---

**Автор:** Andrew  
**Дата:** 26.04.2026  
**Версія:** 1.0.0
