import sqlite3
import logging
import threading
from typing import List, Tuple, Optional, Dict, Iterator
from contextlib import contextmanager
from functools import lru_cache

logger = logging.getLogger("db_manager")

class DatabaseManager:
    """
    Оптимізований менеджер бази даних з connection pooling та кешуванням.
    """

    def __init__(self, db_path: str, pool_size: int = 5) -> None:
        self.db_path = db_path
        self.pool_size = pool_size
        self._local = threading.local()
        self._lock = threading.Lock()

        # Ініціалізація бази та індексів
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Отримує connection для поточного потоку"""
        if not hasattr(self._local, 'connection'):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Оптимізації SQLite
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging для швидшості
            conn.execute("PRAGMA synchronous=NORMAL")  # Баланс між швидкістю та безпекою
            conn.execute("PRAGMA cache_size=-64000")  # 64MB кеш
            conn.execute("PRAGMA temp_store=MEMORY")  # Тимчасові таблиці в RAM
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return self._local.connection

    @contextmanager
    def get_cursor(self) -> Iterator[sqlite3.Cursor]:
        """Context manager для безпечної роботи з курсором"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()

    def _init_database(self) -> None:
        """Ініціалізація бази та створення індексів"""
        try:
            with self.get_cursor() as cur:
                # Перевірка існування таблиці
                cur.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='apps'
                """)

                if not cur.fetchone():
                    logger.info("Таблиця apps не існує, створюємо...")
                    cur.execute("""
                        CREATE TABLE apps (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            exe_path TEXT NOT NULL,
                            canonical_name TEXT,
                            source TEXT,
                            score INTEGER DEFAULT 0
                        )
                    """)

                # Створення індексів для швидкого пошуку
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_canonical_name
                    ON apps(canonical_name)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_score
                    ON apps(score DESC)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_name
                    ON apps(name COLLATE NOCASE)
                """)

                logger.info("✅ База даних ініціалізована з індексами")
        except Exception as e:
            logger.error(f"Помилка ініціалізації БД: {e}")

    @lru_cache(maxsize=128)
    def get_exe_by_canonical(self, canon: str) -> Optional[Tuple[str, str]]:
        """Кешований пошук додатку за канонічною назвою"""
        if not canon:
            return None

        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT name, exe_path
                    FROM apps
                    WHERE canonical_name = ?
                    ORDER BY score DESC
                    LIMIT 1
                """, (canon.strip().lower(),))

                row = cur.fetchone()
                if row:
                    return (row['name'], row['exe_path'])
        except Exception as e:
            logger.error(f"get_exe_by_canonical error: {e}")

        return None

    def load_apps(self) -> List[Tuple[str, str]]:
        """Завантаження всіх додатків з оптимізованим запитом"""
        items = []
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT name, exe_path
                    FROM apps
                    ORDER BY score DESC, name ASC
                """)
                items = [(row['name'], row['exe_path']) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"load_apps error: {e}")

        return items

    def get_counts(self) -> Dict:
        """Статистика по базі даних"""
        try:
            with self.get_cursor() as cur:
                # Загальна кількість
                cur.execute("SELECT COUNT(*) as total FROM apps")
                total = cur.fetchone()['total']

                # По джерелах
                cur.execute("""
                    SELECT source, COUNT(*) as count
                    FROM apps
                    GROUP BY source
                """)
                by_source = {row['source'] or '': row['count'] for row in cur.fetchall()}

                return {
                    "total": total,
                    "by_source": by_source,
                    "db_path": self.db_path
                }
        except Exception as e:
            logger.error(f"get_counts error: {e}")
            return {"total": 0, "by_source": {}, "db_path": self.db_path, "error": str(e)}

    def add_app(
        self,
        name: str,
        exe_path: str,
        canonical_name: Optional[str] = None,
        source: Optional[str] = None,
        score: int = 0
    ) -> None:
        """Додавання нового додатку"""
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO apps (name, exe_path, canonical_name, source, score)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, exe_path, canonical_name, source, score))

                # Очищаємо кеш після додавання
                self.get_exe_by_canonical.cache_clear()
                logger.info(f"✅ Додано додаток: {name}")
        except Exception as e:
            logger.error(f"add_app error: {e}")

    def close(self) -> None:
        """Закриття всіх з'єднань"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
