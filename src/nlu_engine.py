"""
NLU Engine - Hybrid система розпізнавання інтенцій
Використовує rule-based для простих команд та LLM для складних
"""
import logging
import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from rapidfuzz import process, fuzz
import requests

logger = logging.getLogger("nlu_engine")

# Імпорт entity extractor та context manager
from entity_extractors import entity_extractor
from context_manager import context_manager

# Карта інтенцій (імпортуємо з agent_main)
INTENT_MAP = {
    "run": ["запусти", "відкрий", "стартуй", "run", "open", "play", "грати"],
    "find": ["знайди", "пошукай", "find", "search"],
    "control_on": ["увімкни", "включи", "засвіти", "on"],
    "control_off": ["вимкни", "виключи", "погаси", "off"],
    "vol_set": ["гучність", "звук", "volume"],
    "vol_up": ["гучніше", "голосніше", "up"],
    "vol_down": ["тихіше", "зменш", "down"],
    "mute": ["без звуку", "мут", "mute"],
    "pc_off": ["вимкни комп'ютер", "вируби пк", "shutdown"],
    "pc_cancel": ["скасувати", "відміни", "стоп", "cancel"],
    "weather_now": ["погода", "температура"],
    "weather_forecast": ["прогноз"],
    "screenshot": ["скріншот", "знімок", "screenshot", "зроби фото", "сфоткай"],
    "describe_screen": ["опиши екран", "що бачиш", "describe screen", "аналізуй екран", "що на екрані"],
    "find_element": ["знайди на екрані", "де знаходиться", "find element", "шукай елемент"],
    "detect_errors": ["є помилки", "перевір помилки", "check errors", "помилки на екрані"],
    "read_text": ["прочитай текст", "що написано", "read text", "ocr", "розпізнай текст"]
}


@dataclass
class IntentResult:
    """Результат NLU аналізу"""
    intent: str                      # Тип інтенції (run, find, control_on, etc.)
    confidence: float                # Впевненість 0.0 - 1.0
    entities: Dict[str, Any]         # Витягнуті сутності {"app": "chrome", "volume": 50}
    raw_text: str                    # Оригінальний текст команди
    method: str                      # Метод класифікації: "rule" | "llm" | "context"
    context: Optional[Dict] = None   # Контекст діалогу

    def to_dict(self) -> Dict[str, Any]:
        """Конвертує в словник"""
        return asdict(self)


class RuleBasedClassifier:
    """Швидка класифікація на основі правил та fuzzy matching"""

    def __init__(self):
        self.intent_map = INTENT_MAP

    def classify(self, text: str) -> IntentResult:
        """
        Класифікує команду використовуючи правила

        Args:
            text: Текст команди

        Returns:
            IntentResult з інтенцією та confidence
        """
        text_lower = text.lower().strip()
        words = text_lower.split()

        best_score = 0
        best_intent = None
        best_word_idx = 0

        # Перевіряємо перші 3 слова
        for i, word in enumerate(words[:3]):
            # Порівнюємо з усіма можливими інтенціями
            for intent_name, keywords in self.intent_map.items():
                match = process.extractOne(word, keywords, scorer=fuzz.QRatio)
                if match:
                    _, score, _ = match
                    if score > 75 and score > best_score:
                        best_score = score
                        best_intent = intent_name
                        best_word_idx = i

        # Конвертуємо fuzzy score (0-100) в confidence (0.0-1.0)
        confidence = best_score / 100.0 if best_score > 0 else 0.0

        # Якщо не знайшли інтенцію
        if best_intent is None:
            return IntentResult(
                intent="unknown",
                confidence=0.0,
                entities={},
                raw_text=text,
                method="rule"
            )

        logger.debug(f"Rule-based: intent={best_intent}, score={best_score}, confidence={confidence:.2f}")

        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            entities={},
            raw_text=text,
            method="rule"
        )


class LLMClassifier:
    """Класифікація складних команд через Ollama LLM"""

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self.url = f"{ollama_host}/api/chat"
        self.model = "llama3.2"

        # Connection pooling
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        # Список доступних інтенцій для промпту
        self.available_intents = list(INTENT_MAP.keys())

    def classify(self, text: str, context: Optional[Dict] = None) -> IntentResult:
        """
        Класифікує команду використовуючи LLM

        Args:
            text: Текст команди
            context: Контекст діалогу (опціонально)

        Returns:
            IntentResult з інтенцією, confidence та entities
        """
        # Формуємо промпт для LLM
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(text, context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Низька температура для більш детермінованих результатів
                "num_ctx": 2048
            }
        }

        try:
            start_time = time.time()
            response = self.session.post(self.url, json=payload, timeout=30)
            duration = (time.time() - start_time) * 1000

            if response.status_code == 200:
                answer = response.json().get("message", {}).get("content", "")
                logger.debug(f"LLM response ({duration:.0f}ms): {answer}")

                # Парсимо JSON відповідь
                result = self._parse_llm_response(answer, text)
                return result
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                # Fallback на unknown
                return self._fallback_result(text)

        except requests.RequestException as e:
            logger.error(f"LLM connection failed: {e}")
            return self._fallback_result(text)
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return self._fallback_result(text)

    def _build_system_prompt(self) -> str:
        """Створює system prompt для LLM"""
        intents_list = ", ".join(self.available_intents)

        return f"""Ти - NLU система для голосового асистента AIVA.
Твоя задача - проаналізувати команду користувача та визначити інтенцію.

Доступні інтенції: {intents_list}

Поверни результат ТІЛЬКИ у форматі JSON (без додаткового тексту):
{{
  "intent": "назва_інтенції",
  "confidence": 0.0-1.0,
  "entities": {{"ключ": "значення"}}
}}

Правила:
- intent: одна з доступних інтенцій або "unknown"
- confidence: твоя впевненість у класифікації (0.0 = невпевнений, 1.0 = дуже впевнений)
- entities: витягнуті параметри (назва програми, число, місто, тощо)

Приклади:
Команда: "запусти chrome"
{{"intent": "run", "confidence": 0.95, "entities": {{"app": "chrome"}}}}

Команда: "гучність 50"
{{"intent": "vol_set", "confidence": 0.9, "entities": {{"volume": 50}}}}

Команда: "погода у києві"
{{"intent": "weather_now", "confidence": 0.85, "entities": {{"city": "Київ"}}}}
"""

    def _build_user_prompt(self, text: str, context: Optional[Dict] = None) -> str:
        """Створює user prompt з командою та контекстом"""
        prompt = f'Команда: "{text}"'

        if context:
            prompt += f'\nКонтекст: {json.dumps(context, ensure_ascii=False)}'

        return prompt

    def _parse_llm_response(self, response: str, original_text: str) -> IntentResult:
        """
        Парсить JSON відповідь від LLM

        Args:
            response: Відповідь від LLM
            original_text: Оригінальний текст команди

        Returns:
            IntentResult
        """
        try:
            # Витягуємо JSON з відповіді (може бути обгорнутий в markdown)
            json_match = response
            if "```json" in response:
                json_match = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_match = response.split("```")[1].split("```")[0].strip()

            # Парсимо JSON
            data = json.loads(json_match)

            intent = data.get("intent", "unknown")
            confidence = float(data.get("confidence", 0.5))
            entities = data.get("entities", {})

            # Валідація
            if intent not in self.available_intents and intent != "unknown":
                logger.warning(f"LLM returned invalid intent: {intent}, using 'unknown'")
                intent = "unknown"
                confidence = 0.3

            return IntentResult(
                intent=intent,
                confidence=confidence,
                entities=entities,
                raw_text=original_text,
                method="llm"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}, response: {response}")
            return self._fallback_result(original_text)
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return self._fallback_result(original_text)

    def _fallback_result(self, text: str) -> IntentResult:
        """Fallback результат при помилці"""
        return IntentResult(
            intent="unknown",
            confidence=0.0,
            entities={},
            raw_text=text,
            method="llm"
        )


class NLUEngine:
    """Головний NLU engine з Hybrid логікою"""

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.rule_classifier = RuleBasedClassifier()
        self.llm_classifier = LLMClassifier(ollama_host)
        self.entity_extractor = entity_extractor

        # Статистика використання
        self.stats = {
            "total": 0,
            "rule": 0,
            "llm": 0,
            "context": 0,
            "avg_rule_time_ms": 0.0,
            "avg_llm_time_ms": 0.0
        }

    def analyze(self, text: str, context: Optional[Dict] = None, session_id: str = "default") -> IntentResult:
        """
        Аналізує команду та повертає інтенцію з entities

        Args:
            text: Текст команди
            context: Контекст діалогу (опціонально, deprecated - використовуйте session_id)
            session_id: ID сесії для отримання контексту з БД

        Returns:
            IntentResult з повною інформацією
        """
        if not text or not text.strip():
            return IntentResult(
                intent="unknown",
                confidence=0.0,
                entities={},
                raw_text=text,
                method="rule"
            )

        start_time = time.time()

        # Отримуємо контекст з context manager
        nlu_context = context_manager.get_nlu_context(session_id)

        # Об'єднуємо з переданим контекстом (для зворотної сумісності)
        if context:
            nlu_context.update(context)

        # 1. Спробуємо вивести intent з контексту
        inferred_intent = context_manager.infer_intent_from_context(session_id, text)
        if inferred_intent:
            logger.info(f"🔗 Using inferred intent from context: {inferred_intent}")
            result = IntentResult(
                intent=inferred_intent,
                confidence=0.85,  # Висока впевненість для виведеного intent
                entities={},
                raw_text=text,
                method="context",
                context=nlu_context
            )
            # Витягуємо entities
            extracted_entities = self.entity_extractor.extract(text, result.intent)
            result.entities.update(extracted_entities)

            # Розв'язуємо entities з контексту
            self._resolve_entities_from_context(result, session_id)

            # Оновлюємо статистику
            self.stats["context"] += 1
            self.stats["total"] += 1

            duration = (time.time() - start_time) * 1000
            self._log_result(result, duration)
            return result

        # 2. Визначаємо чи проста команда
        is_simple = self._is_simple_command(text)

        # 3. Класифікуємо
        if is_simple:
            result = self._classify_with_rules(text)
            self.stats["rule"] += 1
        else:
            result = self._classify_with_llm(text, nlu_context)
            self.stats["llm"] += 1

        # 4. Витягуємо entities (якщо LLM не витягнув)
        if result.method == "rule" or not result.entities:
            extracted_entities = self.entity_extractor.extract(text, result.intent)
            result.entities.update(extracted_entities)

        # 5. Розв'язуємо entities з контексту
        self._resolve_entities_from_context(result, session_id)

        # 6. Додаємо контекст
        result.context = nlu_context

        # 7. Оновлюємо статистику
        duration = (time.time() - start_time) * 1000
        self.stats["total"] += 1
        if result.method == "rule":
            self.stats["avg_rule_time_ms"] = (
                (self.stats["avg_rule_time_ms"] * (self.stats["rule"] - 1) + duration) / self.stats["rule"]
            )
        else:
            self.stats["avg_llm_time_ms"] = (
                (self.stats["avg_llm_time_ms"] * (self.stats["llm"] - 1) + duration) / self.stats["llm"]
            )

        self._log_result(result, duration)

        return result

    def _resolve_entities_from_context(self, result: IntentResult, session_id: str) -> None:
        """Розв'язує відсутні entities з контексту"""
        # Список entities які можна розв'язати з контексту
        resolvable_entities = ["app", "city", "device", "volume"]

        for entity_type in resolvable_entities:
            if entity_type not in result.entities or result.entities[entity_type] is None:
                resolved = context_manager.resolve_entity(session_id, entity_type, result.entities)
                if resolved:
                    result.entities[entity_type] = resolved
                    logger.info(f"✨ Resolved '{entity_type}' from context: {resolved}")

    def _log_result(self, result: IntentResult, duration: float) -> None:
        """Логує результат аналізу"""
        logger.info(
            f"🔍 NLU: intent={result.intent}, confidence={result.confidence:.2f}, "
            f"method={result.method}, entities={result.entities}, time={duration:.0f}ms"
        )

    def _is_simple_command(self, text: str) -> bool:
        """
        Визначає чи команда проста (для rule-based) чи складна (для LLM)

        Евристика:
        - Проста: 2-5 слів + є ключові слова з INTENT_MAP
        - Складна: >7 слів або немає ключових слів
        """
        words = text.lower().split()
        word_count = len(words)

        # Якщо дуже довга команда - точно складна
        if word_count > 7:
            return False

        # Якщо дуже коротка - проста
        if word_count <= 2:
            return True

        # Перевіряємо чи є ключові слова в перших 2 словах
        for word in words[:2]:
            for keywords in INTENT_MAP.values():
                # Використовуємо високий поріг для точності
                if any(fuzz.ratio(word, kw) > 85 for kw in keywords):
                    # Додаткова перевірка: якщо команда містить складні конструкції
                    # (той/та/те, який/яка/яке, вчора, завтра тощо)
                    complex_markers = ["який", "яка", "яке", "той", "та", "те", "вчора", "завтра", "ввечері", "вранці"]
                    if any(marker in text.lower() for marker in complex_markers):
                        return False
                    return True

        # Якщо не знайшли ключових слів - складна команда
        return False

    def _classify_with_rules(self, text: str) -> IntentResult:
        """Класифікація через правила"""
        return self.rule_classifier.classify(text)

    def _classify_with_llm(self, text: str, context: Optional[Dict] = None) -> IntentResult:
        """Класифікація через LLM"""
        return self.llm_classifier.classify(text, context)

    def get_stats(self) -> Dict[str, Any]:
        """Повертає статистику використання"""
        total = self.stats["total"]
        return {
            **self.stats,
            "rule_percentage": (self.stats["rule"] / total * 100) if total > 0 else 0,
            "llm_percentage": (self.stats["llm"] / total * 100) if total > 0 else 0,
            "context_percentage": (self.stats["context"] / total * 100) if total > 0 else 0
        }


# Глобальний екземпляр для використання в інших модулях
nlu_engine = NLUEngine()
