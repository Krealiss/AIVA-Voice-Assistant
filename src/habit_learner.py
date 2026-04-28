"""
Habit Learner - ML-система для виявлення та навчання на звичках користувача
Використовує pattern recognition, preference learning, adaptive responses
"""
import logging
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

logger = logging.getLogger("habit_learner")

@dataclass
class Habit:
    """Виявлена звичка користувача"""
    habit_id: Optional[int]
    habit_type: str  # "routine", "preference", "trigger"
    description: str
    trigger_condition: Dict  # Умова спрацювання
    suggested_action: str
    confidence: float  # 0.0 - 1.0
    times_observed: int
    times_accepted: int
    times_rejected: int
    last_triggered: Optional[datetime]
    created_at: datetime
    active: bool = True

@dataclass
class UserPreference:
    """Вподобання користувача"""
    preference_type: str  # "app", "time", "sequence", "device"
    key: str
    value: str
    confidence: float
    learned_from: int  # Кількість спостережень

class HabitLearner:
    """Система навчання на звичках"""

    def __init__(self, db_path: str = "data/habits.db", analytics_db: str = "data/analytics.db"):
        self.db_path = db_path
        self.analytics_db = analytics_db
        self._init_db()

    def _init_db(self):
        """Ініціалізація БД для звичок"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        # Таблиця звичок
        conn.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_type TEXT NOT NULL,
                description TEXT NOT NULL,
                trigger_condition TEXT NOT NULL,
                suggested_action TEXT NOT NULL,
                confidence REAL NOT NULL,
                times_observed INTEGER DEFAULT 0,
                times_accepted INTEGER DEFAULT 0,
                times_rejected INTEGER DEFAULT 0,
                last_triggered TEXT,
                created_at TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)

        # Таблиця вподобань
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL NOT NULL,
                learned_from INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(preference_type, key)
            )
        """)

        # Таблиця історії взаємодій зі звичками
        conn.execute("""
            CREATE TABLE IF NOT EXISTS habit_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                action TEXT NOT NULL,  -- "accepted", "rejected", "ignored"
                timestamp TEXT NOT NULL,
                FOREIGN KEY (habit_id) REFERENCES habits(id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Habit Learner DB initialized")

    def learn_from_analytics(self):
        """Навчання на основі даних з analytics"""
        logger.info("Learning from analytics data...")

        # Підключаємося до analytics DB
        conn = sqlite3.connect(self.analytics_db)
        cur = conn.cursor()

        # Отримуємо дані за останні 14 днів
        since = (datetime.now() - timedelta(days=14)).isoformat()
        rows = cur.execute("""
            SELECT command, intent_type, timestamp, source
            FROM command_metrics
            WHERE timestamp > ? AND success = 1
            ORDER BY timestamp
        """, (since,)).fetchall()

        conn.close()

        if len(rows) < 5:
            logger.info("Not enough data for learning")
            return

        # Аналізуємо рутини (команди в певний час)
        self._learn_time_routines(rows)

        # Аналізуємо послідовності (команда A → команда B)
        self._learn_sequences(rows)

        # Аналізуємо вподобання (улюблені програми)
        self._learn_preferences(rows)

        logger.info("Learning completed")

    def _learn_time_routines(self, rows: List[Tuple]):
        """Виявлення рутин за часом"""
        # Групуємо команди по годинах
        hour_commands = defaultdict(list)

        for command, intent, timestamp, source in rows:
            ts = datetime.fromisoformat(timestamp)
            hour = ts.hour
            hour_commands[hour].append((command, intent))

        # Шукаємо стабільні рутини (команда в певну годину 3+ рази)
        for hour, commands in hour_commands.items():
            command_counts = defaultdict(int)
            for cmd, _ in commands:
                command_counts[cmd] += 1

            for command, count in command_counts.items():
                if count >= 3:
                    # Перевіряємо, чи вже є така звичка
                    existing = self._find_habit("routine", {"hour": hour, "command": command})

                    if existing:
                        # Оновлюємо існуючу
                        self._update_habit_confidence(existing.habit_id, count)
                    else:
                        # Створюємо нову
                        habit = Habit(
                            habit_id=None,
                            habit_type="routine",
                            description=f"Зазвичай о {hour}:00 ти виконуєш '{command}'",
                            trigger_condition={"hour": hour, "command": command},
                            suggested_action=command,
                            confidence=min(count / 10, 0.9),
                            times_observed=count,
                            times_accepted=0,
                            times_rejected=0,
                            last_triggered=None,
                            created_at=datetime.now()
                        )
                        self._save_habit(habit)

    def _learn_sequences(self, rows: List[Tuple]):
        """Виявлення послідовностей команд"""
        if len(rows) < 2:
            return

        sequences = []
        for i in range(len(rows) - 1):
            cmd1, _, ts1, _ = rows[i]
            cmd2, _, ts2, _ = rows[i + 1]

            t1 = datetime.fromisoformat(ts1)
            t2 = datetime.fromisoformat(ts2)

            # Якщо команди в межах 5 хвилин
            if abs((t2 - t1).total_seconds()) < 300:
                sequences.append((cmd1, cmd2))

        # Підраховуємо частоту
        sequence_counts = defaultdict(int)
        for seq in sequences:
            sequence_counts[seq] += 1

        # Зберігаємо стабільні послідовності (3+ рази)
        for (cmd1, cmd2), count in sequence_counts.items():
            if count >= 3:
                existing = self._find_habit("trigger", {"first": cmd1, "second": cmd2})

                if existing:
                    self._update_habit_confidence(existing.habit_id, count)
                else:
                    habit = Habit(
                        habit_id=None,
                        habit_type="trigger",
                        description=f"Після '{cmd1}' ти часто виконуєш '{cmd2}'",
                        trigger_condition={"first": cmd1, "second": cmd2},
                        suggested_action=cmd2,
                        confidence=min(count / 10, 0.9),
                        times_observed=count,
                        times_accepted=0,
                        times_rejected=0,
                        last_triggered=None,
                        created_at=datetime.now()
                    )
                    self._save_habit(habit)

    def _learn_preferences(self, rows: List[Tuple]):
        """Виявлення вподобань (улюблені програми, час активності)"""
        command_counts = defaultdict(int)

        for command, intent, _, _ in rows:
            if intent == "run":  # Тільки запуск програм
                command_counts[command] += 1

        # Топ-5 програм
        top_apps = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        for app, count in top_apps:
            if count >= 5:
                self._save_preference(UserPreference(
                    preference_type="favorite_app",
                    key=app,
                    value=str(count),
                    confidence=min(count / 20, 1.0),
                    learned_from=count
                ))

    def _find_habit(self, habit_type: str, trigger: Dict) -> Optional[Habit]:
        """Знайти існуючу звичку"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        rows = cur.execute("""
            SELECT id, habit_type, description, trigger_condition, suggested_action,
                   confidence, times_observed, times_accepted, times_rejected,
                   last_triggered, created_at, active
            FROM habits
            WHERE habit_type = ? AND active = 1
        """, (habit_type,)).fetchall()

        conn.close()

        for row in rows:
            stored_trigger = json.loads(row[3])
            if stored_trigger == trigger:
                return Habit(
                    habit_id=row[0],
                    habit_type=row[1],
                    description=row[2],
                    trigger_condition=stored_trigger,
                    suggested_action=row[4],
                    confidence=row[5],
                    times_observed=row[6],
                    times_accepted=row[7],
                    times_rejected=row[8],
                    last_triggered=datetime.fromisoformat(row[9]) if row[9] else None,
                    created_at=datetime.fromisoformat(row[10]),
                    active=bool(row[11])
                )

        return None

    def _save_habit(self, habit: Habit):
        """Зберегти нову звичку"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO habits
            (habit_type, description, trigger_condition, suggested_action,
             confidence, times_observed, times_accepted, times_rejected,
             last_triggered, created_at, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            habit.habit_type,
            habit.description,
            json.dumps(habit.trigger_condition),
            habit.suggested_action,
            habit.confidence,
            habit.times_observed,
            habit.times_accepted,
            habit.times_rejected,
            habit.last_triggered.isoformat() if habit.last_triggered else None,
            habit.created_at.isoformat(),
            1 if habit.active else 0
        ))
        conn.commit()
        conn.close()
        logger.info(f"Saved new habit: {habit.description}")

    def _update_habit_confidence(self, habit_id: int, new_observations: int):
        """Оновити впевненість у звичці"""
        conn = sqlite3.connect(self.db_path)

        # Отримуємо поточні дані
        row = conn.execute(
            "SELECT times_observed, confidence FROM habits WHERE id = ?",
            (habit_id,)
        ).fetchone()

        if row:
            old_obs, old_conf = row
            new_total = old_obs + new_observations
            # Збільшуємо впевненість, але не більше 0.95
            new_conf = min(old_conf + 0.05, 0.95)

            conn.execute("""
                UPDATE habits
                SET times_observed = ?, confidence = ?
                WHERE id = ?
            """, (new_total, new_conf, habit_id))

            conn.commit()

        conn.close()

    def _save_preference(self, pref: UserPreference):
        """Зберегти вподобання"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO preferences
            (preference_type, key, value, confidence, learned_from, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pref.preference_type,
            pref.key,
            pref.value,
            pref.confidence,
            pref.learned_from,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_active_habits(self, min_confidence: float = 0.5) -> List[Habit]:
        """Отримати активні звички з достатньою впевненістю"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        rows = cur.execute("""
            SELECT id, habit_type, description, trigger_condition, suggested_action,
                   confidence, times_observed, times_accepted, times_rejected,
                   last_triggered, created_at, active
            FROM habits
            WHERE active = 1 AND confidence >= ?
            ORDER BY confidence DESC
        """, (min_confidence,)).fetchall()

        conn.close()

        habits = []
        for row in rows:
            habits.append(Habit(
                habit_id=row[0],
                habit_type=row[1],
                description=row[2],
                trigger_condition=json.loads(row[3]),
                suggested_action=row[4],
                confidence=row[5],
                times_observed=row[6],
                times_accepted=row[7],
                times_rejected=row[8],
                last_triggered=datetime.fromisoformat(row[9]) if row[9] else None,
                created_at=datetime.fromisoformat(row[10]),
                active=bool(row[11])
            ))

        return habits

    def check_triggers(self, context: Dict) -> List[Habit]:
        """Перевірити, чи спрацювали якісь тригери"""
        habits = self.get_active_habits()
        triggered = []

        current_hour = datetime.now().hour
        last_command = context.get("last_command")

        for habit in habits:
            trigger = habit.trigger_condition

            # Перевірка рутини за часом
            if habit.habit_type == "routine":
                if trigger.get("hour") == current_hour:
                    # Перевіряємо, чи не спрацьовувала вже сьогодні
                    if not habit.last_triggered or \
                       (datetime.now() - habit.last_triggered).days >= 1:
                        triggered.append(habit)

            # Перевірка послідовності
            elif habit.habit_type == "trigger":
                if trigger.get("first") == last_command:
                    triggered.append(habit)

        return triggered

    def record_interaction(self, habit_id: int, action: str):
        """Записати взаємодію зі звичкою (accepted/rejected/ignored)"""
        conn = sqlite3.connect(self.db_path)

        # Записуємо взаємодію
        conn.execute("""
            INSERT INTO habit_interactions (habit_id, action, timestamp)
            VALUES (?, ?, ?)
        """, (habit_id, action, datetime.now().isoformat()))

        # Оновлюємо лічильники
        if action == "accepted":
            conn.execute("""
                UPDATE habits
                SET times_accepted = times_accepted + 1,
                    last_triggered = ?,
                    confidence = MIN(confidence + 0.05, 0.98)
                WHERE id = ?
            """, (datetime.now().isoformat(), habit_id))

        elif action == "rejected":
            conn.execute("""
                UPDATE habits
                SET times_rejected = times_rejected + 1,
                    confidence = MAX(confidence - 0.1, 0.1)
                WHERE id = ?
            """, (habit_id,))

            # Якщо відхилено 3+ рази - деактивуємо
            row = conn.execute(
                "SELECT times_rejected FROM habits WHERE id = ?",
                (habit_id,)
            ).fetchone()

            if row and row[0] >= 3:
                conn.execute("UPDATE habits SET active = 0 WHERE id = ?", (habit_id,))
                logger.info(f"Deactivated habit {habit_id} due to rejections")

        conn.commit()
        conn.close()

    def get_preferences(self, preference_type: Optional[str] = None) -> List[UserPreference]:
        """Отримати вподобання користувача"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        if preference_type:
            rows = cur.execute("""
                SELECT preference_type, key, value, confidence, learned_from
                FROM preferences
                WHERE preference_type = ?
                ORDER BY confidence DESC
            """, (preference_type,)).fetchall()
        else:
            rows = cur.execute("""
                SELECT preference_type, key, value, confidence, learned_from
                FROM preferences
                ORDER BY confidence DESC
            """).fetchall()

        conn.close()

        return [
            UserPreference(
                preference_type=row[0],
                key=row[1],
                value=row[2],
                confidence=row[3],
                learned_from=row[4]
            )
            for row in rows
        ]

    def get_suggestion(self, context: Dict) -> Optional[str]:
        """Отримати пропозицію на основі контексту"""
        triggered = self.check_triggers(context)

        if not triggered:
            return None

        # Беремо звичку з найвищою впевненістю
        best_habit = max(triggered, key=lambda h: h.confidence)

        # Формуємо пропозицію
        if best_habit.habit_type == "routine":
            return f"Зазвичай в цей час ти {best_habit.suggested_action}. Хочеш?"

        elif best_habit.habit_type == "trigger":
            return f"Може також {best_habit.suggested_action}?"

        return None

# Глобальний екземпляр
habit_learner = HabitLearner()
