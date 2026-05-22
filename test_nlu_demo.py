"""
Демонстрація можливостей покращеного NLU Engine
"""
import sys
import os

# Виправлення кодування для Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'src')

from nlu_engine import nlu_engine
from context_manager import ContextManager
from entity_extractors import DateExtractor, RangeExtractor, MultipleItemsExtractor

print("=" * 60)
print("AIVA NLU Engine - Демонстрація")
print("=" * 60)

# Створюємо контекст
ctx = ContextManager(db_path="data/demo_context.db")
session = ctx.create_session("demo_user")
session_id = session.session_id

print(f"\nОК Створено сесію: {session_id}\n")

# ============= Тест 1: Проста команда =============
print("Тест 1: Проста команда")
print("-" * 60)

result = nlu_engine.analyze("запусти chrome", session_id=session_id)
print(f"Команда: 'запусти chrome'")
print(f"  Intent: {result.intent}")
print(f"  Confidence: {result.confidence:.2f}")
print(f"  Method: {result.method}")
print(f"  Entities: {result.entities}")

# Зберігаємо в контекст
ctx.add_message(
    session_id, "user", "запусти chrome",
    intent=result.intent, entities=result.entities, confidence=result.confidence
)

# ============= Тест 2: Контекстне продовження =============
print("\n> Тест 2: Контекстне продовження")
print("-" * 60)

result = nlu_engine.analyze("і firefox теж", session_id=session_id)
print(f"Команда: 'і firefox теж'")
print(f"  Intent: {result.intent}")
print(f"  Confidence: {result.confidence:.2f}")
print(f"  Method: {result.method} ← Виведено з контексту!")
print(f"  Entities: {result.entities}")

ctx.add_message(
    session_id, "user", "і firefox теж",
    intent=result.intent, entities=result.entities, confidence=result.confidence
)

# ============= Тест 3: Множинні об'єкти =============
print("\n> Тест 3: Множинні об'єкти")
print("-" * 60)

result = nlu_engine.analyze("запусти chrome і firefox і telegram", session_id=session_id)
print(f"Команда: 'запусти chrome і firefox і telegram'")
print(f"  Intent: {result.intent}")
print(f"  Entities: {result.entities}")
if result.entities.get("multiple"):
    print(f"  * Виявлено множинні програми: {result.entities.get('apps')}")

# ============= Тест 4: Дати =============
print("\n> Тест 4: Витягування дат")
print("-" * 60)

test_dates = [
    "погода завтра",
    "нагадай мені через 3 дні",
    "зустріч 15 травня"
]

for cmd in test_dates:
    result = nlu_engine.analyze(cmd, session_id=session_id)
    print(f"Команда: '{cmd}'")
    print(f"  Date: {result.entities.get('date', 'не знайдено')}")

# ============= Тест 5: Діапазони =============
print("\n> Тест 5: Витягування діапазонів")
print("-" * 60)

result = nlu_engine.analyze("гучність від 50 до 75", session_id=session_id)
print(f"Команда: 'гучність від 50 до 75'")
print(f"  Intent: {result.intent}")
print(f"  Range: {result.entities.get('range')}")

# ============= Тест 6: Розв'язування entities з контексту =============
print("\n> Тест 6: Розв'язування entities з контексту")
print("-" * 60)

# Перша команда з містом
result1 = nlu_engine.analyze("погода у києві", session_id=session_id)
print(f"Команда 1: 'погода у києві'")
print(f"  City: {result1.entities.get('city')}")

ctx.add_message(
    session_id, "user", "погода у києві",
    intent=result1.intent, entities=result1.entities, confidence=result1.confidence
)

# Друга команда без міста
result2 = nlu_engine.analyze("а завтра?", session_id=session_id)
print(f"\nКоманда 2: 'а завтра?'")
print(f"  City: {result2.entities.get('city')} ← Взято з контексту!")
print(f"  Date: {result2.entities.get('date')}")

# ============= Тест 7: Статистика =============
print("\n= Статистика NLU Engine")
print("-" * 60)

stats = nlu_engine.get_stats()
print(f"Всього команд: {stats['total']}")
print(f"Rule-based: {stats['rule']} ({stats['rule_percentage']:.1f}%)")
print(f"LLM-based: {stats['llm']} ({stats['llm_percentage']:.1f}%)")
print(f"Context-based: {stats['context']} ({stats['context_percentage']:.1f}%)")
print(f"Середній час (rule): {stats['avg_rule_time_ms']:.1f}ms")

# ============= Тест 8: Контекст діалогу =============
print("\n> Контекст діалогу")
print("-" * 60)

nlu_context = ctx.get_nlu_context(session_id)
print(f"Останній intent: {nlu_context['last_intent']}")
print(f"Активні entities: {nlu_context['active_entities']}")
print(f"Останні intents: {nlu_context['recent_intents']}")

pattern = ctx.detect_pattern(session_id)
if pattern:
    print(f"\n> Виявлено паттерн:")
    print(f"  Тип: {pattern['type']}")
    print(f"  Деталі: {pattern.get('suggestion', pattern)}")

print("\n" + "=" * 60)
print("OK Демонстрація завершена!")
print("=" * 60)
