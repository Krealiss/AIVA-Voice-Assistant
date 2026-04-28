"""
Скрипт для тестування продуктивності AIVA
"""
import time
import sys
import os

# Додаємо поточну директорію до шляху
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_performance():
    """Тест продуктивності бази даних"""
    print("\n=== Тест бази даних ===")
    try:
        from db_manager import DatabaseManager

        db = DatabaseManager('assistant.db')

        # Тест завантаження всіх додатків
        start = time.time()
        apps = db.load_apps()
        load_time = time.time() - start
        print(f"✓ Завантаження {len(apps)} додатків: {load_time*1000:.2f} мс")

        # Тест кешованого пошуку
        start = time.time()
        for _ in range(100):
            db.get_exe_by_canonical("chrome")
        cache_time = time.time() - start
        print(f"✓ 100 кешованих запитів: {cache_time*1000:.2f} мс ({cache_time*10:.2f} мс/запит)")

        # Тест статистики
        start = time.time()
        stats = db.get_counts()
        stats_time = time.time() - start
        print(f"✓ Статистика БД: {stats_time*1000:.2f} мс")
        print(f"  Всього додатків: {stats['total']}")

        return True
    except Exception as e:
        print(f"✗ Помилка: {e}")
        return False

def test_ai_cache():
    """Тест кешування AI"""
    print("\n=== Тест AI кешування ===")
    try:
        from ai_brain import brain

        test_query = "котра година"

        # Перший запит (без кешу)
        start = time.time()
        response1 = brain.ask(test_query)
        first_time = time.time() - start
        print(f"✓ Перший запит: {first_time*1000:.2f} мс")

        # Другий запит (з кешу)
        start = time.time()
        response2 = brain.ask(test_query)
        cache_time = time.time() - start
        print(f"✓ Кешований запит: {cache_time*1000:.2f} мс")

        speedup = first_time / cache_time if cache_time > 0 else 0
        print(f"✓ Прискорення: {speedup:.1f}x")

        return True
    except Exception as e:
        print(f"✗ Помилка: {e}")
        return False

def test_whisper_model():
    """Тест завантаження Whisper моделі"""
    print("\n=== Тест Whisper моделі ===")
    try:
        from asr_whisper import get_model, warmup

        # Тест warmup
        start = time.time()
        warmup()
        warmup_time = time.time() - start
        print(f"✓ Warmup моделі: {warmup_time:.2f} сек")

        # Тест повторного отримання (має бути миттєво)
        start = time.time()
        model = get_model()
        get_time = time.time() - start
        print(f"✓ Повторне отримання: {get_time*1000:.2f} мс")

        return True
    except Exception as e:
        print(f"✗ Помилка: {e}")
        return False

def test_smart_home_cache():
    """Тест кешування розумного дому"""
    print("\n=== Тест Smart Home кешування ===")
    try:
        from smart_home import home

        # Тест кешованого пошуку пристрою
        start = time.time()
        for _ in range(100):
            device_id, name = home._find_device("лампа")
        cache_time = time.time() - start
        print(f"✓ 100 кешованих пошуків: {cache_time*1000:.2f} мс ({cache_time*10:.2f} мс/пошук)")

        return True
    except Exception as e:
        print(f"✗ Помилка: {e}")
        return False

def print_summary(results):
    """Виведення підсумків"""
    print("\n" + "="*50)
    print("ПІДСУМОК ТЕСТІВ")
    print("="*50)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    print("="*50)
    print(f"Пройдено: {passed}/{total} ({passed/total*100:.0f}%)")
    print("="*50)

def main():
    print("="*50)
    print("ТЕСТУВАННЯ ПРОДУКТИВНОСТІ AIVA")
    print("="*50)

    results = {
        "База даних": test_database_performance(),
        "AI кешування": test_ai_cache(),
        "Whisper модель": test_whisper_model(),
        "Smart Home кеш": test_smart_home_cache()
    }

    print_summary(results)

if __name__ == "__main__":
    main()
