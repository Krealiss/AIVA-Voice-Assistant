"""
Тести для db_manager.py
"""
import pytest
import os
import tempfile
from db_manager import DatabaseManager


@pytest.fixture
def temp_db():
    """Створює тимчасову БД для тестів"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db = DatabaseManager(path)
    yield db

    db.close()
    if os.path.exists(path):
        os.remove(path)


def test_database_initialization(temp_db):
    """Тест ініціалізації БД"""
    counts = temp_db.get_counts()
    assert counts["total"] == 0
    assert isinstance(counts["by_source"], dict)


def test_add_app(temp_db):
    """Тест додавання додатку"""
    temp_db.add_app(
        name="Test App",
        exe_path="C:\\test.exe",
        canonical_name="testapp",
        source="test",
        score=100
    )

    counts = temp_db.get_counts()
    assert counts["total"] == 1


def test_get_exe_by_canonical(temp_db):
    """Тест пошуку за канонічною назвою"""
    temp_db.add_app(
        name="Chrome",
        exe_path="C:\\chrome.exe",
        canonical_name="chrome",
        score=100
    )

    result = temp_db.get_exe_by_canonical("chrome")
    assert result is not None
    assert result[0] == "Chrome"
    assert result[1] == "C:\\chrome.exe"


def test_cache_performance(temp_db):
    """Тест кешування"""
    temp_db.add_app(
        name="Test",
        exe_path="C:\\test.exe",
        canonical_name="test",
        score=50
    )

    # Перший виклик
    result1 = temp_db.get_exe_by_canonical("test")

    # Другий виклик (має бути з кешу)
    result2 = temp_db.get_exe_by_canonical("test")

    assert result1 == result2


def test_load_apps(temp_db):
    """Тест завантаження всіх додатків"""
    temp_db.add_app("App1", "C:\\app1.exe", "app1", score=100)
    temp_db.add_app("App2", "C:\\app2.exe", "app2", score=50)

    apps = temp_db.load_apps()
    assert len(apps) == 2
    # Перевіряємо сортування за score
    assert apps[0][0] == "App1"  # Вищий score


def test_get_counts_by_source(temp_db):
    """Тест статистики по джерелах"""
    temp_db.add_app("App1", "C:\\app1.exe", source="steam")
    temp_db.add_app("App2", "C:\\app2.exe", source="steam")
    temp_db.add_app("App3", "C:\\app3.exe", source="manual")

    counts = temp_db.get_counts()
    assert counts["total"] == 3
    assert counts["by_source"]["steam"] == 2
    assert counts["by_source"]["manual"] == 1


def test_nonexistent_canonical(temp_db):
    """Тест пошуку неіснуючого додатку"""
    result = temp_db.get_exe_by_canonical("nonexistent")
    assert result is None


def test_empty_canonical(temp_db):
    """Тест пошуку з порожнім запитом"""
    result = temp_db.get_exe_by_canonical("")
    assert result is None
