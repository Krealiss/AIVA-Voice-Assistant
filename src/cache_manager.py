"""
Unified Cache Manager - централізоване кешування для всіх модулів
LRU eviction policy, статистика, автоматичне очищення
"""
import sqlite3
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict
from collections import OrderedDict
import threading

logger = logging.getLogger("cache_manager")


class CacheStats:
    """Статистика кешування"""
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_size = 0
        self._lock = threading.Lock()

    def record_hit(self):
        with self._lock:
            self.hits += 1

    def record_miss(self):
        with self._lock:
            self.misses += 1

    def record_eviction(self):
        with self._lock:
            self.evictions += 1

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "total_requests": total,
                "hit_rate_percent": round(hit_rate, 2),
                "total_size": self.total_size
            }

    def reset(self):
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.evictions = 0


class LRUCache:
    """LRU Cache з обмеженням розміру та TTL"""
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()  # key -> (value, expires_at)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self.cache:
                value, expires_at = self.cache[key]

                # Перевірка TTL
                if datetime.now() < expires_at:
                    # Переміщуємо в кінець (найбільш недавно використаний)
                    self.cache.move_to_end(key)
                    return value
                else:
                    # Видаляємо протерміноване
                    del self.cache[key]
                    return None
            return None

    def set(self, key: str, value: Any, expires_at: datetime) -> bool:
        """Повертає True якщо був eviction"""
        with self._lock:
            evicted = False

            # Якщо ключ вже є, оновлюємо
            if key in self.cache:
                self.cache.move_to_end(key)
                self.cache[key] = (value, expires_at)
                return False

            # Якщо досягли ліміту, видаляємо найстаріший
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
                evicted = True

            self.cache[key] = (value, expires_at)
            return evicted

    def delete(self, key: str):
        with self._lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self):
        with self._lock:
            self.cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self.cache)


class CacheManager:
    """Unified Cache Manager для всіх модулів"""

    def __init__(self, db_path: str = "data/unified_cache.db", max_memory_items: int = 1000):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory LRU cache для швидкого доступу
        self.memory_cache = LRUCache(max_size=max_memory_items)

        # Статистика
        self.stats = CacheStats()

        # Ініціалізація БД
        self._init_db()

        logger.info(f"CacheManager initialized: {self.db_path}")

    def _init_db(self):
        """Ініціалізація БД кешу"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT NOT NULL
                )
            """)

            # Індекси для швидкого пошуку
            conn.execute("CREATE INDEX IF NOT EXISTS idx_namespace ON cache(namespace)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache(last_accessed)")

            conn.commit()

    def _make_key(self, namespace: str, key: str) -> str:
        """Створити унікальний ключ"""
        return f"{namespace}:{key}"

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Отримати значення з кешу"""
        full_key = self._make_key(namespace, key)

        # Спочатку перевіряємо memory cache (з TTL)
        cached = self.memory_cache.get(full_key)
        if cached is not None:
            self.stats.record_hit()
            return cached

        # Якщо немає в пам'яті, шукаємо в БД
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                result = cur.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?",
                    (full_key,)
                ).fetchone()

                if result:
                    value_json, expires_at_str = result
                    expires_at = datetime.fromisoformat(expires_at_str)

                    # Перевірка TTL
                    if expires_at > datetime.now():
                        value = json.loads(value_json)

                        # Оновлюємо статистику доступу
                        cur.execute(
                            "UPDATE cache SET access_count = access_count + 1, last_accessed = ? WHERE key = ?",
                            (datetime.now().isoformat(), full_key)
                        )
                        conn.commit()

                        # Додаємо в memory cache з TTL
                        self.memory_cache.set(full_key, value, expires_at)

                        self.stats.record_hit()
                        return value
                    else:
                        # Видаляємо протерміноване з БД
                        cur.execute("DELETE FROM cache WHERE key = ?", (full_key,))
                        conn.commit()

        except Exception as e:
            logger.error(f"Cache get error: {e}")

        self.stats.record_miss()
        return None

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int = 300):
        """Зберегти значення в кеш"""
        full_key = self._make_key(namespace, key)

        try:
            value_json = json.dumps(value)
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl_seconds)

            # Зберігаємо в БД
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache
                    (key, value, namespace, created_at, expires_at, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, ?, 0, ?)
                """, (full_key, value_json, namespace, now.isoformat(), expires_at.isoformat(), now.isoformat()))
                conn.commit()

            # Додаємо в memory cache з TTL
            evicted = self.memory_cache.set(full_key, value, expires_at)
            if evicted:
                self.stats.record_eviction()

            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, namespace: str, key: str):
        """Видалити значення з кешу"""
        full_key = self._make_key(namespace, key)

        # Видаляємо з memory cache
        self.memory_cache.delete(full_key)

        # Видаляємо з БД
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (full_key,))
                conn.commit()
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

    def clear_namespace(self, namespace: str):
        """Очистити весь namespace"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE namespace = ?", (namespace,))
                conn.commit()

            # Очищаємо memory cache (тільки для цього namespace)
            # Це неефективно, але простіше за підтримку окремих namespace в LRU
            self.memory_cache.clear()

            logger.info(f"Cleared namespace: {namespace}")

        except Exception as e:
            logger.error(f"Cache clear namespace error: {e}")

    def clear_expired(self):
        """Видалити всі протерміновані записи"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM cache WHERE expires_at < ?",
                    (datetime.now().isoformat(),)
                )
                deleted = cur.rowcount
                conn.commit()

                logger.info(f"Cleared {deleted} expired cache entries")
                return deleted

        except Exception as e:
            logger.error(f"Cache clear expired error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Отримати статистику кешування"""
        stats = self.stats.get_stats()

        # Додаємо інформацію про розмір
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()

                # Загальна кількість записів
                total = cur.execute("SELECT COUNT(*) FROM cache").fetchone()[0]

                # Кількість по namespace
                namespaces = cur.execute(
                    "SELECT namespace, COUNT(*) FROM cache GROUP BY namespace"
                ).fetchall()

                stats["db_total_entries"] = total
                stats["memory_cache_size"] = self.memory_cache.size()
                stats["namespaces"] = {ns: count for ns, count in namespaces}

        except Exception as e:
            logger.error(f"Cache stats error: {e}")

        return stats

    def close(self):
        """Закрити з'єднання"""
        self.memory_cache.clear()
        logger.info("CacheManager closed")


# Глобальний екземпляр
cache_manager = CacheManager()
