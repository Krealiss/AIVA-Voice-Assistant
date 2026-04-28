"""
Тести для utils.py
"""
import pytest
import time
from utils import retry, measure_time, safe_execute, ErrorHandler, truncate_text, validate_config


def test_retry_success():
    """Тест успішного виконання з retry"""
    call_count = 0

    @retry(max_attempts=3, delay=0.1)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Temporary failure")
        return "Success"

    result = flaky_function()
    assert result == "Success"
    assert call_count == 2


def test_retry_failure():
    """Тест невдалого виконання після всіх спроб"""
    @retry(max_attempts=2, delay=0.1)
    def always_fails():
        raise ValueError("Always fails")

    with pytest.raises(ValueError):
        always_fails()


def test_measure_time():
    """Тест вимірювання часу"""
    @measure_time
    def slow_function():
        time.sleep(0.1)
        return "Done"

    result = slow_function()
    assert result == "Done"


def test_safe_execute_with_error():
    """Тест безпечного виконання з помилкою"""
    @safe_execute(default_return="Error")
    def risky_function():
        return 1 / 0

    result = risky_function()
    assert result == "Error"


def test_safe_execute_success():
    """Тест безпечного виконання без помилки"""
    @safe_execute(default_return="Error")
    def safe_function():
        return "Success"

    result = safe_function()
    assert result == "Success"


def test_error_handler_api():
    """Тест обробки API помилок"""
    error = ConnectionError("Connection failed")
    result = ErrorHandler.handle_api_error(error, "TestAPI")
    assert "TestAPI" in result
    assert "помилка" in result.lower()


def test_error_handler_db():
    """Тест обробки помилок БД"""
    error = Exception("DB error")
    result = ErrorHandler.handle_db_error(error, "SELECT")
    assert "SELECT" in result


def test_truncate_text_short():
    """Тест обрізання короткого тексту"""
    text = "Short text"
    result = truncate_text(text, max_length=100)
    assert result == text


def test_truncate_text_long():
    """Тест обрізання довгого тексту"""
    text = "A" * 200
    result = truncate_text(text, max_length=50)
    assert len(result) == 50
    assert result.endswith("...")


def test_validate_config_valid():
    """Тест валідації правильної конфігурації"""
    config = {"key1": "value1", "key2": "value2"}
    is_valid, error = validate_config(config, ["key1", "key2"])
    assert is_valid is True
    assert error is None


def test_validate_config_missing_keys():
    """Тест валідації з відсутніми ключами"""
    config = {"key1": "value1"}
    is_valid, error = validate_config(config, ["key1", "key2"])
    assert is_valid is False
    assert "key2" in error


def test_validate_config_empty_values():
    """Тест валідації з порожніми значеннями"""
    config = {"key1": "value1", "key2": ""}
    is_valid, error = validate_config(config, ["key1", "key2"])
    assert is_valid is False
    assert "key2" in error
