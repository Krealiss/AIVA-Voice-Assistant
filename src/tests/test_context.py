"""
Tests for Context Manager and User Profile modules
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from context_manager import ContextManager, Session, Message
from user_profile import UserProfileManager, UserProfile


# === Fixtures ===

@pytest.fixture
def temp_context_db():
    """Create temporary context database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Windows fix: wait a bit before cleanup
    import time
    time.sleep(0.1)
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except PermissionError:
        pass  # File still in use, will be cleaned by OS


@pytest.fixture
def temp_profile_db():
    """Create temporary profile database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Windows fix: wait a bit before cleanup
    import time
    time.sleep(0.1)
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except PermissionError:
        pass  # File still in use, will be cleaned by OS


@pytest.fixture
def context_mgr(temp_context_db):
    """Create ContextManager instance"""
    return ContextManager(db_path=temp_context_db, context_window=5, session_ttl_minutes=30)


@pytest.fixture
def profile_mgr(temp_profile_db):
    """Create UserProfileManager instance"""
    return UserProfileManager(db_path=temp_profile_db)


# === Context Manager Tests ===

class TestContextManager:

    def test_create_session(self, context_mgr):
        """Test session creation"""
        session = context_mgr.create_session(user_id="test_user")

        assert session.session_id is not None
        assert session.user_id == "test_user"
        assert session.is_active is True
        assert isinstance(session.start_time, datetime)
        assert isinstance(session.last_activity, datetime)

    def test_get_session(self, context_mgr):
        """Test retrieving session by ID"""
        session = context_mgr.create_session(user_id="test_user")

        retrieved = context_mgr.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        assert retrieved.user_id == session.user_id

    def test_get_active_session(self, context_mgr):
        """Test getting active session for user"""
        session1 = context_mgr.get_active_session("user1")
        assert session1 is not None
        assert session1.is_active is True

        # Should return same session
        session2 = context_mgr.get_active_session("user1")
        assert session2.session_id == session1.session_id

    def test_end_session(self, context_mgr):
        """Test ending a session"""
        session = context_mgr.create_session(user_id="test_user")
        context_mgr.end_session(session.session_id)

        retrieved = context_mgr.get_session(session.session_id)
        assert retrieved.is_active is False

    def test_add_message(self, context_mgr):
        """Test adding message to session"""
        session = context_mgr.create_session(user_id="test_user")

        message = context_mgr.add_message(
            session_id=session.session_id,
            role="user",
            content="Hello AIVA",
            metadata={"source": "test"}
        )

        assert message.message_id is not None
        assert message.session_id == session.session_id
        assert message.role == "user"
        assert message.content == "Hello AIVA"
        assert message.metadata["source"] == "test"

    def test_get_session_history(self, context_mgr):
        """Test retrieving session history"""
        session = context_mgr.create_session(user_id="test_user")

        # Add multiple messages
        context_mgr.add_message(session.session_id, "user", "Message 1")
        context_mgr.add_message(session.session_id, "assistant", "Response 1")
        context_mgr.add_message(session.session_id, "user", "Message 2")

        history = context_mgr.get_session_history(session.session_id)
        assert len(history) == 3
        assert history[0].content == "Message 1"
        assert history[1].content == "Response 1"
        assert history[2].content == "Message 2"

    def test_context_window(self, context_mgr):
        """Test context window limiting"""
        session = context_mgr.create_session(user_id="test_user")

        # Add more messages than context window
        for i in range(10):
            context_mgr.add_message(session.session_id, "user", f"Message {i}")

        window = context_mgr.get_context_window(session.session_id)
        assert len(window) == 5  # context_window=5
        assert window[0].content == "Message 5"
        assert window[-1].content == "Message 9"

    def test_clear_session_history(self, context_mgr):
        """Test clearing session history"""
        session = context_mgr.create_session(user_id="test_user")

        context_mgr.add_message(session.session_id, "user", "Message 1")
        context_mgr.add_message(session.session_id, "assistant", "Response 1")

        context_mgr.clear_session_history(session.session_id)

        history = context_mgr.get_session_history(session.session_id)
        assert len(history) == 0

    def test_get_user_sessions(self, context_mgr):
        """Test retrieving user sessions"""
        context_mgr.create_session(user_id="user1")
        context_mgr.create_session(user_id="user1")
        context_mgr.create_session(user_id="user2")

        sessions = context_mgr.get_user_sessions("user1")
        assert len(sessions) == 2
        assert all(s.user_id == "user1" for s in sessions)

    def test_session_ttl_expiry(self, context_mgr):
        """Test session TTL expiration"""
        # Create context manager with 0 minute TTL for testing
        mgr = ContextManager(
            db_path=context_mgr.db_path,
            context_window=5,
            session_ttl_minutes=0
        )

        session = mgr.create_session(user_id="test_user")

        # Get active session should create new one due to TTL
        new_session = mgr.get_active_session("test_user")
        assert new_session.session_id != session.session_id

    def test_cleanup_old_sessions(self, context_mgr):
        """Test cleanup of old sessions"""
        session = context_mgr.create_session(user_id="test_user")
        context_mgr.add_message(session.session_id, "user", "Test message")

        # Cleanup sessions older than 0 days (all)
        context_mgr.cleanup_old_sessions(days=0)

        # Session should be gone
        retrieved = context_mgr.get_session(session.session_id)
        assert retrieved is None


# === User Profile Tests ===

class TestUserProfileManager:

    def test_create_profile(self, profile_mgr):
        """Test profile creation"""
        profile = UserProfile(
            user_id="user1",
            name="Test User",
            preferences={"theme": "dark"},
            timezone="Europe/Kiev",
            language="uk"
        )

        success = profile_mgr.create_profile(profile)
        assert success is True

    def test_create_duplicate_profile(self, profile_mgr):
        """Test creating duplicate profile fails"""
        profile = UserProfile(user_id="user1", name="Test User")

        profile_mgr.create_profile(profile)
        success = profile_mgr.create_profile(profile)

        assert success is False

    def test_get_profile(self, profile_mgr):
        """Test retrieving profile"""
        profile = UserProfile(
            user_id="user1",
            name="Test User",
            preferences={"theme": "dark"}
        )
        profile_mgr.create_profile(profile)

        retrieved = profile_mgr.get_profile("user1")
        assert retrieved is not None
        assert retrieved.user_id == "user1"
        assert retrieved.name == "Test User"
        assert retrieved.preferences["theme"] == "dark"

    def test_get_nonexistent_profile(self, profile_mgr):
        """Test getting non-existent profile returns None"""
        profile = profile_mgr.get_profile("nonexistent")
        assert profile is None

    def test_update_profile(self, profile_mgr):
        """Test updating profile"""
        profile = UserProfile(user_id="user1", name="Old Name")
        profile_mgr.create_profile(profile)

        success = profile_mgr.update_profile("user1", {
            "name": "New Name",
            "preferences": {"theme": "light"}
        })

        assert success is True

        updated = profile_mgr.get_profile("user1")
        assert updated.name == "New Name"
        assert updated.preferences["theme"] == "light"

    def test_delete_profile(self, profile_mgr):
        """Test deleting profile"""
        profile = UserProfile(user_id="user1", name="Test User")
        profile_mgr.create_profile(profile)

        success = profile_mgr.delete_profile("user1")
        assert success is True

        retrieved = profile_mgr.get_profile("user1")
        assert retrieved is None

    def test_list_profiles(self, profile_mgr):
        """Test listing all profiles"""
        profile1 = UserProfile(user_id="user1", name="User 1")
        profile2 = UserProfile(user_id="user2", name="User 2")

        profile_mgr.create_profile(profile1)
        profile_mgr.create_profile(profile2)

        profiles = profile_mgr.list_profiles()
        assert len(profiles) == 2
        assert any(p.user_id == "user1" for p in profiles)
        assert any(p.user_id == "user2" for p in profiles)

    def test_get_or_create_default(self, profile_mgr):
        """Test get or create default profile"""
        profile = profile_mgr.get_or_create_default("default_user", "Default")

        assert profile.user_id == "default_user"
        assert profile.name == "Default"

        # Should return existing profile
        profile2 = profile_mgr.get_or_create_default("default_user", "Default")
        assert profile2.user_id == profile.user_id

    def test_profile_to_dict(self):
        """Test profile serialization"""
        profile = UserProfile(
            user_id="user1",
            name="Test User",
            preferences={"key": "value"},
            timezone="Europe/Kiev",
            language="uk"
        )

        data = profile.to_dict()
        assert data["user_id"] == "user1"
        assert data["name"] == "Test User"
        assert data["preferences"]["key"] == "value"
        assert data["timezone"] == "Europe/Kiev"
        assert data["language"] == "uk"

    def test_profile_from_dict(self):
        """Test profile deserialization"""
        data = {
            "user_id": "user1",
            "name": "Test User",
            "preferences": {"key": "value"},
            "timezone": "Europe/Kiev",
            "language": "uk",
            "created_at": datetime.now().isoformat()
        }

        profile = UserProfile.from_dict(data)
        assert profile.user_id == "user1"
        assert profile.name == "Test User"
        assert profile.preferences["key"] == "value"


# === Integration Tests ===

class TestContextIntegration:

    def test_multi_turn_conversation(self, context_mgr):
        """Test multi-turn conversation flow"""
        session = context_mgr.get_active_session("user1")

        # Turn 1
        context_mgr.add_message(session.session_id, "user", "Привіт")
        context_mgr.add_message(session.session_id, "assistant", "Привіт! Як справи?")

        # Turn 2
        context_mgr.add_message(session.session_id, "user", "Добре, дякую")
        context_mgr.add_message(session.session_id, "assistant", "Радий чути!")

        history = context_mgr.get_session_history(session.session_id)
        assert len(history) == 4
        assert history[0].role == "user"
        assert history[1].role == "assistant"

    def test_context_persistence(self, context_mgr):
        """Test context persists across manager instances"""
        session = context_mgr.create_session("user1")
        context_mgr.add_message(session.session_id, "user", "Test message")

        # Create new manager with same DB
        new_mgr = ContextManager(db_path=context_mgr.db_path)

        history = new_mgr.get_session_history(session.session_id)
        assert len(history) == 1
        assert history[0].content == "Test message"
