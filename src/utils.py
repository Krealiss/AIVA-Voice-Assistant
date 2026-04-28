"""
Утиліти для AIVA: декоратори, хелпери, обробка помилок
"""
import time
import logging
import functools
from typing import Callable, Any, Optional, Type
from datetime import datetime

logger = logging.getLogger("utils")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Декоратор для автоматичних повторних спроб при помилках.

    Args:
        max_attempts: Максимальна кількість спроб
        delay: Початкова затримка між спробами (секунди)
        backoff: Множник для збільшення затримки
        exceptions: Tuple винятків, які треба ловити

    Example:
        @retry(max_attempts=3, delay=1.0)
        def unstable_api_call():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            raise last_exception

        return wrapper
    return decorator


def measure_time(func: Callable) -> Callable:
    """
    Декоратор для вимірювання часу виконання функції.

    Example:
        @measure_time
        def slow_function():
            time.sleep(2)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start

        logger.debug(f"{func.__name__} took {elapsed:.3f}s")
        return result

    return wrapper


def safe_execute(
    default_return: Any = None,
    log_errors: bool = True,
    raise_on_error: bool = False
):
    """
    Декоратор для безпечного виконання з обробкою помилок.

    Args:
        default_return: Значення, яке повертається при помилці
        log_errors: Чи логувати помилки
        raise_on_error: Чи піднімати виняток після логування

    Example:
        @safe_execute(default_return="Помилка")
        def risky_function():
            return 1 / 0
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(
                        f"Error in {func.__name__}: {type(e).__name__}: {e}",
                        exc_info=True
                    )

                if raise_on_error:
                    raise

                return default_return

        return wrapper
    return decorator


class ErrorHandler:
    """
    Централізований обробник помилок для AIVA.
    """

    @staticmethod
    def handle_api_error(error: Exception, service: str) -> str:
        """Обробка помилок API"""
        logger.error(f"{service} API error: {error}")
        return f"Помилка зв'язку з {service}. Спробуй пізніше."

    @staticmethod
    def handle_file_error(error: Exception, file_path: str) -> str:
        """Обробка помилок файлової системи"""
        logger.error(f"File error ({file_path}): {error}")
        return f"Помилка доступу до файлу: {file_path}"

    @staticmethod
    def handle_db_error(error: Exception, operation: str) -> str:
        """Обробка помилок бази даних"""
        logger.error(f"Database error ({operation}): {error}")
        return f"Помилка бази даних при {operation}"

    @staticmethod
    def handle_recognition_error(error: Exception) -> str:
        """Обробка помилок розпізнавання"""
        logger.error(f"Recognition error: {error}")
        return "Не вдалося розпізнати команду. Спробуй ще раз."


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Форматує timestamp для логів.

    Args:
        dt: datetime об'єкт (якщо None - використовується поточний час)

    Returns:
        Відформатований рядок
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрізає текст до максимальної довжини.

    Args:
        text: Вхідний текст
        max_length: Максимальна довжина
        suffix: Суфікс для обрізаного тексту

    Returns:
        Обрізаний текст
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_config(config: dict, required_keys: list) -> tuple[bool, Optional[str]]:
    """
    Валідує конфігурацію.

    Args:
        config: Словник конфігурації
        required_keys: Список обов'язкових ключів

    Returns:
        (is_valid, error_message)
    """
    missing_keys = [key for key in required_keys if key not in config or not config[key]]

    if missing_keys:
        return False, f"Відсутні обов'язкові параметри: {', '.join(missing_keys)}"

    return True, None


# Приклади використання
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Тест retry
    @retry(max_attempts=3, delay=0.5)
    def flaky_function():
        import random
        if random.random() < 0.7:
            raise ConnectionError("Random failure")
        return "Success!"

    # Тест measure_time
    @measure_time
    def slow_function():
        time.sleep(0.1)
        return "Done"

    # Тест safe_execute
    @safe_execute(default_return="Error occurred")
    def risky_function():
        return 1 / 0

    print("Testing retry:", flaky_function())
    print("Testing measure_time:", slow_function())
    print("Testing safe_execute:", risky_function())
