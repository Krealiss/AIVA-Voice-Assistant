import logging
import datetime
import requests
import json
import hashlib
from typing import Optional, Dict, Any, List
from functools import lru_cache
try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None
import config
import locale
from utils import retry, ErrorHandler
from context_manager import context_manager, Message

logger = logging.getLogger("ai_brain")

# Налаштування локалі (залишаємо як є, це гарне рішення)
try:
    locale.setlocale(locale.LC_TIME, 'uk_UA.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'uk_UA')
    except:
        pass

class AIBrain:

    def __init__(self) -> None:
        self.host = config.OLLAMA_HOST
        self.url = f"{self.host}/api/chat"
        self.model = "llama3.2"

        self.history = []
        self.max_history = 15
        self.ddgs = DDGS() if DDGS else None

        # Connection pooling для Ollama
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        # Кеш для повторюваних запитів (LRU cache на 100 елементів)
        self._response_cache = {}
        self._cache_max_size = 100

        self.system_prompt = (
            "Ти — AIVA, просунутий асистент на базі ШІ. Твій розробник — студент 4-го курсу Computer Science. "
            "Ти допомагаєш із розробкою, написанням коду на Python та навчанням. "
            "Твоя мета — бути точною, лаконічною та професійною. "
            "Стиль спілкування: дружній, але технічно грамотний. "
            "Якщо питання стосується коду — давай приклад. "
            "Якщо тобі надали [Дані з Інтернету], використовуй їх для актуалізації знань. "
            "Пам'ятай: ти працюєш локально на ПК."
        )

    def _get_cache_key(self, text: str) -> str:
        """Генерує ключ кешу для запиту"""
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Отримує відповідь з кешу, якщо вона є"""
        if key in self._response_cache:
            cached_data = self._response_cache[key]
            # Перевіряємо, чи не застаріла відповідь (5 хвилин)
            if (datetime.datetime.now() - cached_data['timestamp']).seconds < 300:
                logger.info("🎯 Cache hit")
                return cached_data['response']
        return None

    def _save_to_cache(self, key: str, response: str) -> None:
        """Зберігає відповідь у кеш"""
        if len(self._response_cache) >= self._cache_max_size:
            # Видаляємо найстаріший елемент
            oldest_key = min(self._response_cache.keys(),
                           key=lambda k: self._response_cache[k]['timestamp'])
            del self._response_cache[oldest_key]

        self._response_cache[key] = {
            'response': response,
            'timestamp': datetime.datetime.now()
        }

    @lru_cache(maxsize=50)
    def _search_internet(self, query: str) -> str:
        """Покращений пошук з обробкою помилок"""
        if not self.ddgs:
            logger.warning("DuckDuckGo search not available")
            return ""

        try:
            # Розширюємо логіку регіону
            region = 'ua-uk'
            
            logger.info(f"🌍 Searching: {query}")
            
            # Спробуємо спочатку 'lite', він швидший, якщо html блокується
            results = self.ddgs.text(query, region=region, max_results=4, backend="lite")
            
            if not results:
                logger.warning("⚠️ Lite backend failed, trying HTML...")
                results = self.ddgs.text(query, region=region, max_results=4, backend="html")

            if not results:
                return ""
            
            # Додаємо посилання на джерело, щоб AIVA могла сказати "за даними сайту X"
            context = "\n".join([f"• {r['title']} ({r['href']}): {r['body']}" for r in results])
            return context

        except Exception as e:
            logger.error(f"Search error: {e}")
            return ""

    def _should_search(self, text: str) -> bool:
        """Розширена евристика для пошуку"""
        text_lower = text.lower()
        
        # Слова-маркери, які вимагають свіжих даних
        info_triggers = [
            "хто", "де", "коли", "яка", "скільки", "курс", "погода", "новини", 
            "ціна", "купити", "знайди", "пошукай", "що трапилось", "результат",
            "сьогодні", "зараз"
        ]
        
        # Слова, які часто стосуються коду (гуглити не завжди треба, LLM знає Python)
        code_triggers = ["def ", "class ", "import ", "print(", "як написати", "помилка", "error"]
        
        # Якщо це питання по коду — гуглимо тільки якщо прямо просять ("знайди бібліотеку")
        if any(c in text_lower for c in code_triggers) and "знайди" not in text_lower:
            return False

        return any(t in text_lower for t in info_triggers)

    @retry(max_attempts=3, delay=1.0, exceptions=(requests.RequestException,))
    def ask(self, user_text: str, user_id: str = "default", session_id: Optional[str] = None) -> str:
        if not user_text: return ""

        # Перевірка кешу для простих запитів
        cache_key = self._get_cache_key(user_text)
        cached_response = self._get_from_cache(cache_key)
        if cached_response:
            return cached_response

        now_dt = datetime.datetime.now()
        time_str = now_dt.strftime("%H:%M")
        date_str = now_dt.strftime("%d %B %Y")

        # --- HARD RULES (Швидкі відповіді) ---
        user_lower = user_text.lower().strip()

        if user_lower in ['котра година', 'час', 'яка година']:
             return f"Зараз {time_str}."

        if user_lower in ['яка дата', 'яке число', 'сьогодні']:
            return f"Сьогодні {date_str}."

        # --- ПОШУК ---
        internet_context = ""
        if self._should_search(user_text):
            search_data = self._search_internet(user_text)
            if search_data:
                internet_context = f"\n\n[Дані з Інтернету (пріоритет!)]:\n{search_data}\n"

        # --- ОТРИМАННЯ КОНТЕКСТУ З СЕСІЇ ---
        session = context_manager.get_active_session(user_id) if not session_id else context_manager.get_session(session_id)
        if not session:
            session = context_manager.create_session(user_id)

        # Отримуємо історію розмов з контекст-менеджера
        context_history = context_manager.get_context_window(session.session_id)

        # --- ФОРМУВАННЯ КОНТЕКСТУ ---
        current_system_prompt = (
            f"{self.system_prompt}\n"
            f"Поточний контекст часу: {time_str}, {date_str}."
        )

        messages = [{"role": "system", "content": current_system_prompt}]

        # Додаємо історію з контекст-менеджера
        for msg in context_history:
            messages.append({"role": msg.role, "content": msg.content})

        # Додаємо поточне повідомлення
        messages.append({"role": "user", "content": f"{user_text}{internet_context}"})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_ctx": 4096
            }
        }

        try:
            # Використовуємо session замість requests.post
            r = self.session.post(self.url, json=payload, timeout=60)
            if r.status_code == 200:
                answer = r.json().get("message", {}).get("content", "")

                # Зберігаємо в контекст-менеджер
                context_manager.add_message(session.session_id, "user", user_text)
                context_manager.add_message(session.session_id, "assistant", answer)

                # Зберігаємо в старий history для backward compatibility
                self.history.append({"role": "user", "content": user_text})
                self.history.append({"role": "assistant", "content": answer})

                # Очищення історії
                if len(self.history) > self.max_history * 2:
                    self.history = self.history[-(self.max_history*2):]

                # Зберігаємо в кеш
                self._save_to_cache(cache_key, answer)

                return answer
            else:
                logger.error(f"Ollama Error: {r.status_code} - {r.text}")
                return ErrorHandler.handle_api_error(
                    Exception(f"Status {r.status_code}"), "Ollama"
                )
        except requests.RequestException as e:
            logger.error(f"Brain connection failed: {e}")
            return ErrorHandler.handle_api_error(e, "Ollama")
brain = AIBrain()