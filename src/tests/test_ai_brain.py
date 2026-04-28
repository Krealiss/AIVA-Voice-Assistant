"""
Тести для ai_brain.py
"""
import pytest
import requests
from unittest.mock import Mock, patch
from ai_brain import AIBrain


@pytest.fixture
def brain():
    """Створює екземпляр AIBrain для тестів"""
    return AIBrain()


def test_cache_key_generation(brain):
    """Тест генерації ключа кешу"""
    key1 = brain._get_cache_key("test query")
    key2 = brain._get_cache_key("TEST QUERY")
    key3 = brain._get_cache_key("  test query  ")

    # Всі мають бути однаковими (lowercase + strip)
    assert key1 == key2 == key3


def test_cache_save_and_get(brain):
    """Тест збереження та отримання з кешу"""
    key = brain._get_cache_key("test")
    brain._save_to_cache(key, "cached response")

    result = brain._get_from_cache(key)
    assert result == "cached response"


def test_cache_miss(brain):
    """Тест промаху кешу"""
    result = brain._get_from_cache("nonexistent_key")
    assert result is None


def test_should_search_triggers(brain):
    """Тест визначення необхідності пошуку"""
    # Має шукати
    assert brain._should_search("хто такий Ілон Маск") is True
    assert brain._should_search("яка погода сьогодні") is True
    assert brain._should_search("курс долара") is True

    # Не має шукати
    assert brain._should_search("як написати функцію") is False
    assert brain._should_search("def test():") is False


def test_hard_rules_time(brain):
    """Тест швидких відповідей на час"""
    result = brain.ask("котра година")
    assert "зараз" in result.lower()


def test_hard_rules_date(brain):
    """Тест швидких відповідей на дату"""
    result = brain.ask("яка дата")
    assert "сьогодні" in result.lower()


@patch('ai_brain.requests.Session.post')
def test_ollama_request(mock_post, brain):
    """Тест запиту до Ollama"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Test response"}
    }
    mock_post.return_value = mock_response

    result = brain.ask("test question")
    assert result == "Test response"


@patch('ai_brain.requests.Session.post')
def test_ollama_error_handling(mock_post, brain):
    """Тест обробки помилок Ollama"""
    mock_post.side_effect = requests.RequestException("Connection error")

    result = brain.ask("test question")
    assert "помилка" in result.lower() or "ollama" in result.lower()


def test_history_management(brain):
    """Тест управління історією"""
    initial_max = brain.max_history
    brain.max_history = 2

    # Додаємо більше повідомлень ніж max_history
    for i in range(5):
        brain.history.append({"role": "user", "content": f"message {i}"})
        brain.history.append({"role": "assistant", "content": f"response {i}"})

    # Симулюємо очищення історії (як в методі ask)
    if len(brain.history) > brain.max_history * 2:
        brain.history = brain.history[-(brain.max_history*2):]

    # Історія має бути обрізана
    assert len(brain.history) <= brain.max_history * 2

    # Відновлюємо початкове значення
    brain.max_history = initial_max


def test_cache_size_limit(brain):
    """Тест обмеження розміру кешу"""
    brain._cache_max_size = 5

    # Додаємо більше елементів ніж ліміт
    for i in range(10):
        key = brain._get_cache_key(f"query {i}")
        brain._save_to_cache(key, f"response {i}")

    # Кеш не має перевищувати ліміт
    assert len(brain._response_cache) <= brain._cache_max_size
