"""
Analytics Engine - система збору та аналізу метрик використання
Відстежує команди, success rate, performance, usage patterns
"""
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger("analytics")

@dataclass
class CommandMetric:
    """Метрика виконання команди"""
    command: str
    intent_type: str
    success: bool
    duration_ms: float
    timestamp: datetime
    source: str  # "voice", "telegram", "web"
    user_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class UsagePattern:
    """Патерн використання"""
    pattern_type: str  # "time_of_day", "sequence", "frequency"
    description: str
    confidence: float  # 0.0 - 1.0
    occurrences: int
    last_seen: datetime
    metadata: Dict

class AnalyticsEngine:
    """Система аналітики використання"""

    def __init__(self, db_path: str = "data/analytics.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ініціалізація БД для аналітики"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            # Таблиця метрик команд
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    intent_type TEXT,
                    success INTEGER NOT NULL,
                    duration_ms REAL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    user_id TEXT,
                    error TEXT
                )
            """)

            # Таблиця виявлених патернів
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    occurrences INTEGER NOT NULL,
                    last_seen TEXT NOT NULL,
                    metadata TEXT,
                    active INTEGER DEFAULT 1
                )
            """)

            # Індекси для швидкого пошуку
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON command_metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_intent ON command_metrics(intent_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_success ON command_metrics(success)")

            conn.commit()
        logger.info("Analytics DB initialized")

    def track_command(self, metric: CommandMetric):
        """Записати метрику виконання команди"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO command_metrics
                (command, intent_type, success, duration_ms, timestamp, source, user_id, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.command,
                metric.intent_type,
                1 if metric.success else 0,
                metric.duration_ms,
                metric.timestamp.isoformat(),
                metric.source,
                metric.user_id,
                metric.error
            ))
            conn.commit()

    def get_success_rate(self, hours: int = 24) -> Dict:
        """Отримати success rate за останні N годин"""
        since = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            # Загальна статистика
            total = cur.execute(
                "SELECT COUNT(*) FROM command_metrics WHERE timestamp > ?",
                (since.isoformat(),)
            ).fetchone()[0]

            successful = cur.execute(
                "SELECT COUNT(*) FROM command_metrics WHERE timestamp > ? AND success = 1",
                (since.isoformat(),)
            ).fetchone()[0]

            # По типах intent
            by_intent = cur.execute("""
                SELECT intent_type,
                       COUNT(*) as total,
                       SUM(success) as successful
                FROM command_metrics
                WHERE timestamp > ?
                GROUP BY intent_type
            """, (since.isoformat(),)).fetchall()

        return {
            "total_commands": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "by_intent": {
                intent: {
                    "total": t,
                    "successful": s,
                    "rate": (s / t * 100) if t > 0 else 0
                }
                for intent, t, s in by_intent
            }
        }

    def get_performance_stats(self, hours: int = 24) -> Dict:
        """Статистика продуктивності"""
        since = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            stats = cur.execute("""
                SELECT
                    AVG(duration_ms) as avg_duration,
                    MIN(duration_ms) as min_duration,
                    MAX(duration_ms) as max_duration,
                    COUNT(*) as total
                FROM command_metrics
                WHERE timestamp > ? AND duration_ms IS NOT NULL
            """, (since.isoformat(),)).fetchone()

            # По типах intent
            by_intent = cur.execute("""
                SELECT intent_type, AVG(duration_ms) as avg_duration
                FROM command_metrics
                WHERE timestamp > ? AND duration_ms IS NOT NULL
                GROUP BY intent_type
            """, (since.isoformat(),)).fetchall()

        return {
            "avg_duration_ms": stats[0] or 0,
            "min_duration_ms": stats[1] or 0,
            "max_duration_ms": stats[2] or 0,
            "total_commands": stats[3] or 0,
            "by_intent": {intent: avg for intent, avg in by_intent}
        }

    def get_top_commands(self, limit: int = 10, hours: int = 168) -> List[Tuple[str, int]]:
        """Топ команд за останній тиждень"""
        since = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            top = cur.execute("""
                SELECT command, COUNT(*) as count
                FROM command_metrics
                WHERE timestamp > ?
                GROUP BY command
                ORDER BY count DESC
                LIMIT ?
            """, (since.isoformat(), limit)).fetchall()

        return top

    def get_usage_by_hour(self, days: int = 7) -> Dict[int, int]:
        """Розподіл використання по годинах доби"""
        since = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            rows = cur.execute("""
                SELECT timestamp FROM command_metrics
                WHERE timestamp > ?
            """, (since.isoformat(),)).fetchall()

        # Підрахунок по годинах
        hour_counts = defaultdict(int)
        for (ts_str,) in rows:
            ts = datetime.fromisoformat(ts_str)
            hour_counts[ts.hour] += 1

        return dict(hour_counts)

    def get_usage_by_day(self, days: int = 7) -> Dict[str, int]:
        """Розподіл використання по днях тижня"""
        since = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            rows = cur.execute("""
                SELECT timestamp FROM command_metrics
                WHERE timestamp > ?
            """, (since.isoformat(),)).fetchall()

        # Підрахунок по днях
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_counts = defaultdict(int)

        for (ts_str,) in rows:
            ts = datetime.fromisoformat(ts_str)
            day_counts[day_names[ts.weekday()]] += 1

        return dict(day_counts)

    def detect_time_patterns(self, min_occurrences: int = 3) -> List[UsagePattern]:
        """Виявлення часових патернів (коли користувач активний)"""
        hour_usage = self.get_usage_by_hour(days=14)

        patterns = []
        total_commands = sum(hour_usage.values())

        if total_commands == 0:
            return patterns

        # Знаходимо години з високою активністю (>10% від загальної)
        for hour, count in hour_usage.items():
            percentage = count / total_commands
            if count >= min_occurrences and percentage > 0.1:
                patterns.append(UsagePattern(
                    pattern_type="time_of_day",
                    description=f"Активність о {hour}:00 ({count} команд, {percentage*100:.1f}%)",
                    confidence=min(percentage * 5, 1.0),  # Scale to 0-1
                    occurrences=count,
                    last_seen=datetime.now(),
                    metadata={"hour": hour, "percentage": percentage}
                ))

        return patterns

    def detect_sequence_patterns(self, min_occurrences: int = 2) -> List[UsagePattern]:
        """Виявлення послідовностей команд (що йде після чого)"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            # Отримуємо останні 100 команд
            rows = cur.execute("""
                SELECT command, timestamp
                FROM command_metrics
                ORDER BY timestamp DESC
                LIMIT 100
            """).fetchall()

        if len(rows) < 2:
            return []

        # Шукаємо пари команд (A → B)
        sequences = []
        for i in range(len(rows) - 1):
            cmd1, ts1 = rows[i]
            cmd2, ts2 = rows[i + 1]

            # Якщо команди в межах 5 хвилин - це послідовність
            t1 = datetime.fromisoformat(ts1)
            t2 = datetime.fromisoformat(ts2)
            if abs((t1 - t2).total_seconds()) < 300:
                sequences.append((cmd2, cmd1))  # Reversed because DESC order

        # Підраховуємо частоту
        sequence_counts = Counter(sequences)

        patterns = []
        for (cmd1, cmd2), count in sequence_counts.items():
            if count >= min_occurrences:
                patterns.append(UsagePattern(
                    pattern_type="sequence",
                    description=f"'{cmd1}' часто йде після '{cmd2}'",
                    confidence=min(count / 10, 1.0),
                    occurrences=count,
                    last_seen=datetime.now(),
                    metadata={"first": cmd1, "second": cmd2}
                ))

        return patterns

    def detect_frequency_patterns(self, min_occurrences: int = 5) -> List[UsagePattern]:
        """Виявлення частих команд"""
        top_commands = self.get_top_commands(limit=5, hours=168)

        patterns = []
        total = sum(count for _, count in top_commands)

        for command, count in top_commands:
            if count >= min_occurrences:
                percentage = count / total if total > 0 else 0
                patterns.append(UsagePattern(
                    pattern_type="frequency",
                    description=f"Часто використовується: '{command}' ({count} разів)",
                    confidence=min(percentage * 3, 1.0),
                    occurrences=count,
                    last_seen=datetime.now(),
                    metadata={"command": command, "percentage": percentage}
                ))

        return patterns

    def save_pattern(self, pattern: UsagePattern):
        """Зберегти виявлений патерн"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO usage_patterns
                (pattern_type, description, confidence, occurrences, last_seen, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_type,
                pattern.description,
                pattern.confidence,
                pattern.occurrences,
                pattern.last_seen.isoformat(),
                json.dumps(pattern.metadata)
            ))
            conn.commit()

    def get_all_patterns(self, active_only: bool = True) -> List[UsagePattern]:
        """Отримати всі збережені патерни"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            query = "SELECT pattern_type, description, confidence, occurrences, last_seen, metadata FROM usage_patterns"
            if active_only:
                query += " WHERE active = 1"

            rows = cur.execute(query).fetchall()

        patterns = []
        for row in rows:
            patterns.append(UsagePattern(
                pattern_type=row[0],
                description=row[1],
                confidence=row[2],
                occurrences=row[3],
                last_seen=datetime.fromisoformat(row[4]),
                metadata=json.loads(row[5]) if row[5] else {}
            ))

        return patterns

    def analyze_and_update_patterns(self):
        """Аналіз даних та оновлення патернів"""
        logger.info("Running pattern analysis...")

        # Виявляємо нові патерни
        time_patterns = self.detect_time_patterns()
        sequence_patterns = self.detect_sequence_patterns()
        frequency_patterns = self.detect_frequency_patterns()

        all_new_patterns = time_patterns + sequence_patterns + frequency_patterns

        # Зберігаємо нові патерни
        for pattern in all_new_patterns:
            self.save_pattern(pattern)

        logger.info(f"Found {len(all_new_patterns)} patterns: "
                   f"{len(time_patterns)} time, "
                   f"{len(sequence_patterns)} sequence, "
                   f"{len(frequency_patterns)} frequency")

        return all_new_patterns

    def get_dashboard_stats(self) -> Dict:
        """Повна статистика для dashboard"""
        return {
            "success_rate": self.get_success_rate(hours=24),
            "performance": self.get_performance_stats(hours=24),
            "top_commands": self.get_top_commands(limit=10),
            "usage_by_hour": self.get_usage_by_hour(days=7),
            "usage_by_day": self.get_usage_by_day(days=7),
            "patterns": [asdict(p) for p in self.get_all_patterns()]
        }

# Глобальний екземпляр
analytics = AnalyticsEngine()
