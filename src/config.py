import os
from dotenv import load_dotenv, dotenv_values

# Завантаження змінних із .env (на рівень вище)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)
env_map = dotenv_values(env_path)

def env(key: str, default: str = "") -> str:
    """
    Безпечне отримання змінної середовища.
    Враховує можливий BOM (\ufeff) на початку ключа.
    """
    return (
        os.getenv(key)
        or env_map.get(key)
        or env_map.get("\ufeff" + key)
        or default
    )

# ---------- Конфігурація ----------
BOT_TOKEN = env("BOT_TOKEN")
AGENT_URL = env("AGENT_URL", "http://127.0.0.1:8787")
DB_PATH   = env("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "assistant.db"))
LOG_LEVEL = env("LOG_LEVEL", "INFO")
OLLAMA_HOST = env("OLLAMA_HOST", "http://127.0.0.1:11434")

# ---------- Перевірка ----------
if BOT_TOKEN and ":" not in BOT_TOKEN:
    raise RuntimeError(
        "❌ BOT_TOKEN некоректний (відсутній символ ':')."
        "Перевір .env (UTF-8 без BOM) і правильність значення."
    )

print(f"Конфігурація завантажена. Рівень логів: {LOG_LEVEL}")
