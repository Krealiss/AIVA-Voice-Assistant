"""
Vision Module - система розуміння екрану
Screenshot capture, OCR, UI element detection, Ollama LLaVA integration
"""
import logging
import os
import base64
import io
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import tempfile

# Screenshot capture
try:
    from PIL import ImageGrab, Image
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False
    logging.warning("PIL not available - screenshot features disabled")

# OCR
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("pytesseract not available - OCR disabled")

logger = logging.getLogger("vision")

class VisionModule:
    """Модуль для аналізу екрану"""

    def __init__(self, screenshots_dir: str = "data/screenshots"):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Ollama settings
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.vision_model = "llava"

        # Check if Ollama is available
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            self.vision_available = response.status_code == 200
            if self.vision_available:
                logger.info(f"Vision API initialized (Ollama LLaVA at {self.ollama_host})")
            else:
                logger.warning("Ollama not responding")
                self.vision_available = False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self.vision_available = False

    def capture_screenshot(self, save: bool = True) -> Optional[str]:
        """Зробити скріншот екрану"""
        if not SCREENSHOT_AVAILABLE:
            logger.error("Screenshot capture not available (PIL not installed)")
            return None

        try:
            # Захоплюємо екран
            screenshot = ImageGrab.grab()

            if save:
                # Зберігаємо
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                filepath = self.screenshots_dir / filename

                screenshot.save(filepath)
                logger.info(f"Screenshot saved: {filepath}")
                return str(filepath)
            else:
                # Повертаємо як bytes
                buffer = io.BytesIO()
                screenshot.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue()).decode()

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    def capture_window(self, window_title: Optional[str] = None) -> Optional[str]:
        """Зробити скріншот конкретного вікна"""
        if not SCREENSHOT_AVAILABLE:
            return None

        try:
            # TODO: Implement window-specific capture
            # For now, just capture full screen
            return self.capture_screenshot()
        except Exception as e:
            logger.error(f"Window capture failed: {e}")
            return None

    def extract_text_ocr(self, image_path: str) -> str:
        """Витягнути текст з зображення через OCR"""
        if not OCR_AVAILABLE:
            logger.error("OCR not available (pytesseract not installed)")
            return ""

        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='ukr+eng')
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    def analyze_with_vision_api(self, image_path: str, prompt: str = "Що на цьому зображенні?") -> Optional[str]:
        """Аналіз зображення через Ollama LLaVA"""
        if not self.vision_available:
            logger.error("Vision API not available")
            return None

        try:
            # Читаємо зображення та конвертуємо в base64
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Запит до Ollama
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=120  # 2 minutes for vision analysis
            )

            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "")
                logger.info(f"Vision API response: {answer[:100]}...")
                return answer
            else:
                logger.error(f"Vision API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Vision API failed: {e}")
            return None

    def describe_screen(self, prompt: Optional[str] = None) -> Dict:
        """Описати поточний екран"""
        # Робимо скріншот
        screenshot_path = self.capture_screenshot(save=True)

        if not screenshot_path:
            return {"ok": False, "error": "Failed to capture screenshot"}

        result = {
            "ok": True,
            "screenshot": screenshot_path,
            "timestamp": datetime.now().isoformat()
        }

        # OCR
        if OCR_AVAILABLE:
            text = self.extract_text_ocr(screenshot_path)
            result["ocr_text"] = text
            result["has_text"] = len(text) > 0

        # Vision API
        if self.vision_available:
            default_prompt = (
                "Опиши що на цьому скріншоті. "
                "Які програми відкриті? Що робить користувач? "
                "Чи є якісь помилки або важлива інформація?"
            )
            description = self.analyze_with_vision_api(
                screenshot_path,
                prompt or default_prompt
            )
            result["description"] = description

        return result

    def find_ui_element(self, element_description: str) -> Dict:
        """Знайти UI елемент на екрані"""
        screenshot_path = self.capture_screenshot(save=True)

        if not screenshot_path or not self.vision_available:
            return {"ok": False, "error": "Vision API not available"}

        prompt = (
            f"Знайди на екрані: {element_description}\n"
            f"Опиши де він знаходиться (координати, позиція відносно інших елементів).\n"
            f"Чи можна на нього клікнути? Який текст на ньому?"
        )

        description = self.analyze_with_vision_api(screenshot_path, prompt)

        if not description:
            return {"ok": False, "error": "Vision analysis failed"}

        return {
            "ok": True,
            "screenshot": screenshot_path,
            "element": element_description,
            "found": description
        }

    def detect_errors(self) -> Dict:
        """Виявити помилки на екрані"""
        screenshot_path = self.capture_screenshot(save=True)

        if not screenshot_path or not self.vision_available:
            return {"ok": False, "error": "Vision API not available"}

        prompt = (
            "Чи є на екрані якісь помилки, попередження або проблеми?\n"
            "Шукай: червоні повідомлення, діалоги помилок, warning icons, "
            "crashed programs, frozen UI.\n"
            "Якщо знайдеш - опиши детально."
        )

        analysis = self.analyze_with_vision_api(screenshot_path, prompt)

        if not analysis:
            return {"ok": False, "error": "Vision analysis failed"}

        return {
            "ok": True,
            "screenshot": screenshot_path,
            "analysis": analysis,
            "has_errors": "помилк" in analysis.lower() or "error" in analysis.lower()
        }

    def compare_screenshots(self, path1: str, path2: str) -> Dict:
        """Порівняти два скріншоти"""
        if not self.vision_available:
            return {"ok": False, "error": "Vision API not available"}

        # Аналізуємо обидва
        desc1 = self.analyze_with_vision_api(path1, "Опиши що на цьому зображенні")
        desc2 = self.analyze_with_vision_api(path2, "Опиши що на цьому зображенні")

        # Порівнюємо через текстовий запит
        prompt = (
            f"Порівняй два описи екранів:\n\n"
            f"Екран 1: {desc1}\n\n"
            f"Екран 2: {desc2}\n\n"
            f"Що змінилося? Які відмінності?"
        )

        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            comparison = response.json().get("response", "Comparison failed")
        except Exception as e:
            comparison = f"Comparison failed: {e}"

        return {
            "ok": True,
            "screenshot1": path1,
            "screenshot2": path2,
            "description1": desc1,
            "description2": desc2,
            "comparison": comparison
        }

    def read_screen_text(self) -> str:
        """Прочитати весь текст з екрану"""
        screenshot_path = self.capture_screenshot(save=True)

        if not screenshot_path:
            return ""

        # Спочатку OCR
        if OCR_AVAILABLE:
            text = self.extract_text_ocr(screenshot_path)
            if text:
                return text

        # Fallback на Vision API
        if self.vision_available:
            result = self.analyze_with_vision_api(
                screenshot_path,
                "Витягни весь текст з цього зображення. Тільки текст, без опису."
            )
            return result or ""

        return ""

    def get_active_window_info(self) -> Dict:
        """Отримати інформацію про активне вікно"""
        screenshot_path = self.capture_screenshot(save=True)

        if not screenshot_path or not self.vision_available:
            return {"ok": False}

        prompt = (
            "Яка програма зараз активна (у фокусі)?\n"
            "Назва програми, що користувач робить, який файл відкритий?"
        )

        info = self.analyze_with_vision_api(screenshot_path, prompt)

        return {
            "ok": True,
            "screenshot": screenshot_path,
            "info": info
        }

    def cleanup_old_screenshots(self, keep_last: int = 50):
        """Видалити старі скріншоти"""
        try:
            screenshots = sorted(
                self.screenshots_dir.glob("screenshot_*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Видаляємо всі крім останніх N
            for screenshot in screenshots[keep_last:]:
                screenshot.unlink()
                logger.info(f"Deleted old screenshot: {screenshot}")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

# Глобальний екземпляр
vision = VisionModule()
