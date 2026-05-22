"""
Entity Extractors - витягування сутностей з тексту команд
Підтримує: числа, назви програм, міста, час, дії
"""
import re
import logging
import inspect
from typing import Dict, Any, Optional, List
from rapidfuzz import process, fuzz

logger = logging.getLogger("entity_extractors")

# --- FIX: Pymorphy2 compatibility for Python 3.10+ ---
if not hasattr(inspect, 'getargspec'):
    def getargspec_stub(func):
        spec = inspect.getfullargspec(func)
        return (spec.args, spec.varargs, spec.varkw, spec.defaults)
    inspect.getargspec = getargspec_stub

# Імпорт pymorphy2 для морфологічного аналізу
try:
    import pymorphy2
    morph = pymorphy2.MorphAnalyzer(lang='uk')
    MORPH_AVAILABLE = True
except ImportError:
    logger.warning("pymorphy2 not available, city extraction will be limited")
    MORPH_AVAILABLE = False


class EntityExtractor:
    """Головний клас для витягування entities з тексту"""

    def __init__(self):
        self.number_extractor = NumberExtractor()
        self.app_extractor = AppNameExtractor()
        self.city_extractor = CityExtractor()
        self.time_extractor = TimeExtractor()
        self.action_extractor = ActionExtractor()
        self.date_extractor = DateExtractor()
        self.range_extractor = RangeExtractor()
        self.multiple_extractor = MultipleItemsExtractor()

    def extract(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Витягує entities залежно від типу інтенції

        Args:
            text: Текст команди
            intent: Тип інтенції (run, vol_set, weather_now, etc.)

        Returns:
            Dict з витягнутими entities
        """
        entities = {}
        text_lower = text.lower()

        # Залежно від інтенції витягуємо різні entities
        if intent == "run":
            # Перевіряємо чи є множинні програми
            multiple_apps = self.multiple_extractor.extract(text, "app")
            if multiple_apps:
                entities["apps"] = multiple_apps
                entities["multiple"] = True
            else:
                app = self.app_extractor.extract(text)
                if app:
                    entities["app"] = app

        elif intent in ["vol_set", "vol_up", "vol_down"]:
            volume = self.number_extractor.extract(text)
            if volume is not None:
                entities["volume"] = volume

        elif intent in ["control_on", "control_off"]:
            # Перевіряємо чи є множинні пристрої
            multiple_devices = self.multiple_extractor.extract(text, "device")
            if multiple_devices:
                entities["devices"] = multiple_devices
                entities["multiple"] = True
            else:
                device = self._extract_device_name(text, intent)
                if device:
                    entities["device"] = device
            entities["action"] = "on" if intent == "control_on" else "off"

        elif intent in ["weather_now", "weather_forecast"]:
            city = self.city_extractor.extract(text)
            if city:
                entities["city"] = city
            entities["when"] = "now" if intent == "weather_now" else "forecast"

            # Витягуємо дату якщо є
            date = self.date_extractor.extract(text)
            if date:
                entities["date"] = date

        elif intent == "find":
            # Для пошуку витягуємо query (все після "знайди"/"пошукай")
            query = self._extract_search_query(text)
            if query:
                entities["query"] = query

        # Загальні entities для всіх інтенцій

        # Час
        time = self.time_extractor.extract(text)
        if time:
            entities["time"] = time

        # Дата
        if "date" not in entities:
            date = self.date_extractor.extract(text)
            if date:
                entities["date"] = date

        # Діапазон
        range_data = self.range_extractor.extract(text)
        if range_data:
            entities["range"] = range_data

        return entities

    def _extract_device_name(self, text: str, intent: str) -> Optional[str]:
        """Витягує назву пристрою для smart home команд"""
        # Видаляємо команду з початку
        keywords = ["увімкни", "включи", "засвіти", "вимкни", "виключи", "погаси", "on", "off"]
        text_lower = text.lower()

        for keyword in keywords:
            if keyword in text_lower:
                # Беремо все після ключового слова
                idx = text_lower.find(keyword)
                device = text[idx + len(keyword):].strip()
                return device if device else None

        return None

    def _extract_search_query(self, text: str) -> Optional[str]:
        """Витягує пошуковий запит"""
        keywords = ["знайди", "пошукай", "find", "search"]
        text_lower = text.lower()

        for keyword in keywords:
            if keyword in text_lower:
                idx = text_lower.find(keyword)
                query = text[idx + len(keyword):].strip()
                return query if query else None

        return None


class NumberExtractor:
    """Витягування чисел з тексту"""

    def extract(self, text: str) -> Optional[int]:
        """
        Витягує перше число з тексту

        Examples:
            "гучність 50" -> 50
            "встанови на 75" -> 75
            "зменш на 10" -> 10
        """
        # Шукаємо числа в тексті
        numbers = re.findall(r'\b\d+\b', text)

        if numbers:
            num = int(numbers[0])
            # Валідація для гучності (0-100)
            if 0 <= num <= 100:
                return num
            # Якщо число більше 100, можливо це помилка
            logger.warning(f"Number {num} out of range for volume")
            return None

        return None


class AppNameExtractor:
    """Витягування назв програм з тексту"""

    def __init__(self):
        # Словник синонімів (імпортуємо з agent_main якщо можливо)
        self.aliases = {
            "google chrome": ["хром", "гугл", "браузер", "chrome"],
            "steam": ["стім", "стим", "valve"],
            "telegram": ["тг", "тєлєгу", "телега"],
            "visual studio code": ["код", "віжуал", "вс код", "студіо", "vscode", "vs code"],
            "counter-strike 2": ["кс", "контра", "кс 2", "кс го", "csgo", "cs 2", "cs2"],
            "dota 2": ["дота", "доту", "dota"],
            "spotify": ["спотіфай", "музика", "спотік"],
            "discord": ["діскорд", "діс", "дс"],
        }

    def extract(self, text: str) -> Optional[str]:
        """
        Витягує назву програми з тексту

        Examples:
            "запусти хром" -> "google chrome"
            "відкрий стім" -> "steam"
            "стартуй vscode" -> "visual studio code"
        """
        text_lower = text.lower()

        # Спочатку шукаємо точні збіги з синонімами
        for canonical_name, aliases in self.aliases.items():
            for alias in aliases:
                # Шукаємо як окреме слово
                pattern = rf'\b{re.escape(alias)}\b'
                if re.search(pattern, text_lower):
                    return canonical_name

        # Якщо не знайшли через синоніми, витягуємо все після команди
        keywords = ["запусти", "відкрий", "стартуй", "run", "open", "play", "грати"]
        for keyword in keywords:
            if keyword in text_lower:
                idx = text_lower.find(keyword)
                app_name = text[idx + len(keyword):].strip()
                if app_name:
                    # Перевіряємо чи це не інша команда
                    if app_name not in keywords:
                        return app_name

        return None


class CityExtractor:
    """Витягування назв міст з тексту"""

    def __init__(self):
        # Список популярних міст України з різними формами
        self.cities_map = {
            "Київ": ["київ", "києві", "києва", "києву", "київом", "киев", "киеве"],
            "Харків": ["харків", "харкові", "харкова", "харкову", "харьков", "харькове"],
            "Одеса": ["одеса", "одесі", "одеси", "одесу", "одессе", "одесса"],
            "Дніпро": ["дніпро", "дніпрі", "дніпра", "днепр", "днепре"],
            "Донецьк": ["донецьк", "донецьку", "донецька", "донецк", "донецке"],
            "Запоріжжя": ["запоріжжя", "запоріжжі", "запорожье", "запорожжя"],
            "Львів": ["львів", "львові", "львова", "львову", "львов", "львове"],
            "Кривий Рог": ["кривий рог", "кривому розі", "кривой рог"],
            "Миколаїв": ["миколаїв", "миколаєві", "николаев", "николаеве"],
            "Маріуполь": ["маріуполь", "маріуполі", "мариуполь", "мариуполе"],
            "Луганськ": ["луганськ", "луганську", "луганск", "луганске"],
            "Вінниця": ["вінниця", "вінниці", "винница", "виннице"],
            "Херсон": ["херсон", "херсоні", "херсона"],
            "Полтава": ["полтава", "полтаві", "полтави"],
            "Чернігів": ["чернігів", "чернігові", "чернигов", "чернигове"],
            "Черкаси": ["черкаси", "черкасах", "черкас"],
            "Суми": ["суми", "сумах", "сум"],
            "Житомир": ["житомир", "житомирі", "житомира"],
            "Хмельницький": ["хмельницький", "хмельницькому", "хмельницкий"],
            "Рівне": ["рівне", "рівному", "ровно"],
            "Чернівці": ["чернівці", "чернівцях", "черновцы"],
            "Тернопіль": ["тернопіль", "тернополі", "тернополь"],
            "Івано-Франківськ": ["івано-франківськ", "івано-франківську", "ивано-франковск"],
            "Луцьк": ["луцьк", "луцьку", "луцк"],
            "Ужгород": ["ужгород", "ужгороді", "ужгорода"]
        }

        # Плоский список для зворотної сумісності
        self.cities = list(self.cities_map.keys())

        # Stop words для фільтрації
        self.stop_words = [
            "погода", "прогноз", "температура", "скажи", "яка", "який",
            "у", "в", "на", "завтра", "сьогодні", "зараз"
        ]

    def extract(self, text: str) -> Optional[str]:
        """
        Витягує назву міста з тексту

        Examples:
            "погода у києві" -> "Київ"
            "яка температура в харкові" -> "Харків"
            "прогноз на львів" -> "Львів"
        """
        text_lower = text.lower()

        # Шукаємо збіги з картою міст (всі форми)
        for city_name, city_forms in self.cities_map.items():
            for form in city_forms:
                if form in text_lower:
                    return city_name

        # Якщо не знайшли через карту, пробуємо морфологічний аналіз
        if MORPH_AVAILABLE:
            words = text_lower.split()
            for word in words:
                # Пропускаємо stop words та короткі слова
                if word in self.stop_words or len(word) < 3:
                    continue

                # Аналізуємо морфологію
                parsed = morph.parse(word)[0]

                # Шукаємо іменники (міста - це іменники)
                if 'NOUN' in parsed.tag:
                    # Нормалізуємо до початкової форми
                    normal_form = parsed.normal_form.capitalize()

                    # Перевіряємо чи схоже на місто зі списку
                    match = process.extractOne(
                        normal_form,
                        self.cities,
                        scorer=fuzz.ratio,
                        score_cutoff=80
                    )

                    if match:
                        return match[0]

        return None


class TimeExtractor:
    """Витягування часу з тексту"""

    def extract(self, text: str) -> Optional[str]:
        """
        Витягує час з тексту

        Examples:
            "о 9 ранку" -> "09:00"
            "в 14:30" -> "14:30"
            "о пів на восьму" -> "07:30"
        """
        text_lower = text.lower()

        # Шукаємо формат HH:MM
        time_pattern = r'\b(\d{1,2}):(\d{2})\b'
        match = re.search(time_pattern, text)
        if match:
            hour, minute = match.groups()
            return f"{int(hour):02d}:{minute}"

        # Шукаємо формат "о X" або "в X"
        hour_pattern = r'\b(?:о|в)\s+(\d{1,2})\b'
        match = re.search(hour_pattern, text_lower)
        if match:
            hour = int(match.group(1))
            # Визначаємо AM/PM
            if "ранку" in text_lower or "вранці" in text_lower:
                pass  # Залишаємо як є
            elif "вечора" in text_lower or "ввечері" in text_lower:
                if hour < 12:
                    hour += 12
            elif "дня" in text_lower or "вдень" in text_lower:
                if hour < 12:
                    hour += 12

            return f"{hour:02d}:00"

        return None


class ActionExtractor:
    """Витягування дій (on/off, start/stop)"""

    def extract(self, text: str) -> Optional[str]:
        """
        Витягує дію з тексту

        Examples:
            "увімкни світло" -> "on"
            "вимкни комп'ютер" -> "off"
        """
        text_lower = text.lower()

        on_keywords = ["увімкни", "включи", "засвіти", "on", "start"]
        off_keywords = ["вимкни", "виключи", "погаси", "off", "stop"]

        for keyword in on_keywords:
            if keyword in text_lower:
                return "on"

        for keyword in off_keywords:
            if keyword in text_lower:
                return "off"

        return None


class DateExtractor:
    """Витягування дат з тексту"""

    def __init__(self):
        from datetime import datetime, timedelta
        self.today = datetime.now().date()

    def extract(self, text: str) -> Optional[str]:
        """
        Витягує дату з тексту

        Examples:
            "завтра" -> "2026-05-02"
            "вчора" -> "2026-04-30"
            "через 3 дні" -> "2026-05-04"
            "15 травня" -> "2026-05-15"
        """
        from datetime import timedelta
        text_lower = text.lower()

        # Відносні дати
        if "сьогодні" in text_lower or "today" in text_lower:
            return self.today.isoformat()

        if "завтра" in text_lower or "tomorrow" in text_lower:
            return (self.today + timedelta(days=1)).isoformat()

        if "вчора" in text_lower or "yesterday" in text_lower:
            return (self.today - timedelta(days=1)).isoformat()

        if "післязавтра" in text_lower:
            return (self.today + timedelta(days=2)).isoformat()

        # "через N днів/тижнів"
        through_pattern = r'через\s+(\d+)\s+(день|дні|днів|тиждень|тижні|тижнів)'
        match = re.search(through_pattern, text_lower)
        if match:
            count = int(match.group(1))
            unit = match.group(2)

            if "день" in unit or "дні" in unit or "днів" in unit:
                return (self.today + timedelta(days=count)).isoformat()
            elif "тиждень" in unit or "тижні" in unit or "тижнів" in unit:
                return (self.today + timedelta(weeks=count)).isoformat()

        # Конкретна дата "15 травня", "1 червня"
        months_map = {
            "січня": 1, "січень": 1,
            "лютого": 2, "лютий": 2,
            "березня": 3, "березень": 3,
            "квітня": 4, "квітень": 4,
            "травня": 5, "травень": 5,
            "червня": 6, "червень": 6,
            "липня": 7, "липень": 7,
            "серпня": 8, "серпень": 8,
            "вересня": 9, "вересень": 9,
            "жовтня": 10, "жовтень": 10,
            "листопада": 11, "листопад": 11,
            "грудня": 12, "грудень": 12
        }

        for month_name, month_num in months_map.items():
            pattern = rf'(\d{1,2})\s+{month_name}'
            match = re.search(pattern, text_lower)
            if match:
                day = int(match.group(1))
                year = self.today.year
                # Якщо дата вже минула цього року, беремо наступний рік
                from datetime import date
                try:
                    target_date = date(year, month_num, day)
                    if target_date < self.today:
                        target_date = date(year + 1, month_num, day)
                    return target_date.isoformat()
                except ValueError:
                    pass

        return None


class RangeExtractor:
    """Витягування діапазонів (числових, часових)"""

    def extract(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Витягує діапазон з тексту

        Examples:
            "від 10 до 20" -> {"from": 10, "to": 20}
            "між 5 і 15" -> {"from": 5, "to": 15}
            "з 9 до 17" -> {"from": 9, "to": 17}
        """
        text_lower = text.lower()

        # Паттерн "від X до Y"
        pattern1 = r'від\s+(\d+)\s+до\s+(\d+)'
        match = re.search(pattern1, text_lower)
        if match:
            return {
                "from": int(match.group(1)),
                "to": int(match.group(2)),
                "type": "numeric"
            }

        # Паттерн "між X і Y"
        pattern2 = r'між\s+(\d+)\s+[іi]\s+(\d+)'
        match = re.search(pattern2, text_lower)
        if match:
            return {
                "from": int(match.group(1)),
                "to": int(match.group(2)),
                "type": "numeric"
            }

        # Паттерн "з X до Y"
        pattern3 = r'з\s+(\d+)\s+до\s+(\d+)'
        match = re.search(pattern3, text_lower)
        if match:
            return {
                "from": int(match.group(1)),
                "to": int(match.group(2)),
                "type": "numeric"
            }

        # Часовий діапазон "з 9:00 до 17:00"
        time_pattern = r'з\s+(\d{1,2}):(\d{2})\s+до\s+(\d{1,2}):(\d{2})'
        match = re.search(time_pattern, text_lower)
        if match:
            return {
                "from": f"{int(match.group(1)):02d}:{match.group(2)}",
                "to": f"{int(match.group(3)):02d}:{match.group(4)}",
                "type": "time"
            }

        return None


class MultipleItemsExtractor:
    """Витягування множинних об'єктів"""

    def extract(self, text: str, item_type: str = "app") -> Optional[List[str]]:
        """
        Витягує список об'єктів з тексту

        Examples:
            "запусти chrome і firefox" -> ["chrome", "firefox"]
            "увімкни світло та розетку" -> ["світло", "розетку"]
            "знайди python, javascript і rust" -> ["python", "javascript", "rust"]

        Args:
            text: Текст команди
            item_type: Тип об'єктів (app, device, etc.)

        Returns:
            Список знайдених об'єктів або None
        """
        text_lower = text.lower()

        # Розділювачі
        separators = [" і ", " та ", " й ", ", ", " and ", " plus ", " плюс "]

        # Видаляємо команду з початку
        command_keywords = [
            "запусти", "відкрий", "стартуй", "run", "open",
            "увімкни", "включи", "засвіти", "on",
            "знайди", "пошукай", "find", "search"
        ]

        for keyword in command_keywords:
            if keyword in text_lower:
                idx = text_lower.find(keyword)
                text_lower = text_lower[idx + len(keyword):].strip()
                break

        # Шукаємо розділювачі
        items = [text_lower]
        for sep in separators:
            if sep in text_lower:
                items = text_lower.split(sep)
                break

        # Очищаємо та фільтруємо
        items = [item.strip() for item in items if item.strip()]

        # Якщо знайшли більше одного елемента - повертаємо список
        if len(items) > 1:
            return items

        return None


# Глобальний екземпляр для використання в інших модулях
entity_extractor = EntityExtractor()
