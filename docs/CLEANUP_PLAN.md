# Організація файлів AIVA

## Структура каталогів

```
AIVA/
├── docs/                    # Документація
│   ├── SUMMARY.md
│   ├── IMPROVEMENT_PLAN.md
│   ├── PERFORMANCE_IMPROVEMENTS.md
│   ├── QUICK_WINS.md
│   ├── UPDATE_GUIDE.md
│   ├── DASHBOARD_README.md
│   └── QUICK_START_DASHBOARD.md
│
├── scripts/                 # Скрипти запуску
│   ├── run_system.bat
│   ├── run_dashboard.bat
│   ├── run_dashboard_lite.bat
│   ├── run_with_dashboard.bat
│   ├── run_tests.bat
│   ├── install_all.bat
│   └── install_dependencies.bat
│
├── src/                     # Основний код
│   ├── agent_main.py
│   ├── ai_brain.py
│   ├── asr_whisper.py
│   ├── config.py
│   ├── dashboard_api.py
│   ├── dashboard_lite.py
│   ├── db_manager.py
│   ├── listener.py
│   ├── smart_home.py
│   ├── system_control.py
│   ├── telegram_bot.py
│   ├── tts_module.py
│   ├── utils.py
│   ├── weather.py
│   ├── websocket_manager.py
│   ├── run_system.py
│   └── run_system_dashboard.py
│
├── tests/                   # Тести
│   ├── __init__.py
│   ├── test_ai_brain.py
│   ├── test_db_manager.py
│   └── test_utils.py
│
├── static/                  # Статичні файли
│   └── dashboard.html
│
├── legacy/                  # Старі файли
│   ├── index.html
│   ├── index_win.py
│   ├── test.py
│   └── test_performance.py
│
├── data/                    # Дані
│   ├── assistant.db
│   └── model_vosk/
│
├── .env                     # Конфігурація (не в git)
├── .env.example             # Шаблон конфігурації
├── requirements.txt         # Залежності
├── pytest.ini              # Конфігурація pytest
└── README.md               # Головний README
```

## Команди для організації

```bash
# Створити структуру
mkdir docs scripts src legacy data

# Перемістити документацію
move *.md docs/

# Перемістити скрипти
move *.bat scripts/

# Перемістити код
move *.py src/

# Перемістити старі файли
move index.html legacy/
move index_win.py legacy/
move test.py legacy/
move test_performance.py legacy/

# Перемістити дані
move assistant.db data/
move model_vosk data/
```

## Що видалити

- `__pycache__/` - кеш Python
- `.pytest_cache/` - кеш pytest
- `htmlcov/` - звіти покриття
- `build/` - артефакти збірки
- `dist/` - дистрибутиви
- `env/` - віртуальне середовище (якщо не використовується)
- `.coverage` - файл покриття
- `call` - порожній файл
- `run_agent.bat` - дублікат
- `run_bot.bat` - дублікат
- `run_system.spec` - старий spec файл

## Що залишити в корені

- `.env` (не в git)
- `.env.example`
- `requirements.txt`
- `pytest.ini`
- `README.md` (створити)
- `AIVA.pyproj` (якщо використовується Visual Studio)
