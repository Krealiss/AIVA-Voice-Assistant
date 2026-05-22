"""
Тест Tesseract OCR
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 70)
print("ТЕСТ TESSERACT OCR")
print("=" * 70)

# Тест 1: Перевірка pytesseract
print("\n[ТЕСТ 1] Перевірка pytesseract")
print("-" * 70)
try:
    import pytesseract
    print(f"[OK] pytesseract імпортовано")
    print(f"[OK] Tesseract CMD: {pytesseract.pytesseract.tesseract_cmd}")
except Exception as e:
    print(f"[FAIL] Помилка: {e}")
    sys.exit(1)

# Тест 2: Перевірка Tesseract версії
print("\n[ТЕСТ 2] Перевірка Tesseract версії")
print("-" * 70)
try:
    version = pytesseract.get_tesseract_version()
    print(f"[OK] Tesseract версія: {version}")
except Exception as e:
    print(f"[FAIL] Помилка: {e}")
    import traceback
    traceback.print_exc()

# Тест 3: Перевірка vision_module
print("\n[ТЕСТ 3] Перевірка vision_module")
print("-" * 70)
try:
    from vision_module import vision, OCR_AVAILABLE

    print(f"[OK] vision_module імпортовано")
    print(f"[OK] OCR_AVAILABLE: {OCR_AVAILABLE}")

    if not OCR_AVAILABLE:
        print(f"[FAIL] OCR не доступний")
        sys.exit(1)

except Exception as e:
    print(f"[FAIL] Помилка: {e}")
    import traceback
    traceback.print_exc()

# Тест 4: Тест OCR на простому зображенні
print("\n[ТЕСТ 4] Тест OCR на зображенні")
print("-" * 70)
try:
    from PIL import Image, ImageDraw, ImageFont
    import tempfile
    from pathlib import Path

    # Створюємо просте зображення з текстом
    img = Image.new('RGB', (400, 100), color='white')
    draw = ImageDraw.Draw(img)

    # Малюємо текст (без шрифту, використовуємо default)
    draw.text((10, 30), "Hello World 123", fill='black')

    # Зберігаємо
    test_path = Path(tempfile.gettempdir()) / "test_ocr.png"
    img.save(test_path)
    print(f"[OK] Тестове зображення створено: {test_path}")

    # OCR
    text = vision.extract_text_ocr(str(test_path))
    print(f"[OK] OCR виконано")
    print(f"     Розпізнаний текст: '{text.strip()}'")

    # Очищення
    test_path.unlink()

    if text.strip():
        print(f"[OK] OCR працює!")
    else:
        print(f"[WARNING] OCR не розпізнав текст (можливо проблема зі шрифтом)")

except Exception as e:
    print(f"[FAIL] Помилка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("ТЕСТУВАННЯ ЗАВЕРШЕНО")
print("=" * 70)
