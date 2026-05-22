"""
Тест інтеграції NLU в agent_main.py
"""
import sys
sys.path.insert(0, 'src')

print("=" * 60)
print("Тест інтеграції NLU в agent_main")
print("=" * 60)

# Імпортуємо handle_intent
try:
    from agent_main import handle_intent
    print("\nOK: handle_intent імпортовано успішно")
except Exception as e:
    print(f"\nПОМИЛКА: Не вдалося імпортувати handle_intent: {e}")
    sys.exit(1)

# Тест 1: Проста команда
print("\n" + "-" * 60)
print("Тест 1: Проста команда з user_id")
print("-" * 60)

try:
    result = handle_intent("запусти chrome", source="test", user_id="test_user_1")
    if result:
        print(f"OK: Команда оброблена")
        print(f"  Intent виконано: {result.get('ok')}")
        print(f"  Відповідь: {result.get('text')}")
    else:
        print("ПОМИЛКА: Команда не оброблена")
except Exception as e:
    print(f"ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()

# Тест 2: Контекстна команда
print("\n" + "-" * 60)
print("Тест 2: Контекстна команда (той самий user)")
print("-" * 60)

try:
    result = handle_intent("і firefox теж", source="test", user_id="test_user_1")
    if result:
        print(f"OK: Команда оброблена")
        print(f"  Intent виконано: {result.get('ok')}")
        print(f"  Відповідь: {result.get('text')}")
    else:
        print("УВАГА: Команда не оброблена (можливо потрібен Ollama)")
except Exception as e:
    print(f"ПОМИЛКА: {e}")

# Тест 3: Перевірка контексту
print("\n" + "-" * 60)
print("Тест 3: Перевірка збереження в контекст")
print("-" * 60)

try:
    from context_manager import context_manager

    # Отримуємо сесію
    session = context_manager.get_active_session("test_user_1")
    print(f"OK: Сесія знайдена: {session.session_id}")

    # Отримуємо історію
    history = context_manager.get_session_history(session.session_id, limit=5)
    print(f"OK: Історія містить {len(history)} повідомлень")

    for msg in history[-3:]:
        print(f"  - [{msg.role}] {msg.content[:50]}...")
        if msg.intent:
            print(f"    Intent: {msg.intent}, Entities: {msg.entities}")

    # Перевіряємо NLU контекст
    nlu_context = context_manager.get_nlu_context(session.session_id)
    print(f"\nNLU Context:")
    print(f"  Останній intent: {nlu_context.get('last_intent')}")
    print(f"  Активні entities: {nlu_context.get('active_entities')}")

except Exception as e:
    print(f"ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()

# Тест 4: Різні користувачі
print("\n" + "-" * 60)
print("Тест 4: Різні користувачі (ізольовані контексти)")
print("-" * 60)

try:
    result1 = handle_intent("погода у києві", source="test", user_id="user_A")
    result2 = handle_intent("погода у львові", source="test", user_id="user_B")

    print("OK: Команди від різних користувачів оброблені")

    # Перевіряємо що контексти ізольовані
    session_a = context_manager.get_active_session("user_A")
    session_b = context_manager.get_active_session("user_B")

    context_a = context_manager.get_nlu_context(session_a.session_id)
    context_b = context_manager.get_nlu_context(session_b.session_id)

    print(f"  User A entities: {context_a.get('active_entities')}")
    print(f"  User B entities: {context_b.get('active_entities')}")

    if context_a.get('active_entities') != context_b.get('active_entities'):
        print("OK: Контексти ізольовані правильно")
    else:
        print("УВАГА: Контексти можуть перетинатися")

except Exception as e:
    print(f"ПОМИЛКА: {e}")

print("\n" + "=" * 60)
print("Тестування завершено")
print("=" * 60)
