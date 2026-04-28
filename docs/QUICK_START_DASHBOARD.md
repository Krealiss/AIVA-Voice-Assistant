# AIVA - Швидкий старт Dashboard

## Проблема з запуском?

Якщо `agent_main.py` не запускається через відсутні модулі, використай **Lite версію**:

### Варіант 1: Dashboard Lite (рекомендовано для тестування)

```bash
# Запусти спрощену версію без голосових функцій
run_dashboard_lite.bat
```

Або вручну:
```bash
python dashboard_lite.py
```

Потім відкрий: http://127.0.0.1:8787/dashboard

### Варіант 2: Повна версія (з усіма функціями)

1. Встанови всі залежності:
```bash
install_all.bat
```

Або вручну:
```bash
pip install edge-tts pygame comtypes
```

2. Запусти повну версію:
```bash
run_dashboard.bat
```

---

## Що працює в Lite версії?

✅ Web Dashboard  
✅ REST API  
✅ WebSocket  
✅ Статистика  
✅ Історія команд  
✅ Виконання команд через UI  

❌ Голосове розпізнавання  
❌ TTS (синтез мови)  
❌ Розумний дім  
❌ Listener  

---

## Troubleshooting

### ModuleNotFoundError: No module named 'X'

```bash
pip install X
```

### Port 8787 already in use

```bash
# Зміни порт в dashboard_lite.py
uvicorn.run(app, host="127.0.0.1", port=8788)
```

### Dashboard не відкривається

1. Перевір чи запущений сервер
2. Відкрий вручну: http://127.0.0.1:8787/dashboard
3. Перевір логи в консолі

---

## Мінімальні залежності для Dashboard

```bash
pip install fastapi uvicorn
```

Це все що потрібно для dashboard!

---

**Рекомендація:** Спочатку протестуй Dashboard Lite, потім встанови решту модулів для повної версії.
