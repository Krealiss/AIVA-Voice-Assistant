"""
Vision Module - система розуміння екрану
Screenshot capture, OCR, UI element detection, Ollama LLaVA integration
"""
import logging
import os
import base64
import io
import json
import requests
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import tempfile

logger = logging.getLogger("vision")

# Screenshot capture
try:
    from PIL import ImageGrab, Image
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False
    logger.warning("PIL not available - screenshot features disabled")

# OCR
try:
    import pytesseract
    OCR_AVAILABLE = True

    # Налаштування Tesseract PATH для Windows
    if os.name == 'nt':  # Windows
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe"
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"Tesseract found at: {path}")
                break
        else:
            logger.warning("Tesseract executable not found in standard locations")
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract not available - OCR disabled")

class VisionModule:
    """Модуль для аналізу екрану"""

    def __init__(self, screenshots_dir: str = "data/screenshots"):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Cache database
        self.cache_db = Path("data/vision_cache.db")
        self.cache_db.parent.mkdir(parents=True, exist_ok=True)
        self._init_cache_db()

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

    def _init_cache_db(self):
        """Ініціалізація БД для кешування"""
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vision_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    result TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    UNIQUE(image_hash, prompt)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON vision_cache(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hash_prompt ON vision_cache(image_hash, prompt)")
            conn.commit()
        logger.info(f"Vision cache DB initialized: {self.cache_db}")

    def _get_image_hash(self, image_path: str) -> str:
        """Обчислити hash зображення"""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error computing image hash: {e}")
            return ""

    def _get_from_cache(self, image_hash: str, prompt: str) -> Optional[str]:
        """Отримати результат з кешу"""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                cur = conn.cursor()
                now = datetime.now().isoformat()

                result = cur.execute("""
                    SELECT result FROM vision_cache
                    WHERE image_hash = ? AND prompt = ? AND expires_at > ?
                """, (image_hash, prompt, now)).fetchone()

                if result:
                    logger.info(f"Cache HIT for {image_hash[:8]}...")
                    return result[0]
                else:
                    logger.debug(f"Cache MISS for {image_hash[:8]}...")
                    return None
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def _save_to_cache(self, image_hash: str, prompt: str, result: str, ttl_seconds: int = 300):
        """Зберегти результат в кеш"""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                now = datetime.now()
                expires = now + timedelta(seconds=ttl_seconds)

                conn.execute("""
                    INSERT OR REPLACE INTO vision_cache
                    (image_hash, prompt, result, model, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (image_hash, prompt, result, self.vision_model, now.isoformat(), expires.isoformat()))

                conn.commit()
                logger.debug(f"Cached result for {image_hash[:8]}... (TTL: {ttl_seconds}s)")
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def _cleanup_expired_cache(self):
        """Видалити застарілі записи з кешу"""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                now = datetime.now().isoformat()
                deleted = conn.execute("DELETE FROM vision_cache WHERE expires_at < ?", (now,))
                conn.commit()
                if deleted.rowcount > 0:
                    logger.info(f"Cleaned up {deleted.rowcount} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

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
            # Спроба використати pygetwindow для Windows
            try:
                import pygetwindow as gw

                if window_title:
                    # Шукаємо вікно за назвою
                    windows = gw.getWindowsWithTitle(window_title)
                    if windows:
                        window = windows[0]
                        # Активуємо вікно
                        window.activate()
                        import time
                        time.sleep(0.1)  # Даємо час на активацію

                        # Захоплюємо область вікна
                        bbox = (window.left, window.top, window.right, window.bottom)
                        screenshot = ImageGrab.grab(bbox=bbox)

                        # Зберігаємо
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"window_{window_title[:20]}_{timestamp}.png"
                        filepath = self.screenshots_dir / filename
                        screenshot.save(filepath)

                        logger.info(f"Window screenshot saved: {filepath}")
                        return str(filepath)
                else:
                    # Якщо не вказано назву, захоплюємо активне вікно
                    active_window = gw.getActiveWindow()
                    if active_window:
                        bbox = (active_window.left, active_window.top,
                               active_window.right, active_window.bottom)
                        screenshot = ImageGrab.grab(bbox=bbox)

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"active_window_{timestamp}.png"
                        filepath = self.screenshots_dir / filename
                        screenshot.save(filepath)

                        logger.info(f"Active window screenshot saved: {filepath}")
                        return str(filepath)

            except ImportError:
                logger.warning("pygetwindow not available, falling back to full screen")
                # Fallback на повний екран
                return self.capture_screenshot()

        except Exception as e:
            logger.error(f"Window capture failed: {e}")
            # Fallback на повний екран
            return self.capture_screenshot()

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

    def _compress_image(self, image_path: str, max_size: Tuple[int, int] = (800, 600), quality: int = 60) -> str:
        """Стиснути зображення для швидшого аналізу (оптимізовано для швидкості)"""
        if not SCREENSHOT_AVAILABLE:
            return image_path

        try:
            img = Image.open(image_path)

            # Resize якщо більше max_size
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                logger.debug(f"Resized image from original to {img.size}")

            # Конвертувати в JPEG
            compressed_path = image_path.replace('.png', '_compressed.jpg')
            img.convert('RGB').save(compressed_path, format='JPEG', quality=quality, optimize=True)

            # Порівняння розмірів
            original_size = os.path.getsize(image_path)
            compressed_size = os.path.getsize(compressed_path)
            savings = (1 - compressed_size / original_size) * 100

            logger.info(f"Compressed: {original_size/1024:.1f}KB -> {compressed_size/1024:.1f}KB (saved {savings:.1f}%)")

            return compressed_path

        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            return image_path

    def _is_english(self, text: str) -> bool:
        """Перевірити чи текст англійською (проста евристика)"""
        if not text:
            return False
        # Підраховуємо латинські літери
        latin_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        cyrillic_chars = sum(1 for c in text if 'Ѐ' <= c <= 'ӿ')
        total_chars = latin_chars + cyrillic_chars
        if total_chars == 0:
            return False
        # Якщо більше 70% латиниці - вважаємо англійською
        return (latin_chars / total_chars) > 0.7

    def _translate_to_ukrainian(self, text: str) -> str:
        """Перекласти текст на українську через Ollama"""
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": "llama3.2:latest",
                    "prompt": f"Переклади цей текст на українську мову. Відповідай ТІЛЬКИ перекладом, без додаткових коментарів:\n\n{text}",
                    "stream": False
                },
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                translated = result.get("response", "").strip()
                logger.info(f"Translated to Ukrainian: {translated[:100]}...")
                return translated
            else:
                logger.warning(f"Translation failed: {response.status_code}")
                return text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    def analyze_with_vision_api(self, image_path: str, prompt: str = "Що на цьому зображенні?", stream: bool = False, callback=None) -> Optional[str]:
        """Аналіз зображення через Ollama LLaVA з кешуванням та стисненням"""
        if not self.vision_available:
            logger.error("Vision API not available")
            return None

        try:
            # 1. Обчислюємо hash оригінального зображення
            image_hash = self._get_image_hash(image_path)
            if not image_hash:
                logger.warning("Could not compute image hash, skipping cache")
            else:
                # 2. Перевіряємо кеш
                cached_result = self._get_from_cache(image_hash, prompt)
                if cached_result:
                    return cached_result

            # 3. Стискаємо зображення
            compressed_path = self._compress_image(image_path)

            # 4. Читаємо стиснене зображення та конвертуємо в base64
            with open(compressed_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # 5. Запит до Ollama з retry logic
            max_retries = 1  # Тільки 1 спроба для швидкості
            timeout = 120  # 2 хвилини timeout

            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.ollama_host}/api/generate",
                        json={
                            "model": self.vision_model,
                            "prompt": prompt,
                            "images": [image_data],
                            "stream": stream
                        },
                        timeout=timeout,
                        stream=stream
                    )

                    if response.status_code == 200:
                        if stream:
                            # Streaming mode - збираємо відповідь по частинах
                            full_response = ""
                            for line in response.iter_lines():
                                if line:
                                    try:
                                        chunk = json.loads(line)
                                        token = chunk.get("response", "")
                                        full_response += token

                                        # Викликаємо callback для кожного токену
                                        if callback:
                                            callback(token)

                                        # Перевіряємо чи це останній chunk
                                        if chunk.get("done", False):
                                            break
                                    except json.JSONDecodeError:
                                        continue

                            answer = full_response
                        else:
                            # Non-streaming mode
                            result = response.json()
                            answer = result.get("response", "")

                        logger.info(f"Vision API response: {answer[:100]}...")

                        # 6. Переклад на українську (якщо відповідь англійською)
                        if answer and self._is_english(answer):
                            logger.info("Translating response to Ukrainian...")
                            answer = self._translate_to_ukrainian(answer)

                        # 7. Зберігаємо в кеш
                        if image_hash:
                            self._save_to_cache(image_hash, prompt, answer, ttl_seconds=300)

                        # 8. Видаляємо стиснений файл якщо він тимчасовий
                        if compressed_path != image_path and os.path.exists(compressed_path):
                            try:
                                os.remove(compressed_path)
                            except:
                                pass

                        return answer
                    else:
                        logger.error(f"Vision API error: {response.status_code}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                            continue
                        return None

                except requests.Timeout:
                    logger.warning(f"Vision API timeout (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        continue
                    # Fallback на OCR
                    logger.info("Falling back to OCR")
                    if OCR_AVAILABLE:
                        return self.extract_text_ocr(image_path)
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
                "ВАЖЛИВО: Відповідай ТІЛЬКИ українською мовою!\n\n"
                "Опиши що на цьому скріншоті. "
                "Які програми відкриті? Що робить користувач? "
                "Чи є якісь помилки або важлива інформація?\n\n"
                "Відповідь має бути українською мовою."
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
            f"ВАЖЛИВО: Відповідай ТІЛЬКИ українською мовою!\n\n"
            f"Знайди на екрані: {element_description}\n"
            f"Опиши де він знаходиться (координати, позиція відносно інших елементів).\n"
            f"Чи можна на нього клікнути? Який текст на ньому?\n\n"
            f"Відповідь має бути українською мовою."
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
            "ВАЖЛИВО: Відповідай ТІЛЬКИ українською мовою!\n\n"
            "Чи є на екрані якісь помилки, попередження або проблеми?\n"
            "Шукай: червоні повідомлення, діалоги помилок, warning icons, "
            "crashed programs, frozen UI.\n"
            "Якщо знайдеш - опиши детально.\n\n"
            "Відповідь має бути українською мовою."
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
