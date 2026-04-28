"""
API endpoints для веб-dashboard
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger("dashboard_api")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Зберігання історії команд (в пам'яті, можна перенести в БД)
command_history: List[Dict[str, Any]] = []
MAX_HISTORY = 100

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

class SettingsUpdate(BaseModel):
    key: str
    value: Any

class CommandRequest(BaseModel):
    command: str


@router.get("/stats", response_model=SystemStats)
async def get_system_stats():
    """Отримати статистику системи"""
    total = len(command_history)
    successful = sum(1 for cmd in command_history if cmd.get("success", False))
    failed = total - successful

    avg_time = 0.0
    if command_history:
        times = [cmd.get("duration_ms", 0) for cmd in command_history if cmd.get("duration_ms")]
        avg_time = sum(times) / len(times) if times else 0.0

    return SystemStats(
        uptime_seconds=0.0,  # TODO: додати реальний uptime
        total_commands=total,
        successful_commands=successful,
        failed_commands=failed,
        avg_response_time_ms=avg_time,
        active_connections=0  # TODO: додати підрахунок WebSocket з'єднань
    )


@router.get("/history", response_model=List[CommandRecord])
async def get_command_history(limit: int = 50, offset: int = 0):
    """Отримати історію команд"""
    start = max(0, len(command_history) - offset - limit)
    end = len(command_history) - offset

    return [
        CommandRecord(**cmd)
        for cmd in reversed(command_history[start:end])
    ]


@router.post("/history")
async def add_command_record(record: CommandRecord):
    """Додати запис в історію"""
    command_history.append(record.model_dump())

    # Обмежуємо розмір історії
    if len(command_history) > MAX_HISTORY:
        command_history.pop(0)

    return {"ok": True, "id": record.id}


@router.delete("/history")
async def clear_history():
    """Очистити історію команд"""
    command_history.clear()
    return {"ok": True, "message": "Історію очищено"}


@router.get("/settings")
async def get_settings():
    """Отримати поточні налаштування"""
    import config

    return {
        "ollama_host": config.OLLAMA_HOST,
        "log_level": config.LOG_LEVEL,
        "asr_model_size": getattr(config, "ASR_MODEL_SIZE", "base"),
        "asr_language": getattr(config, "ASR_LANGUAGE", "uk"),
        "db_path": config.DB_PATH
    }


@router.post("/settings")
async def update_settings(update: SettingsUpdate):
    """Оновити налаштування (runtime)"""
    # TODO: Реалізувати збереження налаштувань
    logger.info(f"Settings update: {update.key} = {update.value}")
    return {"ok": True, "message": f"Налаштування {update.key} оновлено"}


@router.get("/logs")
async def get_recent_logs(lines: int = 100):
    """Отримати останні логи"""
    # TODO: Реалізувати читання логів з файлу
    return {
        "logs": [
            {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": "System started"},
            {"timestamp": datetime.now().isoformat(), "level": "DEBUG", "message": "Loading models..."}
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
        command_history.append(record.model_dump())

        return {"ok": True, "result": {"text": response_text, "ok": success}, "duration_ms": duration}
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return {"ok": False, "error": str(e)}
