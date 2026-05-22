"""
Міграція БД context.db для додавання NLU полів
"""
import sqlite3
import os

DB_PATH = "data/context.db"

print("=" * 60)
print("Міграція БД для NLU")
print("=" * 60)

if not os.path.exists(DB_PATH):
    print(f"\nБД не знайдена: {DB_PATH}")
    print("Нова БД буде створена автоматично при першому запуску")
    exit(0)

print(f"\nЗнайдено БД: {DB_PATH}")

# Підключаємось до БД
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Перевіряємо чи є колонки
cursor.execute("PRAGMA table_info(messages)")
columns = [row[1] for row in cursor.fetchall()]

print(f"Поточні колонки: {columns}")

# Додаємо нові колонки якщо їх немає
new_columns = {
    "intent": "TEXT",
    "entities_json": "TEXT DEFAULT '{}'",
    "confidence": "REAL"
}

added = []
for col_name, col_type in new_columns.items():
    if col_name not in columns:
        try:
            cursor.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}")
            added.append(col_name)
            print(f"OK: Додано колонку '{col_name}'")
        except Exception as e:
            print(f"ПОМИЛКА: Не вдалося додати '{col_name}': {e}")
    else:
        print(f"SKIP: Колонка '{col_name}' вже існує")

conn.commit()
conn.close()

if added:
    print(f"\nУспішно додано {len(added)} колонок: {', '.join(added)}")
else:
    print("\nВсі колонки вже існують, міграція не потрібна")

print("\n" + "=" * 60)
print("Міграція завершена!")
print("=" * 60)
