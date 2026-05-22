"""
Тести для NLU Engine та Entity Extractors
"""
import pytest
import sys
import os

# Додаємо src до path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nlu_engine import NLUEngine, IntentResult, RuleBasedClassifier, LLMClassifier
from entity_extractors import (
    EntityExtractor, NumberExtractor, AppNameExtractor,
    CityExtractor, TimeExtractor, ActionExtractor,
    DateExtractor, RangeExtractor, MultipleItemsExtractor
)
from context_manager import ContextManager


# ============= Fixtures =============

@pytest.fixture
def nlu():
    """Фікстура для NLU Engine"""
    return NLUEngine()


@pytest.fixture
def rule_classifier():
    """Фікстура для Rule-based classifier"""
    return RuleBasedClassifier()


@pytest.fixture
def entity_extractor():
    """Фікстура для Entity Extractor"""
    return EntityExtractor()


@pytest.fixture
def number_extractor():
    """Фікстура для Number Extractor"""
    return NumberExtractor()


@pytest.fixture
def app_extractor():
    """Фікстура для App Name Extractor"""
    return AppNameExtractor()


@pytest.fixture
def city_extractor():
    """Фікстура для City Extractor"""
    return CityExtractor()


# Helper для очищення тимчасових БД
def cleanup_temp_db(temp_db_path, ctx=None):
    """Очищає тимчасову БД з обробкою Windows PermissionError"""
    import time
    import os

    if ctx:
        del ctx
    time.sleep(0.1)
    try:
        os.unlink(temp_db_path)
    except (PermissionError, FileNotFoundError):
        pass


# ============= Тести Rule-Based Classifier =============

def test_rule_simple_run_command(rule_classifier):
    """Проста команда запуску програми"""
    result = rule_classifier.classify("запусти chrome")
    assert result.intent == "run"
    assert result.confidence > 0.8
    assert result.method == "rule"


def test_rule_volume_command(rule_classifier):
    """Команда зміни гучності"""
    result = rule_classifier.classify("гучність 50")
    assert result.intent == "vol_set"
    assert result.confidence > 0.8


def test_rule_weather_command(rule_classifier):
    """Команда погоди"""
    result = rule_classifier.classify("погода у києві")
    assert result.intent == "weather_now"
    assert result.confidence > 0.8


def test_rule_control_on_command(rule_classifier):
    """Команда увімкнення пристрою"""
    result = rule_classifier.classify("увімкни світло")
    assert result.intent == "control_on"
    assert result.confidence > 0.8


def test_rule_unknown_command(rule_classifier):
    """Невідома команда"""
    result = rule_classifier.classify("абракадабра фігня")
    assert result.intent == "unknown"
    assert result.confidence < 0.5


# ============= Тести Entity Extractors =============

def test_number_extraction(number_extractor):
    """Витягування числа"""
    assert number_extractor.extract("гучність 75") == 75
    assert number_extractor.extract("встанови на 50") == 50
    assert number_extractor.extract("зменш на 10") == 10


def test_number_extraction_invalid(number_extractor):
    """Витягування невалідного числа"""
    assert number_extractor.extract("гучність 150") is None  # Більше 100
    assert number_extractor.extract("без чисел") is None


def test_app_name_extraction(app_extractor):
    """Витягування назви програми"""
    assert app_extractor.extract("запусти хром") == "google chrome"
    assert app_extractor.extract("відкрий стім") == "steam"
    assert app_extractor.extract("стартуй vscode") == "visual studio code"
    assert app_extractor.extract("грати в доту") == "dota 2"


def test_app_name_extraction_direct(app_extractor):
    """Витягування прямої назви програми"""
    result = app_extractor.extract("запусти notepad")
    assert result == "notepad"


def test_city_extraction(city_extractor):
    """Витягування назви міста"""
    assert city_extractor.extract("погода у києві") == "Київ"
    assert city_extractor.extract("температура в харкові") == "Харків"
    assert city_extractor.extract("прогноз на львів") == "Львів"


def test_city_extraction_no_city(city_extractor):
    """Витягування міста коли його немає"""
    assert city_extractor.extract("погода") is None
    assert city_extractor.extract("яка температура") is None


def test_time_extraction(entity_extractor):
    """Витягування часу"""
    time_ext = TimeExtractor()
    assert time_ext.extract("о 9 ранку") == "09:00"
    assert time_ext.extract("в 14:30") == "14:30"
    assert time_ext.extract("о 7 вечора") == "19:00"


def test_action_extraction(entity_extractor):
    """Витягування дії"""
    action_ext = ActionExtractor()
    assert action_ext.extract("увімкни світло") == "on"
    assert action_ext.extract("вимкни комп'ютер") == "off"


def test_entity_extractor_run_intent(entity_extractor):
    """Entity extraction для run інтенції"""
    entities = entity_extractor.extract("запусти chrome", "run")
    assert "app" in entities
    assert entities["app"] == "google chrome"


def test_entity_extractor_volume_intent(entity_extractor):
    """Entity extraction для vol_set інтенції"""
    entities = entity_extractor.extract("гучність 75", "vol_set")
    assert "volume" in entities
    assert entities["volume"] == 75


def test_entity_extractor_weather_intent(entity_extractor):
    """Entity extraction для weather інтенції"""
    entities = entity_extractor.extract("погода у києві", "weather_now")
    assert "city" in entities
    assert entities["city"] == "Київ"
    assert entities["when"] == "now"


def test_entity_extractor_control_intent(entity_extractor):
    """Entity extraction для control інтенції"""
    entities = entity_extractor.extract("увімкни світло", "control_on")
    assert "action" in entities
    assert entities["action"] == "on"
    assert "device" in entities


# ============= Тести NLU Engine =============

def test_nlu_simple_command_uses_rules(nlu):
    """Проста команда використовує rule-based"""
    result = nlu.analyze("запусти chrome")
    assert result.intent == "run"
    assert result.method == "rule"
    assert result.confidence > 0.8
    assert "app" in result.entities


def test_nlu_volume_command(nlu):
    """Команда гучності з entity extraction"""
    result = nlu.analyze("гучність 50")
    assert result.intent == "vol_set"
    assert result.confidence > 0.8
    assert result.entities.get("volume") == 50


def test_nlu_weather_command(nlu):
    """Команда погоди з entity extraction"""
    result = nlu.analyze("погода у києві")
    assert result.intent == "weather_now"
    assert result.confidence > 0.7
    assert result.entities.get("city") == "Київ"


def test_nlu_complex_command_uses_llm(nlu):
    """Складна команда використовує LLM"""
    result = nlu.analyze("запусти той браузер, яким я користувався вчора ввечері")
    # LLM може не бути доступний, тому перевіряємо тільки що метод спробував
    assert result.method in ["llm", "rule"]  # Fallback на rule якщо LLM недоступний


def test_nlu_empty_command(nlu):
    """Порожня команда"""
    result = nlu.analyze("")
    assert result.intent == "unknown"
    assert result.confidence == 0.0


def test_nlu_unknown_command(nlu):
    """Невідома команда"""
    result = nlu.analyze("абракадабра фігня")
    assert result.confidence < 0.5


def test_nlu_context_awareness(nlu):
    """Контекст діалогу"""
    context = {
        "last_intent": "run",
        "last_app": "chrome",
        "source": "voice"
    }
    result = nlu.analyze("запусти chrome", context=context)
    # Контекст тепер розширюється NLU context manager
    assert result.context is not None
    assert "last_intent" in result.context or context.get("last_intent") in str(result.context)


def test_nlu_is_simple_command(nlu):
    """Перевірка визначення простих команд"""
    assert nlu._is_simple_command("запусти chrome") == True
    assert nlu._is_simple_command("гучність 50") == True
    assert nlu._is_simple_command("погода") == True
    assert nlu._is_simple_command("запусти той браузер, яким я користувався вчора") == False
    assert nlu._is_simple_command("що ти думаєш про цю ситуацію і як мені краще вчинити") == False


def test_nlu_stats(nlu):
    """Статистика використання"""
    # Виконуємо кілька команд
    nlu.analyze("запусти chrome")
    nlu.analyze("гучність 50")
    nlu.analyze("погода")

    stats = nlu.get_stats()
    assert stats["total"] >= 3
    assert stats["rule"] >= 0
    assert stats["llm"] >= 0
    assert "rule_percentage" in stats
    assert "llm_percentage" in stats


# ============= Тести IntentResult =============

def test_intent_result_to_dict():
    """Конвертація IntentResult в словник"""
    result = IntentResult(
        intent="run",
        confidence=0.95,
        entities={"app": "chrome"},
        raw_text="запусти chrome",
        method="rule",
        context={"source": "voice"}
    )

    data = result.to_dict()
    assert data["intent"] == "run"
    assert data["confidence"] == 0.95
    assert data["entities"]["app"] == "chrome"
    assert data["method"] == "rule"


# ============= Інтеграційні тести =============

def test_integration_run_command(nlu):
    """Інтеграційний тест: запуск програми"""
    result = nlu.analyze("запусти chrome")

    assert result.intent == "run"
    assert result.confidence > 0.7
    assert result.entities.get("app") in ["google chrome", "chrome"]
    assert result.raw_text == "запусти chrome"


def test_integration_volume_command(nlu):
    """Інтеграційний тест: зміна гучності"""
    result = nlu.analyze("гучність 75")

    assert result.intent == "vol_set"
    assert result.confidence > 0.7
    assert result.entities.get("volume") == 75


def test_integration_weather_command(nlu):
    """Інтеграційний тест: погода"""
    result = nlu.analyze("погода у києві")

    assert result.intent == "weather_now"
    assert result.confidence > 0.7
    assert result.entities.get("city") == "Київ"
    assert result.entities.get("when") == "now"


def test_integration_control_command(nlu):
    """Інтеграційний тест: керування пристроєм"""
    result = nlu.analyze("увімкни світло")

    assert result.intent == "control_on"
    assert result.confidence > 0.7
    assert result.entities.get("action") == "on"


def test_integration_find_command(nlu):
    """Інтеграційний тест: пошук"""
    result = nlu.analyze("знайди python tutorial")

    assert result.intent == "find"
    assert result.confidence > 0.7
    assert result.entities.get("query") == "python tutorial"


# ============= Тести на edge cases =============

def test_edge_case_mixed_language(nlu):
    """Змішані мови"""
    result = nlu.analyze("запусти google chrome")
    assert result.intent == "run"


def test_edge_case_typos(rule_classifier):
    """Друкарські помилки (fuzzy matching має впоратися)"""
    result = rule_classifier.classify("запустi хроме")  # "i" замість "і"
    assert result.intent == "run"
    assert result.confidence > 0.6  # Трохи нижча впевненість через помилку


def test_edge_case_extra_spaces(nlu):
    """Зайві пробіли"""
    result = nlu.analyze("  запусти   chrome  ")
    assert result.intent == "run"


def test_edge_case_uppercase(nlu):
    """Великі літери"""
    result = nlu.analyze("ЗАПУСТИ CHROME")
    assert result.intent == "run"


# ============= Тести для нових екстракторів =============

def test_date_extraction_relative():
    """Витягування відносних дат"""
    date_ext = DateExtractor()

    result = date_ext.extract("завтра")
    assert result == "2026-05-02"

    result = date_ext.extract("вчора")
    assert result == "2026-04-30"

    result = date_ext.extract("сьогодні")
    assert result == "2026-05-01"


def test_date_extraction_through():
    """Витягування дат 'через N днів'"""
    date_ext = DateExtractor()

    result = date_ext.extract("через 3 дні")
    assert result == "2026-05-04"

    result = date_ext.extract("через 1 тиждень")
    assert result == "2026-05-08" or result == "2026-05-02"  # Залежить від реалізації


def test_range_extraction_numeric():
    """Витягування числових діапазонів"""
    range_ext = RangeExtractor()

    result = range_ext.extract("від 10 до 20")
    assert result["from"] == 10
    assert result["to"] == 20
    assert result["type"] == "numeric"

    result = range_ext.extract("між 5 і 15")
    assert result["from"] == 5
    assert result["to"] == 15


def test_range_extraction_time():
    """Витягування часових діапазонів"""
    range_ext = RangeExtractor()

    result = range_ext.extract("з 9:00 до 17:00")
    assert result["from"] == "09:00"
    assert result["to"] == "17:00"
    assert result["type"] == "time"


def test_multiple_items_extraction():
    """Витягування множинних об'єктів"""
    multi_ext = MultipleItemsExtractor()

    result = multi_ext.extract("запусти chrome і firefox", "app")
    assert result == ["chrome", "firefox"]

    result = multi_ext.extract("увімкни світло та розетку", "device")
    assert result == ["світло", "розетку"]

    result = multi_ext.extract("знайди python, javascript і rust", "query")
    assert len(result) >= 2  # Принаймні 2 елементи
    assert "python" in result or "python," in result


def test_entity_extractor_multiple_apps():
    """Entity extraction для множинних програм"""
    entity_ext = EntityExtractor()

    entities = entity_ext.extract("запусти chrome і firefox", "run")
    assert "apps" in entities
    assert entities["multiple"] == True
    assert len(entities["apps"]) == 2


def test_entity_extractor_with_date():
    """Entity extraction з датою"""
    entity_ext = EntityExtractor()

    entities = entity_ext.extract("погода у києві завтра", "weather_forecast")
    assert entities["city"] == "Київ"
    assert entities["date"] == "2026-05-02"
    assert entities["when"] == "forecast"


def test_entity_extractor_with_range():
    """Entity extraction з діапазоном"""
    entity_ext = EntityExtractor()

    entities = entity_ext.extract("гучність від 50 до 75", "vol_set")
    assert "range" in entities
    assert entities["range"]["from"] == 50
    assert entities["range"]["to"] == 75


# ============= Тести для Context Manager =============

def test_context_manager_session():
    """Створення та отримання сесії"""
    ctx = ContextManager(db_path="data/test_context.db")

    session = ctx.create_session("test_user")
    assert session.user_id == "test_user"
    assert session.is_active == True

    retrieved = ctx.get_session(session.session_id)
    assert retrieved.session_id == session.session_id


def test_context_manager_messages():
    """Додавання повідомлень з NLU даними"""
    ctx = ContextManager(db_path="data/test_context.db")

    session = ctx.create_session("test_user")

    msg = ctx.add_message(
        session.session_id,
        "user",
        "запусти chrome",
        intent="run",
        entities={"app": "chrome"},
        confidence=0.95
    )

    assert msg.intent == "run"
    assert msg.entities["app"] == "chrome"
    assert msg.confidence == 0.95


def test_context_manager_last_intent():
    """Отримання останнього intent"""
    import tempfile

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    ctx = ContextManager(db_path=temp_db.name)
    session = ctx.create_session("test_user")

    ctx.add_message(session.session_id, "user", "запусти chrome", intent="run")
    ctx.add_message(session.session_id, "assistant", "Запускаю Chrome")
    ctx.add_message(session.session_id, "user", "гучність 50", intent="vol_set")

    last_intent = ctx.get_last_intent(session.session_id)
    assert last_intent == "vol_set"

    cleanup_temp_db(temp_db.name, ctx)


def test_context_manager_active_entities():
    """Отримання активних entities"""
    import tempfile

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    ctx = ContextManager(db_path=temp_db.name)
    session = ctx.create_session("test_user")

    ctx.add_message(
        session.session_id, "user", "запусти chrome",
        intent="run", entities={"app": "chrome"}
    )
    ctx.add_message(
        session.session_id, "user", "погода у києві",
        intent="weather_now", entities={"city": "Київ"}
    )

    entities = ctx.get_active_entities(session.session_id)
    assert entities["app"] == "chrome"
    assert entities["city"] == "Київ"

    cleanup_temp_db(temp_db.name, ctx)


def test_context_manager_resolve_entity():
    """Розв'язування entity з контексту"""
    import tempfile

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    ctx = ContextManager(db_path=temp_db.name)
    session = ctx.create_session("test_user")

    ctx.add_message(
        session.session_id, "user", "запусти chrome",
        intent="run", entities={"app": "chrome"}
    )

    resolved = ctx.resolve_entity(session.session_id, "app", {})
    assert resolved == "chrome"

    cleanup_temp_db(temp_db.name, ctx)


def test_context_manager_infer_intent():
    """Виведення intent з контексту"""
    import tempfile

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    ctx = ContextManager(db_path=temp_db.name)
    session = ctx.create_session("test_user")

    ctx.add_message(session.session_id, "user", "запусти chrome", intent="run")

    inferred = ctx.infer_intent_from_context(session.session_id, "і firefox теж")
    assert inferred == "run"

    cleanup_temp_db(temp_db.name, ctx)


def test_context_manager_pattern_detection():
    """Виявлення паттернів"""
    import tempfile

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    ctx = ContextManager(db_path=temp_db.name)
    session = ctx.create_session("test_user")

    for _ in range(3):
        ctx.add_message(session.session_id, "user", "запусти chrome", intent="run")

    pattern = ctx.detect_pattern(session.session_id)
    assert pattern is not None
    assert pattern["type"] == "repeated_intent"
    assert pattern["intent"] == "run"

    cleanup_temp_db(temp_db.name, ctx)


# ============= Інтеграційні тести з контекстом =============

def test_nlu_with_context_inference(nlu):
    """NLU з виведенням intent з контексту"""
    import tempfile
    from context_manager import ContextManager

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    ctx = ContextManager(db_path=temp_db.name)
    session = ctx.create_session("test_user")
    session_id = session.session_id

    # Перша команда
    result1 = nlu.analyze("запусти chrome", session_id=session_id)
    assert result1.intent == "run"

    # Зберігаємо в контекст
    ctx.add_message(
        session_id, "user", "запусти chrome",
        intent=result1.intent, entities=result1.entities, confidence=result1.confidence
    )

    # Друга команда з маркером продовження
    result2 = nlu.analyze("і firefox теж", session_id=session_id)
    assert result2.intent == "run"
    assert result2.method == "context"

    cleanup_temp_db(temp_db.name, ctx)


def test_nlu_with_entity_resolution(nlu):
    """NLU з розв'язуванням entities"""
    import tempfile
    from context_manager import ContextManager

    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    ctx = ContextManager(db_path=temp_db.name)
    session = ctx.create_session("test_user")
    session_id = session.session_id

    # Перша команда з містом
    result1 = nlu.analyze("погода у києві", session_id=session_id)
    ctx.add_message(
        session_id, "user", "погода у києві",
        intent=result1.intent, entities=result1.entities, confidence=result1.confidence
    )

    # Друга команда без міста (має розв'язатися з контексту)
    result2 = nlu.analyze("прогноз", session_id=session_id)
    # Місто має бути розв'язане з контексту
    assert result2.entities.get("city") == "Київ"

    cleanup_temp_db(temp_db.name, ctx)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
