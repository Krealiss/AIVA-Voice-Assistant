"""
Feedback System - система зворотного зв'язку для continuous improvement
User corrections, rating system, learning from mistakes
"""
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger("feedback")

class FeedbackType(Enum):
    """Типи зворотного зв'язку"""
    CORRECTION = "correction"  # Користувач виправив відповідь
    RATING = "rating"  # Оцінка відповіді (1-5)
    COMPLAINT = "complaint"  # Скарга на помилку
    PRAISE = "praise"  # Позитивний відгук
    SUGGESTION = "suggestion"  # Пропозиція покращення

@dataclass
class Feedback:
    """Запис зворотного зв'язку"""
    feedback_id: Optional[int]
    feedback_type: str
    command: str
    response: str
    user_input: str  # Що користувач сказав/написав
    rating: Optional[int]  # 1-5 або None
    comment: Optional[str]
    timestamp: datetime
    processed: bool = False
    applied: bool = False

@dataclass
class Correction:
    """Виправлення від користувача"""
    original_command: str
    original_response: str
    corrected_response: str
    correction_type: str  # "intent", "parameter", "action"
    timestamp: datetime

class FeedbackSystem:
    """Система збору та обробки зворотного зв'язку"""

    def __init__(self, db_path: str = "data/feedback.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ініціалізація БД"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        # Таблиця feedback
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_type TEXT NOT NULL,
                command TEXT NOT NULL,
                response TEXT NOT NULL,
                user_input TEXT NOT NULL,
                rating INTEGER,
                comment TEXT,
                timestamp TEXT NOT NULL,
                processed INTEGER DEFAULT 0,
                applied INTEGER DEFAULT 0
            )
        """)

        # Таблиця corrections
        conn.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_command TEXT NOT NULL,
                original_response TEXT NOT NULL,
                corrected_response TEXT NOT NULL,
                correction_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                applied INTEGER DEFAULT 0
            )
        """)

        # Таблиця learned improvements
        conn.execute("""
            CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                improvement_type TEXT NOT NULL,
                description TEXT NOT NULL,
                before_value TEXT,
                after_value TEXT,
                confidence REAL NOT NULL,
                applied_at TEXT NOT NULL,
                source_feedback_id INTEGER,
                FOREIGN KEY (source_feedback_id) REFERENCES feedback(id)
            )
        """)

        # Індекси
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rating ON feedback(rating)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_processed ON feedback(processed)")

        conn.commit()
        conn.close()
        logger.info("Feedback System DB initialized")

    def submit_feedback(self, feedback: Feedback) -> int:
        """Подати зворотний зв'язок"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO feedback
            (feedback_type, command, response, user_input, rating, comment, timestamp, processed, applied)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback.feedback_type,
            feedback.command,
            feedback.response,
            feedback.user_input,
            feedback.rating,
            feedback.comment,
            feedback.timestamp.isoformat(),
            1 if feedback.processed else 0,
            1 if feedback.applied else 0
        ))

        feedback_id = cur.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Feedback submitted: {feedback.feedback_type} for '{feedback.command}'")
        return feedback_id

    def submit_correction(self, correction: Correction):
        """Подати виправлення"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO corrections
            (original_command, original_response, corrected_response, correction_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            correction.original_command,
            correction.original_response,
            correction.corrected_response,
            correction.correction_type,
            correction.timestamp.isoformat()
        ))
        conn.commit()
        conn.close()

        logger.info(f"Correction submitted for '{correction.original_command}'")

    def rate_response(self, command: str, response: str, rating: int, comment: Optional[str] = None):
        """Оцінити відповідь (1-5 зірок)"""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        feedback = Feedback(
            feedback_id=None,
            feedback_type=FeedbackType.RATING.value,
            command=command,
            response=response,
            user_input="",
            rating=rating,
            comment=comment,
            timestamp=datetime.now()
        )

        return self.submit_feedback(feedback)

    def report_error(self, command: str, response: str, error_description: str):
        """Повідомити про помилку"""
        feedback = Feedback(
            feedback_id=None,
            feedback_type=FeedbackType.COMPLAINT.value,
            command=command,
            response=response,
            user_input=error_description,
            rating=1,
            comment=error_description,
            timestamp=datetime.now()
        )

        return self.submit_feedback(feedback)

    def praise_response(self, command: str, response: str, comment: Optional[str] = None):
        """Позитивний відгук"""
        feedback = Feedback(
            feedback_id=None,
            feedback_type=FeedbackType.PRAISE.value,
            command=command,
            response=response,
            user_input=comment or "Good response",
            rating=5,
            comment=comment,
            timestamp=datetime.now()
        )

        return self.submit_feedback(feedback)

    def get_average_rating(self, days: int = 7) -> float:
        """Середня оцінка за останні N днів"""
        since = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        result = cur.execute("""
            SELECT AVG(rating) FROM feedback
            WHERE rating IS NOT NULL AND timestamp > ?
        """, (since,)).fetchone()

        conn.close()

        return result[0] if result[0] else 0.0

    def get_rating_distribution(self, days: int = 30) -> Dict[int, int]:
        """Розподіл оцінок"""
        since = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        rows = cur.execute("""
            SELECT rating, COUNT(*) as count
            FROM feedback
            WHERE rating IS NOT NULL AND timestamp > ?
            GROUP BY rating
        """, (since,)).fetchall()

        conn.close()

        return {rating: count for rating, count in rows}

    def get_low_rated_commands(self, threshold: int = 2, limit: int = 10) -> List[Dict]:
        """Команди з низькими оцінками"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        rows = cur.execute("""
            SELECT command, AVG(rating) as avg_rating, COUNT(*) as count
            FROM feedback
            WHERE rating IS NOT NULL AND rating <= ?
            GROUP BY command
            HAVING count >= 2
            ORDER BY avg_rating ASC, count DESC
            LIMIT ?
        """, (threshold, limit)).fetchall()

        conn.close()

        return [
            {"command": cmd, "avg_rating": avg, "count": cnt}
            for cmd, avg, cnt in rows
        ]

    def get_unprocessed_feedback(self, limit: int = 50) -> List[Feedback]:
        """Отримати необроблений feedback"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        rows = cur.execute("""
            SELECT id, feedback_type, command, response, user_input, rating, comment, timestamp, processed, applied
            FROM feedback
            WHERE processed = 0
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()

        conn.close()

        feedbacks = []
        for row in rows:
            feedbacks.append(Feedback(
                feedback_id=row[0],
                feedback_type=row[1],
                command=row[2],
                response=row[3],
                user_input=row[4],
                rating=row[5],
                comment=row[6],
                timestamp=datetime.fromisoformat(row[7]),
                processed=bool(row[8]),
                applied=bool(row[9])
            ))

        return feedbacks

    def mark_as_processed(self, feedback_id: int, applied: bool = False):
        """Позначити feedback як оброблений"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE feedback
            SET processed = 1, applied = ?
            WHERE id = ?
        """, (1 if applied else 0, feedback_id))
        conn.commit()
        conn.close()

    def analyze_corrections(self) -> Dict:
        """Аналіз виправлень для виявлення патернів помилок"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Загальна кількість
        total = cur.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]

        # По типах
        by_type = cur.execute("""
            SELECT correction_type, COUNT(*) as count
            FROM corrections
            GROUP BY correction_type
        """).fetchall()

        # Найчастіші помилки
        common_errors = cur.execute("""
            SELECT original_command, COUNT(*) as count
            FROM corrections
            GROUP BY original_command
            HAVING count >= 2
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        conn.close()

        return {
            "total_corrections": total,
            "by_type": {t: c for t, c in by_type},
            "common_errors": [{"command": cmd, "count": cnt} for cmd, cnt in common_errors]
        }

    def learn_from_feedback(self):
        """Автоматичне навчання на основі feedback"""
        logger.info("Learning from feedback...")

        unprocessed = self.get_unprocessed_feedback()

        if not unprocessed:
            logger.info("No unprocessed feedback")
            return

        improvements_made = 0

        for fb in unprocessed:
            # Аналізуємо низькі оцінки
            if fb.rating and fb.rating <= 2:
                # Логуємо проблемну команду
                logger.warning(f"Low rating ({fb.rating}) for command: {fb.command}")

                # Можна додати логіку для автоматичного покращення
                # Наприклад, додати в blacklist або змінити intent mapping

            # Аналізуємо позитивні відгуки
            elif fb.rating and fb.rating >= 4:
                # Зберігаємо успішні патерни
                logger.info(f"High rating ({fb.rating}) for command: {fb.command}")

            # Позначаємо як оброблений
            self.mark_as_processed(fb.feedback_id)
            improvements_made += 1

        logger.info(f"Processed {improvements_made} feedback items")

    def get_feedback_stats(self) -> Dict:
        """Статистика feedback для dashboard"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Загальна статистика
        total = cur.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        processed = cur.execute("SELECT COUNT(*) FROM feedback WHERE processed = 1").fetchone()[0]
        avg_rating = cur.execute("SELECT AVG(rating) FROM feedback WHERE rating IS NOT NULL").fetchone()[0]

        # По типах
        by_type = cur.execute("""
            SELECT feedback_type, COUNT(*) as count
            FROM feedback
            GROUP BY feedback_type
        """).fetchall()

        # Останні відгуки
        recent = cur.execute("""
            SELECT feedback_type, command, rating, comment, timestamp
            FROM feedback
            ORDER BY timestamp DESC
            LIMIT 10
        """).fetchall()

        conn.close()

        return {
            "total_feedback": total,
            "processed": processed,
            "unprocessed": total - processed,
            "average_rating": round(avg_rating, 2) if avg_rating else 0,
            "by_type": {t: c for t, c in by_type},
            "recent": [
                {
                    "type": r[0],
                    "command": r[1],
                    "rating": r[2],
                    "comment": r[3],
                    "timestamp": r[4]
                }
                for r in recent
            ],
            "rating_distribution": self.get_rating_distribution(),
            "low_rated_commands": self.get_low_rated_commands()
        }

    def export_feedback(self, output_file: str = "feedback_export.json"):
        """Експорт feedback для аналізу"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        rows = cur.execute("""
            SELECT feedback_type, command, response, user_input, rating, comment, timestamp
            FROM feedback
            ORDER BY timestamp DESC
        """).fetchall()

        conn.close()

        data = [
            {
                "type": r[0],
                "command": r[1],
                "response": r[2],
                "user_input": r[3],
                "rating": r[4],
                "comment": r[5],
                "timestamp": r[6]
            }
            for r in rows
        ]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {len(data)} feedback items to {output_file}")

# Глобальний екземпляр
feedback_system = FeedbackSystem()
