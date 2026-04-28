# AIVA Web Dashboard 🎛️

Сучасний веб-інтерфейс для керування та моніторингу AIVA.

## Можливості

### 📊 Real-time статистика
- Загальна кількість команд
- Успішні/невдалі команди
- Середній час відповіді
- Активні WebSocket з'єднання

### 🎤 Виконання команд
- Введення команд через веб-інтерфейс
- Миттєва відповідь від AIVA
- Історія виконаних команд

### 📜 Історія команд
- Всі виконані команди з timestamp
- Відповіді AIVA
- Статус виконання (успіх/помилка)
- Джерело команди (voice/telegram/web)

### 📋 Логи системи
- Real-time логи
- Рівні: INFO, WARNING, ERROR
- Автоматичне оновлення

### ⚡ WebSocket
- Real-time оновлення без перезавантаження
- Автоматичне перепідключення
- Ping/pong для підтримки з'єднання

---

## Запуск

### 1. Запусти AIVA сервер

```bash
python run_system.py
```

Або окремо:

```bash
python agent_main.py
```

### 2. Відкрий dashboard

Відкрий браузер та перейди на:

```
http://127.0.0.1:8787/dashboard
```

Або просто:

```
http://127.0.0.1:8787/
```

---

## API Endpoints

### Dashboard API

**GET** `/api/dashboard/stats`
- Отримати статистику системи

**GET** `/api/dashboard/history?limit=50&offset=0`
- Отримати історію команд

**POST** `/api/dashboard/history`
- Додати запис в історію

**DELETE** `/api/dashboard/history`
- Очистити історію

**GET** `/api/dashboard/settings`
- Отримати налаштування

**POST** `/api/dashboard/settings`
- Оновити налаштування

**GET** `/api/dashboard/logs?lines=100`
- Отримати останні логи

**POST** `/api/dashboard/command`
- Виконати команду
```json
{
  "command": "котра година"
}
```

### WebSocket

**WS** `/ws/dashboard`
- Real-time оновлення

**Типи повідомлень:**

```javascript
// Ping
{ "type": "ping" }

// Підписка на канали
{ "type": "subscribe", "channels": ["commands", "logs", "stats"] }

// Виконання команди
{ "type": "command", "command": "запусти Chrome" }
```

**Отримані повідомлення:**

```javascript
// Команда виконана
{
  "type": "command",
  "data": {
    "command": "...",
    "response": "...",
    "source": "web",
    "success": true,
    "timestamp": "2026-04-26T19:00:00"
  }
}

// Оновлення статусу
{
  "type": "status",
  "data": { ... }
}

// Лог повідомлення
{
  "type": "log",
  "data": {
    "level": "INFO",
    "message": "...",
    "timestamp": "2026-04-26T19:00:00"
  }
}
```

---

## Архітектура

```
┌─────────────────┐
│   Browser       │
│  (Dashboard)    │
└────────┬────────┘
         │ HTTP + WebSocket
         │
┌────────▼────────┐
│   FastAPI       │
│  agent_main.py  │
├─────────────────┤
│ dashboard_api   │ ← REST API
│ websocket_mgr   │ ← WebSocket
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│ AI   │  │ DB   │
│Brain │  │Manager│
└──────┘  └──────┘
```

---

## Технології

### Backend
- **FastAPI** - веб-фреймворк
- **WebSocket** - real-time комунікація
- **Pydantic** - валідація даних
- **SQLite** - база даних

### Frontend
- **Vanilla JS** - без фреймворків
- **WebSocket API** - real-time
- **Fetch API** - HTTP запити
- **CSS Grid** - адаптивна верстка

---

## Розробка

### Додавання нових endpoints

1. Відкрий `dashboard_api.py`
2. Додай новий endpoint:

```python
@router.get("/my-endpoint")
async def my_endpoint():
    return {"data": "..."}
```

3. Використай в frontend:

```javascript
const response = await fetch('/api/dashboard/my-endpoint');
const data = await response.json();
```

### Додавання WebSocket подій

1. Відкрий `websocket_manager.py`
2. Додай новий метод:

```python
async def broadcast_my_event(self, data):
    await self.broadcast({
        "type": "my_event",
        "data": data
    })
```

3. Обробка в frontend:

```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'my_event') {
        // Handle event
    }
};
```

---

## Troubleshooting

### Dashboard не відкривається

```bash
# Перевір чи запущений сервер
curl http://127.0.0.1:8787/api/health

# Перевір логи
tail -f logs/aiva.log
```

### WebSocket не підключається

1. Перевір консоль браузера (F12)
2. Переконайся що сервер запущений
3. Перевір firewall

### Статистика не оновлюється

1. Перевір WebSocket з'єднання
2. Відкрий Network tab в DevTools
3. Перезавантаж сторінку

---

## Майбутні покращення

- [ ] Графіки та діаграми (Chart.js)
- [ ] Темна тема
- [ ] Експорт історії в CSV/JSON
- [ ] Фільтри та пошук в історії
- [ ] Налаштування через UI
- [ ] Мультимовність
- [ ] Мобільна версія
- [ ] PWA підтримка
- [ ] Аутентифікація
- [ ] Ролі та права доступу

---

## Скріншоти

### Головна сторінка
![Dashboard](screenshots/dashboard.png)

### Статистика
![Stats](screenshots/stats.png)

### Історія команд
![History](screenshots/history.png)

---

**Версія:** 0.9.0  
**Дата:** 26.04.2026  
**Автор:** Andrew
