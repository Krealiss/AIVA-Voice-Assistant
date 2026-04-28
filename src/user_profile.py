"""
User Profile Management Module

Manages user profiles, preferences, and personalization settings.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class UserProfile:
    """Represents a user profile with preferences and settings"""

    def __init__(
        self,
        user_id: str,
        name: str,
        preferences: Optional[Dict[str, Any]] = None,
        timezone: str = "Europe/Kiev",
        language: str = "uk",
        created_at: Optional[datetime] = None
    ):
        self.user_id = user_id
        self.name = name
        self.preferences = preferences or {}
        self.timezone = timezone
        self.language = language
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "preferences": self.preferences,
            "timezone": self.timezone,
            "language": self.language,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Create profile from dictionary"""
        created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else None
        return cls(
            user_id=data["user_id"],
            name=data["name"],
            preferences=data.get("preferences", {}),
            timezone=data.get("timezone", "Europe/Kiev"),
            language=data.get("language", "uk"),
            created_at=created_at
        )


class UserProfileManager:
    """Manages user profiles with SQLite storage"""

    def __init__(self, db_path: str = "data/profiles.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"UserProfileManager initialized with DB: {db_path}")

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    preferences_json TEXT DEFAULT '{}',
                    timezone TEXT DEFAULT 'Europe/Kiev',
                    language TEXT DEFAULT 'uk',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_profiles_name
                ON user_profiles(name)
            """)
            conn.commit()

    def create_profile(self, profile: UserProfile) -> bool:
        """Create a new user profile"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT INTO user_profiles
                    (user_id, name, preferences_json, timezone, language, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile.user_id,
                    profile.name,
                    json.dumps(profile.preferences, ensure_ascii=False),
                    profile.timezone,
                    profile.language,
                    profile.created_at.isoformat(),
                    now
                ))
                conn.commit()
            logger.info(f"Created profile for user: {profile.user_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Profile already exists: {profile.user_id}")
            return False
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            return False

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM user_profiles WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()

                if row:
                    return UserProfile(
                        user_id=row["user_id"],
                        name=row["name"],
                        preferences=json.loads(row["preferences_json"]),
                        timezone=row["timezone"],
                        language=row["language"],
                        created_at=datetime.fromisoformat(row["created_at"])
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None

    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                set_clauses = []
                values = []

                if "name" in updates:
                    set_clauses.append("name = ?")
                    values.append(updates["name"])

                if "preferences" in updates:
                    set_clauses.append("preferences_json = ?")
                    values.append(json.dumps(updates["preferences"], ensure_ascii=False))

                if "timezone" in updates:
                    set_clauses.append("timezone = ?")
                    values.append(updates["timezone"])

                if "language" in updates:
                    set_clauses.append("language = ?")
                    values.append(updates["language"])

                set_clauses.append("updated_at = ?")
                values.append(datetime.now().isoformat())
                values.append(user_id)

                query = f"UPDATE user_profiles SET {', '.join(set_clauses)} WHERE user_id = ?"
                conn.execute(query, values)
                conn.commit()

            logger.info(f"Updated profile: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False

    def delete_profile(self, user_id: str) -> bool:
        """Delete user profile"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
                conn.commit()
            logger.info(f"Deleted profile: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting profile: {e}")
            return False

    def list_profiles(self) -> List[UserProfile]:
        """List all user profiles"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM user_profiles ORDER BY created_at DESC")

                profiles = []
                for row in cursor.fetchall():
                    profiles.append(UserProfile(
                        user_id=row["user_id"],
                        name=row["name"],
                        preferences=json.loads(row["preferences_json"]),
                        timezone=row["timezone"],
                        language=row["language"],
                        created_at=datetime.fromisoformat(row["created_at"])
                    ))
                return profiles
        except Exception as e:
            logger.error(f"Error listing profiles: {e}")
            return []

    def get_or_create_default(self, user_id: str = "default", name: str = "User") -> UserProfile:
        """Get existing profile or create default one"""
        profile = self.get_profile(user_id)
        if profile:
            return profile

        profile = UserProfile(user_id=user_id, name=name)
        self.create_profile(profile)
        return profile


# Global instance
profile_manager = UserProfileManager()
