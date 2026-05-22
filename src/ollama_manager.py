"""
OllamaManager — авто-запуск і моніторинг Ollama сервісу
"""
import os
import time
import logging
import subprocess
import requests
from typing import List, Optional

logger = logging.getLogger("ollama_manager")


class OllamaManager:
    """Менеджер Ollama: запуск, перевірка моделей, health check"""

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self._process: Optional[subprocess.Popen] = None

    def is_running(self, timeout: float = 2.0) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def start(self, wait_seconds: int = 12) -> bool:
        """Запускає `ollama serve` якщо не запущено. Повертає True якщо успішно."""
        if self.is_running():
            return True

        logger.info("Ollama не запущено — спроба запуску...")
        try:
            kwargs = {}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self._process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **kwargs,
            )
        except FileNotFoundError:
            logger.error("Ollama не знайдено у PATH. Встанови: https://ollama.ai")
            return False
        except Exception as e:
            logger.error(f"Не вдалося запустити Ollama: {e}")
            return False

        for _ in range(wait_seconds):
            time.sleep(1)
            if self.is_running(timeout=1.0):
                logger.info("✅ Ollama запущено успішно")
                return True

        logger.error("Ollama запущено, але не відповідає")
        return False

    def ensure_running(self) -> bool:
        """Перевіряє чи Ollama запущено, запускає якщо ні."""
        if self.is_running():
            return True
        return self.start()

    def get_available_models(self) -> List[str]:
        """Повертає список завантажених моделей."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=3)
            if r.status_code == 200:
                return [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            pass
        return []

    def is_model_available(self, model: str) -> bool:
        """Перевіряє чи модель завантажена локально."""
        base_name = model.split(":")[0]
        return any(m.startswith(base_name) for m in self.get_available_models())

    def best_available_model(self, preferred: str) -> Optional[str]:
        """
        Повертає найкращу доступну модель.
        Якщо preferred є — повертає її. Інакше повертає першу доступну.
        """
        models = self.get_available_models()
        if not models:
            return None
        base = preferred.split(":")[0]
        for m in models:
            if m.startswith(base):
                return m
        return models[0]


# Глобальний екземпляр
ollama_manager = OllamaManager()
