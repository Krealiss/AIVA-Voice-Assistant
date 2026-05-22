"""
Тест оптимізованого Vision
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pathlib import Path
from PIL import Image

print("=" * 70)
print("ТЕСТ ОПТИМІЗОВАНОГО VISION")
print("=" * 70)

# Тест 1: Перевірка параметрів стиснення
print("\n[ТЕСТ 1] Параметри стиснення")
print("-" * 70)
try:
    from vision_module import vision
    import inspect

    source = inspect.getsource(vision._compress_image)

    # Перевірка нових параметрів
    assert "800, 600" in source, "Розмір не змінено на 800x600"
    assert "quality: int = 60" in source, "Якість не змінено на 60"
    print(f"[OK] Розмір: 800x600")
    print(f"[OK] Якість: 60%")

except Exception as e:
    print(f"[FAIL] Помилка: {e}")

# Тест 2: Перевірка retry та timeout
print("\n[ТЕСТ 2] Retry та timeout")
print("-" * 70)
try:
    source = inspect.getsource(vision.analyze_with_vision_api)

    assert "max_retries = 1" in source, "Retry не змінено на 1"
    assert "timeout = 120" in source, "Timeout не змінено на 120s"
    print(f"[OK] Max retries: 1")
    print(f"[OK] Timeout: 120s")

except Exception as e:
    print(f"[FAIL] Помилка: {e}")

# Тест 3: Тест стиснення
print("\n[ТЕСТ 3] Тест стиснення")
print("-" * 70)
try:
    # Створюємо велике зображення
    test_img = Image.new('RGB', (1920, 1080), color='blue')
    test_path = Path("data/screenshots/test_compress.png")
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_img.save(test_path)

    original_size = test_path.stat().st_size
    print(f"[OK] Оригінал: {original_size / 1024:.1f} KB, {test_img.size}")

    # Стискаємо
    compressed_path = vision._compress_image(str(test_path))
    compressed_size = Path(compressed_path).stat().st_size
    compressed_img = Image.open(compressed_path)

    print(f"[OK] Стиснене: {compressed_size / 1024:.1f} KB, {compressed_img.size}")
    print(f"[OK] Економія: {(1 - compressed_size/original_size)*100:.1f}%")

    # Перевірка розміру
    assert compressed_img.size[0] <= 800, f"Ширина {compressed_img.size[0]} > 800"
    assert compressed_img.size[1] <= 600, f"Висота {compressed_img.size[1]} > 600"
    print(f"[OK] Розміри коректні")

    # Очищення
    test_path.unlink()
    Path(compressed_path).unlink()

except Exception as e:
    print(f"[FAIL] Помилка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("ПІДСУМОК")
print("=" * 70)
print("""
✅ Оптимізація Vision:
- Розмір: 1280x720 → 800x600 (менше даних)
- Якість: 75% → 60% (менший файл)
- Retry: 3 → 1 (швидше при помилках)
- Timeout: 180s → 120s (менше очікування)

Очікуваний результат:
- Розмір файлу: ~30-50 KB (було ~170 KB)
- Швидкість: ~60-90 секунд (було 180+ секунд)
- Fallback на OCR: <1 секунда

Vision оптимізовано для швидкості!
""")
