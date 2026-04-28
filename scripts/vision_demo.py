"""
Quick Vision Demo
Демонстрація можливостей Vision системи
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')

from vision_module import vision
import time

print("AIVA Vision Demo")
print("=" * 60)
print()

# Demo 1: Screenshot
print("Demo 1: Screenshot Capture")
print("-" * 60)
print("Taking screenshot in 3 seconds...")
print("Switch to the window you want to capture!")
print()

for i in range(3, 0, -1):
    print(f"   {i}...")
    time.sleep(1)

screenshot = vision.capture_screenshot()
if screenshot:
    print(f"[OK] Screenshot saved: {screenshot}")
else:
    print("[ERROR] Screenshot failed")
    sys.exit(1)

print()

# Demo 2: Screen Description
print("Demo 2: Screen Description")
print("-" * 60)

result = vision.describe_screen(
    prompt="Опиши що на екрані. Які програми відкриті? Що робить користувач?"
)

if result.get("ok"):
    print("[OK] Analysis complete!")
    print()

    if result.get("description"):
        print("Description:")
        print(result["description"])
        print()

    if result.get("ocr_text"):
        print("Extracted text (first 200 chars):")
        print(result["ocr_text"][:200])
        print()
else:
    print("[ERROR] Analysis failed")
    print(f"Error: {result.get('error')}")

print()

# Demo 3: Find Element
print("Demo 3: Find UI Element")
print("-" * 60)
print("Looking for 'Start' button...")

result = vision.find_ui_element("кнопка Start або меню Пуск")

if result.get("ok"):
    print("[OK] Search complete!")
    print()
    print("Result:")
    print(result.get("found", "Not found"))
else:
    print("[ERROR] Search failed")

print()

# Demo 4: Error Detection
print("Demo 4: Error Detection")
print("-" * 60)
print("Checking for errors on screen...")

result = vision.detect_errors()

if result.get("ok"):
    print("[OK] Check complete!")
    print()

    if result.get("has_errors"):
        print("[WARNING] Errors detected:")
        print(result.get("analysis"))
    else:
        print("[OK] No errors detected")
else:
    print("[ERROR] Check failed")

print()

# Demo 5: Active Window
print("Demo 5: Active Window Info")
print("-" * 60)

result = vision.get_active_window_info()

if result.get("ok"):
    print("[OK] Info retrieved!")
    print()
    print("Active window:")
    print(result.get("info"))
else:
    print("[ERROR] Failed to get info")

print()
print("=" * 60)
print("Demo Complete!")
print()
print("All screenshots saved to: data/screenshots/")
print()
