"""
Context & User Profile API

REST API endpoints for context management and user profiles.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from context_manager import context_manager, Session, Message
from user_profile import profile_manager, UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context", tags=["context"])
user_router = APIRouter(prefix="/api/users", tags=["users"])


# === Request/Response Models ===

class SessionCreateRequest(BaseModel):
    user_id: str = "default"
    session_id: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    start_time: str
    last_activity: str
    is_active: bool


class MessageResponse(BaseModel):
    message_id: str
    session_id: str
    role: str
    content: str
    timestamp: str


class MessageAddRequest(BaseModel):
    session_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class UserProfileRequest(BaseModel):
    user_id: str
    name: str
    preferences: Optional[Dict[str, Any]] = None
    timezone: str = "Europe/Kiev"
    language: str = "uk"


class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


# === Context Endpoints ===

@router.post("/session/start", response_model=SessionResponse)
async def start_session(request: SessionCreateRequest):
    """Create a new conversation session"""
    try:
        session = context_manager.create_session(
            user_id=request.user_id,
            session_id=request.session_id
        )
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            start_time=session.start_time.isoformat(),
            last_activity=session.last_activity.isoformat(),
            is_active=session.is_active
        )
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session by ID"""
    session = context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        start_time=session.start_time.isoformat(),
        last_activity=session.last_activity.isoformat(),
        is_active=session.is_active
    )


@router.get("/session/active/{user_id}", response_model=SessionResponse)
async def get_active_session(user_id: str = "default"):
    """Get or create active session for user"""
    try:
        session = context_manager.get_active_session(user_id)
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            start_time=session.start_time.isoformat(),
            last_activity=session.last_activity.isoformat(),
            is_active=session.is_active
        )
    except Exception as e:
        logger.error(f"Error getting active session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    """End a conversation session"""
    try:
        context_manager.end_session(session_id)
        return {"ok": True, "message": "Session ended"}
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", response_model=List[MessageResponse])
async def get_history(session_id: str, limit: Optional[int] = None):
    """Get conversation history for session"""
    try:
        messages = context_manager.get_session_history(session_id, limit)
        return [
            MessageResponse(
                message_id=msg.message_id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp.isoformat()
            )
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/window/{session_id}", response_model=List[MessageResponse])
async def get_context_window(session_id: str):
    """Get recent messages within context window"""
    try:
        messages = context_manager.get_context_window(session_id)
        return [
            MessageResponse(
                message_id=msg.message_id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp.isoformat()
            )
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"Error getting context window: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/add", response_model=MessageResponse)
async def add_message(request: MessageAddRequest):
    """Add message to session"""
    try:
        message = context_manager.add_message(
            session_id=request.session_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata
        )
        return MessageResponse(
            message_id=message.message_id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            timestamp=message.timestamp.isoformat()
        )
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear conversation history for session"""
    try:
        context_manager.clear_session_history(session_id)
        return {"ok": True, "message": "History cleared"}
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/user/{user_id}", response_model=List[SessionResponse])
async def get_user_sessions(user_id: str, limit: int = 10):
    """Get recent sessions for user"""
    try:
        sessions = context_manager.get_user_sessions(user_id, limit)
        return [
            SessionResponse(
                session_id=s.session_id,
                user_id=s.user_id,
                start_time=s.start_time.isoformat(),
                last_activity=s.last_activity.isoformat(),
                is_active=s.is_active
            )
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_sessions(days: int = 7):
    """Remove sessions older than specified days"""
    try:
        context_manager.cleanup_old_sessions(days)
        return {"ok": True, "message": f"Cleaned up sessions older than {days} days"}
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === User Profile Endpoints ===

@user_router.post("/profile", response_model=Dict[str, Any])
async def create_profile(request: UserProfileRequest):
    """Create a new user profile"""
    try:
        profile = UserProfile(
            user_id=request.user_id,
            name=request.name,
            preferences=request.preferences,
            timezone=request.timezone,
            language=request.language
        )
        success = profile_manager.create_profile(profile)
        if not success:
            raise HTTPException(status_code=400, detail="Profile already exists")

        return profile.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/profile/{user_id}", response_model=Dict[str, Any])
async def get_profile(user_id: str):
    """Get user profile by ID"""
    profile = profile_manager.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile.to_dict()


@user_router.put("/profile/{user_id}", response_model=Dict[str, Any])
async def update_profile(user_id: str, request: UserProfileUpdateRequest):
    """Update user profile"""
    try:
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.preferences is not None:
            updates["preferences"] = request.preferences
        if request.timezone is not None:
            updates["timezone"] = request.timezone
        if request.language is not None:
            updates["language"] = request.language

        success = profile_manager.update_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile = profile_manager.get_profile(user_id)
        return profile.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.delete("/profile/{user_id}")
async def delete_profile(user_id: str):
    """Delete user profile"""
    try:
        success = profile_manager.delete_profile(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {"ok": True, "message": "Profile deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/profiles", response_model=List[Dict[str, Any]])
async def list_profiles():
    """List all user profiles"""
    try:
        profiles = profile_manager.list_profiles()
        return [p.to_dict() for p in profiles]
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))
