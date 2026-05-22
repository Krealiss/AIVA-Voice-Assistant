"""
Context Manager Module

Manages conversation context, session tracking, and multi-turn dialogues.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a single message in conversation"""
    message_id: str
    session_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None  # NLU: розпізнана інтенція
    entities: Optional[Dict[str, Any]] = None  # NLU: витягнуті entities
    confidence: Optional[float] = None  # NLU: впевненість розпізнавання

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class Session:
    """Represents a conversation session"""
    session_id: str
    user_id: str
    start_time: datetime
    last_activity: datetime
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        return data


class ContextManager:
    """Manages conversation context and session tracking"""

    def __init__(
        self,
        db_path: str = "data/context.db",
        context_window: int = 10,
        session_ttl_minutes: int = 30
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.context_window = context_window
        self.session_ttl = timedelta(minutes=session_ttl_minutes)
        self._init_db()
        logger.info(f"ContextManager initialized: window={context_window}, ttl={session_ttl_minutes}m")

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    metadata_json TEXT DEFAULT '{}'
                )
            """)

            # Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}',
                    intent TEXT,
                    entities_json TEXT DEFAULT '{}',
                    confidence REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON sessions(user_id, last_activity DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, timestamp DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_active
                ON sessions(is_active, last_activity DESC)
            """)

            conn.commit()

    def create_session(self, user_id: str, session_id: Optional[str] = None) -> Session:
        """Create a new conversation session"""
        if not session_id:
            session_id = f"session_{user_id}_{int(datetime.now().timestamp() * 1000)}"

        now = datetime.now()
        session = Session(
            session_id=session_id,
            user_id=user_id,
            start_time=now,
            last_activity=now,
            is_active=True
        )

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO sessions
                    (session_id, user_id, start_time, last_activity, is_active, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session.session_id,
                    session.user_id,
                    session.start_time.isoformat(),
                    session.last_activity.isoformat(),
                    1,
                    json.dumps(session.metadata or {})
                ))
                conn.commit()
            logger.info(f"Created session: {session_id}")
            return session
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sessions WHERE session_id = ?
                """, (session_id,))
                row = cursor.fetchone()

                if row:
                    return Session(
                        session_id=row["session_id"],
                        user_id=row["user_id"],
                        start_time=datetime.fromisoformat(row["start_time"]),
                        last_activity=datetime.fromisoformat(row["last_activity"]),
                        is_active=bool(row["is_active"]),
                        metadata=json.loads(row["metadata_json"])
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    def get_active_session(self, user_id: str) -> Optional[Session]:
        """Get active session for user or create new one"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sessions
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY last_activity DESC
                    LIMIT 1
                """, (user_id,))
                row = cursor.fetchone()

                if row:
                    session = Session(
                        session_id=row["session_id"],
                        user_id=row["user_id"],
                        start_time=datetime.fromisoformat(row["start_time"]),
                        last_activity=datetime.fromisoformat(row["last_activity"]),
                        is_active=bool(row["is_active"]),
                        metadata=json.loads(row["metadata_json"])
                    )

                    # Check if session expired
                    if datetime.now() - session.last_activity > self.session_ttl:
                        self.end_session(session.session_id)
                        return self.create_session(user_id)

                    return session

                # No active session, create new
                return self.create_session(user_id)
        except Exception as e:
            logger.error(f"Error getting active session: {e}")
            return self.create_session(user_id)

    def update_session_activity(self, session_id: str):
        """Update last activity timestamp"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE sessions
                    SET last_activity = ?
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")

    def end_session(self, session_id: str):
        """Mark session as inactive"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE sessions
                    SET is_active = 0, last_activity = ?
                    WHERE session_id = ?
                """, (datetime.now().isoformat(), session_id))
                conn.commit()
            logger.info(f"Ended session: {session_id}")
        except Exception as e:
            logger.error(f"Error ending session: {e}")

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None
    ) -> Message:
        """Add message to session with NLU data"""
        now = datetime.now()
        message_id = f"msg_{session_id}_{int(now.timestamp() * 1000)}"

        message = Message(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=now,
            metadata=metadata,
            intent=intent,
            entities=entities,
            confidence=confidence
        )

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO messages
                    (message_id, session_id, role, content, timestamp, metadata_json,
                     intent, entities_json, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.message_id,
                    message.session_id,
                    message.role,
                    message.content,
                    message.timestamp.isoformat(),
                    json.dumps(message.metadata or {}),
                    message.intent,
                    json.dumps(message.entities or {}),
                    message.confidence
                ))
                conn.commit()

            # Update session activity
            self.update_session_activity(session_id)

            logger.debug(f"Added message to session {session_id}: {role}, intent={intent}")
            return message
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise

    def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get conversation history for session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                query = """
                    SELECT * FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """
                params = [session_id]

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor = conn.execute(query, params)

                messages = []
                for row in cursor.fetchall():
                    # sqlite3.Row не має .get(), використовуємо try/except
                    try:
                        intent = row["intent"]
                    except (KeyError, IndexError):
                        intent = None

                    try:
                        entities_json = row["entities_json"]
                    except (KeyError, IndexError):
                        entities_json = "{}"

                    try:
                        confidence = row["confidence"]
                    except (KeyError, IndexError):
                        confidence = None

                    messages.append(Message(
                        message_id=row["message_id"],
                        session_id=row["session_id"],
                        role=row["role"],
                        content=row["content"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        metadata=json.loads(row["metadata_json"]),
                        intent=intent,
                        entities=json.loads(entities_json),
                        confidence=confidence
                    ))
                return messages
        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return []

    def get_context_window(self, session_id: str) -> List[Message]:
        """Get recent messages within context window"""
        messages = self.get_session_history(session_id)
        return messages[-self.context_window:] if messages else []

    def clear_session_history(self, session_id: str):
        """Clear all messages from session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                conn.commit()
            logger.info(f"Cleared history for session: {session_id}")
        except Exception as e:
            logger.error(f"Error clearing session history: {e}")

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Session]:
        """Get recent sessions for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sessions
                    WHERE user_id = ?
                    ORDER BY last_activity DESC
                    LIMIT ?
                """, (user_id, limit))

                sessions = []
                for row in cursor.fetchall():
                    sessions.append(Session(
                        session_id=row["session_id"],
                        user_id=row["user_id"],
                        start_time=datetime.fromisoformat(row["start_time"]),
                        last_activity=datetime.fromisoformat(row["last_activity"]),
                        is_active=bool(row["is_active"]),
                        metadata=json.loads(row["metadata_json"])
                    ))
                return sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    def cleanup_old_sessions(self, days: int = 7):
        """Remove sessions older than specified days"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            with sqlite3.connect(self.db_path) as conn:
                # Delete old messages
                conn.execute("""
                    DELETE FROM messages
                    WHERE session_id IN (
                        SELECT session_id FROM sessions
                        WHERE last_activity < ?
                    )
                """, (cutoff.isoformat(),))

                # Delete old sessions
                conn.execute("""
                    DELETE FROM sessions
                    WHERE last_activity < ?
                """, (cutoff.isoformat(),))

                conn.commit()
            logger.info(f"Cleaned up sessions older than {days} days")
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")

    # ============= NLU-specific methods =============

    def get_last_intent(self, session_id: str) -> Optional[str]:
        """Get last recognized intent from session"""
        messages = self.get_context_window(session_id)
        for msg in reversed(messages):
            if msg.role == "user" and msg.intent:
                return msg.intent
        return None

    def get_active_entities(self, session_id: str) -> Dict[str, Any]:
        """Get all active entities from recent context"""
        messages = self.get_context_window(session_id)
        entities = {}

        # Збираємо entities з останніх повідомлень (новіші перезаписують старіші)
        for msg in messages:
            if msg.role == "user" and msg.entities:
                entities.update(msg.entities)

        return entities

    def resolve_entity(
        self,
        session_id: str,
        entity_type: str,
        current_entities: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Resolve entity from context if not in current entities

        Args:
            session_id: Session ID
            entity_type: Type of entity (app, city, device, etc.)
            current_entities: Currently extracted entities

        Returns:
            Entity value or None
        """
        # Спочатку перевіряємо поточні entities
        if entity_type in current_entities:
            return current_entities[entity_type]

        # Шукаємо в контексті
        active_entities = self.get_active_entities(session_id)
        if entity_type in active_entities:
            logger.info(f"Resolved '{entity_type}' from context: {active_entities[entity_type]}")
            return active_entities[entity_type]

        return None

    def get_recent_intents(self, session_id: str, count: int = 5) -> List[str]:
        """Get list of recent intents"""
        messages = self.get_context_window(session_id)
        intents = []

        for msg in reversed(messages):
            if msg.role == "user" and msg.intent:
                intents.append(msg.intent)
                if len(intents) >= count:
                    break

        return list(reversed(intents))

    def infer_intent_from_context(self, session_id: str, current_text: str) -> Optional[str]:
        """
        Infer intent based on conversation context

        Example:
        - User: "запусти chrome"
        - System: "Запускаю Chrome"
        - User: "і firefox теж" <- no explicit command, but context suggests "run"
        """
        last_intent = self.get_last_intent(session_id)
        if not last_intent:
            return None

        # Ключові слова продовження
        continuation_markers = [
            "теж", "також", "ще", "і", "та", "плюс", "додатково",
            "too", "also", "and", "plus"
        ]

        words = set(current_text.lower().split())

        if any(marker in words for marker in continuation_markers):
            logger.info(f"Inferred intent '{last_intent}' from context")
            return last_intent

        return None

    def get_conversation_summary(self, session_id: str, count: int = 3) -> str:
        """Generate conversation summary for LLM"""
        messages = self.get_context_window(session_id)
        if not messages:
            return "Нова розмова"

        recent = messages[-count:]
        summary_parts = []

        for msg in recent:
            if msg.role == "user":
                intent_info = f" (intent: {msg.intent})" if msg.intent else ""
                summary_parts.append(f"User: '{msg.content}'{intent_info}")
            else:
                summary_parts.append(f"Assistant: '{msg.content[:50]}...'")

        return " | ".join(summary_parts)

    def detect_pattern(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Detect patterns in conversation history"""
        messages = self.get_context_window(session_id)
        if len(messages) < 3:
            return None

        user_messages = [m for m in messages if m.role == "user" and m.intent]
        if len(user_messages) < 3:
            return None

        recent = user_messages[-5:]

        # Pattern 1: Repeated intent
        intents = [m.intent for m in recent]
        if len(set(intents)) == 1:
            return {
                "type": "repeated_intent",
                "intent": intents[0],
                "count": len(intents),
                "suggestion": f"Схоже ви часто використовуєте '{intents[0]}'"
            }

        # Pattern 2: Sequence of actions
        if len(recent) >= 3:
            sequence = " -> ".join([m.intent for m in recent[-3:]])
            return {
                "type": "sequence",
                "sequence": sequence,
                "suggestion": "Виявлено послідовність дій"
            }

        return None

    def get_nlu_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get full NLU context for intent analysis

        Returns:
            Dictionary with context information for NLU engine
        """
        return {
            "last_intent": self.get_last_intent(session_id),
            "active_entities": self.get_active_entities(session_id),
            "recent_intents": self.get_recent_intents(session_id, 5),
            "conversation_summary": self.get_conversation_summary(session_id),
            "pattern": self.detect_pattern(session_id)
        }


# Global instance
context_manager = ContextManager()
