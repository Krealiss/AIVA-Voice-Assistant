"""
API endpoints для веб-dashboard
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging
import sqlite3
import time
import psutil

logger = logging.getLogger("dashboard_api")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MAX_HISTORY = 500

# Uptime tracking
START_TIME = time.time()


class HistoryDB:
    """Персистентна історія команд у SQLite"""

    def __init__(self, db_path: str = "data/dashboard_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_history (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    command TEXT NOT NULL,
                    response TEXT NOT NULL,
                    source TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    duration_ms REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON command_history(timestamp DESC)")
            conn.commit()
        logger.info(f"Dashboard history DB: {self.db_path}")

    def add(self, record: Dict) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO command_history
                (id, timestamp, command, response, source, success, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record["id"],
                record["timestamp"] if isinstance(record["timestamp"], str) else record["timestamp"].isoformat(),
                record["command"],
                record["response"],
                record["source"],
                int(record["success"]),
                record.get("duration_ms")
            ))
            # Обмежуємо кількість записів
            conn.execute("""
                DELETE FROM command_history WHERE id NOT IN (
                    SELECT id FROM command_history ORDER BY timestamp DESC LIMIT ?
                )
            """, (MAX_HISTORY,))
            conn.commit()

    def get(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM command_history
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(success) as successful,
                    AVG(duration_ms) as avg_time
                FROM command_history
            """).fetchone()
        total = row[0] or 0
        successful = row[1] or 0
        avg_time = row[2] or 0.0
        return {"total": total, "successful": successful, "failed": total - successful, "avg_time": avg_time}

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM command_history")
            conn.commit()


history_db = HistoryDB()

class CommandRecord(BaseModel):
    id: str
    timestamp: datetime
    command: str
    response: str
    source: str  # "voice", "telegram", "web"
    success: bool
    duration_ms: Optional[float] = None

class SystemStats(BaseModel):
    uptime_seconds: float
    total_commands: int
    successful_commands: int
    failed_commands: int
    avg_response_time_ms: float
    active_connections: int
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float

class SettingsUpdate(BaseModel):
    key: str
    value: Any

class CommandRequest(BaseModel):
    command: str


@router.get("/stats", response_model=SystemStats)
async def get_system_stats():
    """Отримати статистику системи"""
    db_stats = history_db.stats()
    total = db_stats["total"]
    successful = db_stats["successful"]
    failed = db_stats["failed"]
    avg_time = db_stats["avg_time"]

    # Реальний uptime
    uptime = time.time() - START_TIME

    # Підрахунок активних WebSocket з'єднань
    active_ws = 0
    try:
        from websocket_manager import manager
        active_ws = len(manager.active_connections)
    except Exception as e:
        logger.debug(f"Could not get WebSocket connections: {e}")

    # Системні ресурси
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024  # Bytes to MB
    memory_percent = process.memory_percent()
    cpu_percent = process.cpu_percent(interval=0.1)

    return SystemStats(
        uptime_seconds=uptime,
        total_commands=total,
        successful_commands=successful,
        failed_commands=failed,
        avg_response_time_ms=avg_time,
        active_connections=active_ws,
        memory_usage_mb=round(memory_mb, 2),
        memory_percent=round(memory_percent, 2),
        cpu_percent=round(cpu_percent, 2)
    )


@router.get("/history", response_model=List[CommandRecord])
async def get_command_history(limit: int = 50, offset: int = 0):
    """Отримати історію команд"""
    rows = history_db.get(limit=limit, offset=offset)
    return [CommandRecord(**row) for row in rows]


@router.post("/history")
async def add_command_record(record: CommandRecord):
    """Додати запис в історію"""
    history_db.add(record.model_dump())
    return {"ok": True, "id": record.id}


@router.delete("/history")
async def clear_history():
    """Очистити історію команд"""
    history_db.clear()
    return {"ok": True, "message": "Історію очищено"}


@router.get("/settings/schema")
async def get_settings_schema():
    """Отримати схему налаштувань з описами та типами"""
    return {
        "categories": {
            "vision": {
                "label": "Vision System",
                "settings": {
                    "vision_quality": {
                        "type": "number",
                        "label": "Якість стиснення JPEG",
                        "description": "Якість стиснення зображень (1-100)",
                        "default": 85,
                        "min": 1,
                        "max": 100
                    },
                    "vision_cache_ttl": {
                        "type": "number",
                        "label": "TTL кешу (секунди)",
                        "description": "Час життя кешу Vision результатів",
                        "default": 300,
                        "min": 60,
                        "max": 3600
                    },
                    "vision_max_width": {
                        "type": "number",
                        "label": "Максимальна ширина",
                        "description": "Максимальна ширина зображення для аналізу",
                        "default": 1920,
                        "min": 800,
                        "max": 3840
                    },
                    "vision_max_height": {
                        "type": "number",
                        "label": "Максимальна висота",
                        "description": "Максимальна висота зображення для аналізу",
                        "default": 1080,
                        "min": 600,
                        "max": 2160
                    }
                }
            },
            "learning": {
                "label": "Learning System",
                "settings": {
                    "analytics_enabled": {
                        "type": "boolean",
                        "label": "Увімкнути аналітику",
                        "description": "Збирати статистику використання",
                        "default": True
                    },
                    "habits_enabled": {
                        "type": "boolean",
                        "label": "Увімкнути habits tracking",
                        "description": "Відстежувати звички користувача",
                        "default": True
                    },
                    "feedback_enabled": {
                        "type": "boolean",
                        "label": "Увімкнути feedback",
                        "description": "Збирати зворотній зв'язок",
                        "default": True
                    }
                }
            },
            "system": {
                "label": "Системні налаштування",
                "settings": {
                    "log_level": {
                        "type": "select",
                        "label": "Рівень логування",
                        "description": "Рівень деталізації логів",
                        "default": "INFO",
                        "options": ["DEBUG", "INFO", "WARNING", "ERROR"]
                    },
                    "asr_language": {
                        "type": "select",
                        "label": "Мова розпізнавання",
                        "description": "Мова для ASR (Whisper)",
                        "default": "uk",
                        "options": ["uk", "en", "ru"]
                    }
                }
            }
        }
    }


@router.get("/settings")
async def get_settings():
    """Отримати поточні налаштування"""
    import config
    import json
    from pathlib import Path

    # Базові налаштування з config
    base_settings = {
        "ollama_host": config.OLLAMA_HOST,
        "log_level": config.LOG_LEVEL,
        "asr_model_size": getattr(config, "ASR_MODEL_SIZE", "base"),
        "asr_language": getattr(config, "ASR_LANGUAGE", "uk"),
        "db_path": config.DB_PATH
    }

    # Додаткові налаштування з JSON файлу
    settings_file = Path("data/settings.json")
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
                base_settings.update(saved_settings)
        except Exception as e:
            logger.warning(f"Could not read settings file: {e}")

    return base_settings


@router.post("/settings")
async def update_settings(update: SettingsUpdate):
    """Оновити налаштування (runtime)"""
    import json
    from pathlib import Path

    settings_file = Path("data/settings.json")
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    # Читаємо існуючі налаштування
    settings = {}
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except Exception as e:
            logger.warning(f"Could not read settings: {e}")

    # Оновлюємо значення
    settings[update.key] = update.value

    # Зберігаємо
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        logger.info(f"Settings updated: {update.key} = {update.value}")
        return {"ok": True, "message": f"Налаштування {update.key} оновлено та збережено"}
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return {"ok": False, "error": f"Помилка збереження: {e}"}


@router.get("/logs")
async def get_recent_logs(lines: int = 100, level: Optional[str] = None):
    """Отримати останні логи з опціональною фільтрацією по рівню"""
    import os
    from pathlib import Path

    # Шукаємо файл логів
    log_paths = [
        Path("logs/aiva.log"),
        Path("../logs/aiva.log"),
        Path("aiva.log")
    ]

    log_file = None
    for path in log_paths:
        if path.exists():
            log_file = path
            break

    if not log_file:
        # Повертаємо заглушку якщо файл не знайдено
        return {
            "logs": [
                {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": "Log file not found"}
            ]
        }

    try:
        # Читаємо останні N рядків
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        # Парсимо логи (формат: YYYY-MM-DD HH:MM:SS [LEVEL] message)
        logs = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue

            # Спроба розпарсити стандартний формат
            try:
                # Формат: "2026-04-28 14:00:00 [INFO] message"
                # Шукаємо [LEVEL]
                level_start = line.find('[')
                level_end = line.find(']')

                if level_start != -1 and level_end != -1:
                    timestamp = line[:level_start].strip()
                    log_level = line[level_start+1:level_end].strip()
                    message = line[level_end+1:].strip()
                else:
                    timestamp = datetime.now().isoformat()
                    log_level = "INFO"
                    message = line

                # Фільтрація по рівню
                if level and log_level.upper() != level.upper():
                    continue

                logs.append({
                    "timestamp": timestamp,
                    "level": log_level,
                    "message": message
                })
            except Exception:
                # Якщо не вдалося розпарсити, додаємо як є
                if not level:  # Тільки якщо немає фільтру
                    logs.append({
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO",
                        "message": line
                    })

        return {"logs": logs}

    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {
            "logs": [
                {"timestamp": datetime.now().isoformat(), "level": "ERROR", "message": f"Error reading logs: {e}"}
            ]
        }


class CommandRequest(BaseModel):
    command: str

@router.post("/command")
async def execute_command(request: CommandRequest):
    """Виконати команду через dashboard"""
    command = request.command
    import time
    start = time.time()

    try:
        # Спроба використати повний agent_main
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))

            from agent_main import handle_intent
            result = handle_intent(command, source="web")

            if result:
                response_text = result.get("text", "")
                success = result.get("ok", False)
            else:
                # Fallback на AI brain
                from ai_brain import brain
                response_text = brain.ask(command)
                success = True

        except ImportError as e:
            logger.warning(f"agent_main not available, using AI brain: {e}")
            # Fallback на AI brain
            from ai_brain import brain
            response_text = brain.ask(command)
            success = True

        duration = (time.time() - start) * 1000

        record = CommandRecord(
            id=f"web-{int(time.time() * 1000)}",
            timestamp=datetime.now(),
            command=command,
            response=response_text,
            source="web",
            success=success,
            duration_ms=duration
        )
        history_db.add(record.model_dump())

        return {"ok": True, "result": {"text": response_text, "ok": success}, "duration_ms": duration}
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return {"ok": False, "error": str(e)}
