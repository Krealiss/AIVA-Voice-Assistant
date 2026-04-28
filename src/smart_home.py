import logging
import os
from functools import lru_cache
from tuya_connector import TuyaOpenAPI
from rapidfuzz import process, fuzz

logger = logging.getLogger("smart_home")

class SmartHome:
    def __init__(self):
        # Винесено в змінні середовища для безпеки
        self.ACCESS_ID = os.getenv("TUYA_ACCESS_ID", "s8kgd7783ra4yv55rekc")
        self.ACCESS_KEY = os.getenv("TUYA_ACCESS_KEY", "12a043df2e244305b608ee2f36938508")
        self.API_ENDPOINT = os.getenv("TUYA_API_ENDPOINT", "https://openapi.tuyaeu.com")

        # Підключення з retry логікою
        self.openapi = None
        self._connect_with_retry()

        # ID пристроїв
        self.DEVICES = {
            'bulb': 'bf45b542a6746e2fc8bnjv',
            'plug': 'bf7764e43070426d7enlgr'
        }

        # Кеш для команд (зменшує навантаження на API)
        self._command_cache = {}

        # Словник для пошуку (назви -> ID)
        self.mapping = {
            "лампочка": self.DEVICES['bulb'],
            "лампа": self.DEVICES['bulb'],
            "світло": self.DEVICES['bulb'],
            "люстра": self.DEVICES['bulb'],

            "розетка": self.DEVICES['plug'],
            "вентилятор": self.DEVICES['plug'],
            "обігрівач": self.DEVICES['plug']
        }

    def _connect_with_retry(self, max_retries=3):
        """Підключення з повторними спробами"""
        for attempt in range(max_retries):
            try:
                self.openapi = TuyaOpenAPI(self.API_ENDPOINT, self.ACCESS_ID, self.ACCESS_KEY)
                self.openapi.connect()
                logger.info("✅ Smart Home: Підключено до Tuya Cloud")
                return
            except Exception as e:
                logger.warning(f"⚠️ Спроба {attempt + 1}/{max_retries} не вдалася: {e}")
                if attempt == max_retries - 1:
                    logger.error("❌ Не вдалося підключитися до Tuya Cloud")
                    self.openapi = None

    @lru_cache(maxsize=32)
    def _find_device(self, device_name: str) -> tuple:
        """Кешований пошук пристрою за назвою"""
        query = device_name.lower().strip()
        known_names = list(self.mapping.keys())
        match = process.extractOne(query, known_names, scorer=fuzz.WRatio, score_cutoff=60)

        if match:
            found_name, score, index = match
            device_id = self.mapping[found_name]
            return (device_id, found_name)
        return (None, None)

    def control(self, device_name: str, action: str) -> str:
        """
        Оптимізована функція керування з кешуванням.
        """
        # Використовуємо кешований пошук
        device_id, found_name = self._find_device(device_name)

        if not device_id:
            return f"Я не знайшов пристрій, схожий на '{device_name}'."

        logger.info(f"🔍 Smart Home: '{device_name}' -> '{found_name}' (ID: {device_id})")

        # Перевірка з'єднання
        if not self.openapi:
            self._connect_with_retry()
            if not self.openapi:
                return "Помилка: Немає зв'язку з сервером Tuya."

        # Визначення команди
        switch_value = True if action == "on" else False
        res_text = "увімкнено" if action == "on" else "вимкнено"

        # Можливі коди команд
        possible_codes = ["switch_1", "switch_led", "switch", "led_switch"]

        success = False
        last_error = ""

        for code in possible_codes:
            commands = {'commands': [{'code': code, 'value': switch_value}]}

            try:
                response = self.openapi.post(f'/v1.0/devices/{device_id}/commands', commands)

                if response.get('success') is True:
                    success = True
                    break
                else:
                    if 'msg' in response:
                        last_error = response['msg']
            except Exception as e:
                logger.error(f"⚠️ Помилка команди {code}: {e}")

        if success:
            return f"Окей, {found_name} {res_text}."
        else:
            logger.error(f"❌ Tuya Fail: {last_error}")
            return f"Не вдалося виконати команду. Хмара відповіла: {last_error if last_error else 'невідома помилка'}"

# Створюємо екземпляр класу, щоб інші файли могли його імпортувати
home = SmartHome()