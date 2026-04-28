"""
Vision System Test Script
Тестує всі можливості Vision модуля
"""
import sys
import os

# Додаємо src до шляху
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("=" * 60)
print("AIVA Vision System Test")
print("=" * 60)
print()

# Перевірка залежностей
print("[1/6] Checking dependencies...")
print()

dependencies = {
    "PIL (Pillow)": False,
    "pytesseract": False,
    "anthropic": False
}

try:
    from PIL import Image, ImageGrab
    dependencies["PIL (Pillow)"] = True
    print("✅ PIL (Pillow) - OK")
except ImportError:
    print("❌ PIL (Pillow) - NOT INSTALLED")
    print("   Install: pip install Pillow")

try:
    import pytesseract
    dependencies["pytesseract"] = True
    print("✅ pytesseract - OK")
except ImportError:
    print("❌ pytesseract - NOT INSTALLED")
    print("   Install: pip install pytesseract")
    print("   Also install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")

try:
    import anthropic
    dependencies["anthropic"] = True
    print("✅ anthropic - OK")
except ImportError:
    print("❌ anthropic - NOT INSTALLED")
    print("   Install: pip install anthropic")

print()

# Перевірка API ключа
print("[2/6] Checking API key...")
print()

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    print(f"✅ ANTHROPIC_API_KEY found: {api_key[:20]}...")
else:
    print("❌ ANTHROPIC_API_KEY not found in .env")
    print("   Add to .env: ANTHROPIC_API_KEY=sk-ant-...")

print()

# Імпорт vision модуля
print("[3/6] Loading vision module...")
print()

try:
    from vision_module import vision
    print("✅ Vision module loaded")
except Exception as e:
    print(f"❌ Failed to load vision module: {e}")
    sys.exit(1)

print()

# Тест 1: Screenshot
print("[4/6] Testing screenshot capture...")
print()

if dependencies["PIL (Pillow)"]:
    try:
        screenshot_path = vision.capture_screenshot(save=True)
        if screenshot_path:
            print(f"✅ Screenshot captured: {screenshot_path}")
            print(f"   File size: {os.path.getsize(screenshot_path) / 1024:.1f} KB")
        else:
            print("❌ Screenshot capture failed")
    except Exception as e:
        print(f"❌ Screenshot error: {e}")
else:
    print("⏭️  Skipped (PIL not installed)")

print()

# Тест 2: OCR
print("[5/6] Testing OCR (text extraction)...")
print()

if dependencies["PIL (Pillow)"] and dependencies["pytesseract"]:
    try:
        if screenshot_path:
            text = vision.extract_text_ocr(screenshot_path)
            if text:
                print(f"✅ OCR successful")
                print(f"   Extracted {len(text)} characters")
                print(f"   Preview: {text[:100]}...")
            else:
                print("⚠️  No text found on screen")
    except Exception as e:
        print(f"❌ OCR error: {e}")
else:
    print("⏭️  Skipped (dependencies not installed)")

print()

# Тест 3: Vision API
print("[6/6] Testing Vision API (Claude)...")
print()

if dependencies["anthropic"] and api_key:
    try:
        if screenshot_path:
            print("   Analyzing screenshot with Claude Vision...")
            result = vision.analyze_with_vision_api(
                screenshot_path,
                "Опиши що на цьому зображенні в 2-3 реченнях."
            )
            if result:
                print(f"✅ Vision API successful")
                print(f"   Response: {result[:200]}...")
            else:
                print("❌ Vision API returned no result")
    except Exception as e:
        print(f"❌ Vision API error: {e}")
else:
    print("⏭️  Skipped (anthropic not installed or API key missing)")

print()

# Підсумок
print("=" * 60)
print("Test Summary")
print("=" * 60)
print()

total_deps = len(dependencies)
installed_deps = sum(dependencies.values())

print(f"Dependencies: {installed_deps}/{total_deps} installed")
for dep, status in dependencies.items():
    status_icon = "✅" if status else "❌"
    print(f"  {status_icon} {dep}")

print()

if api_key:
    print("✅ API Key configured")
else:
    print("❌ API Key missing")

print()

# Рекомендації
if installed_deps < total_deps or not api_key:
    print("📝 Next steps:")
    print()

    if not dependencies["PIL (Pillow)"]:
        print("1. Install Pillow:")
        print("   pip install Pillow")
        print()

    if not dependencies["pytesseract"]:
        print("2. Install pytesseract:")
        print("   pip install pytesseract")
        print("   Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
        print()

    if not dependencies["anthropic"]:
        print("3. Install anthropic:")
        print("   pip install anthropic")
        print()

    if not api_key:
        print("4. Add API key to .env:")
        print("   ANTHROPIC_API_KEY=sk-ant-...")
        print("   Get key: https://console.anthropic.com/")
        print()
else:
    print("🎉 All dependencies installed and configured!")
    print("   Vision system is ready to use.")
    print()
    print("Try it:")
    print("  python src/agent_main.py")
    print("  curl -X POST http://127.0.0.1:8787/api/vision/describe")

print()
print("=" * 60)
