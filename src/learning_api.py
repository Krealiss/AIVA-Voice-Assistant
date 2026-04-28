"""
Learning API - endpoints для системи самонавчання
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

from analytics_engine import analytics, CommandMetric
from habit_learner import habit_learner
from feedback_system import feedback_system, Feedback, FeedbackType

router = APIRouter(prefix="/api/learning", tags=["learning"])

# === Models ===

class CommandMetricRequest(BaseModel):
    command: str
    intent_type: str
    success: bool
    duration_ms: float
    source: str
    user_id: Optional[str] = None
    error: Optional[str] = None

class FeedbackRequest(BaseModel):
    feedback_type: str
    command: str
    response: str
    user_input: str
    rating: Optional[int] = None
    comment: Optional[str] = None

class RatingRequest(BaseModel):
    command: str
    response: str
    rating: int
    comment: Optional[str] = None

class HabitInteractionRequest(BaseModel):
    habit_id: int
    action: str  # "accepted", "rejected", "ignored"

# === Analytics Endpoints ===

@router.post("/track")
async def track_command(metric: CommandMetricRequest):
    """Записати метрику виконання команди"""
    try:
        analytics.track_command(CommandMetric(
            command=metric.command,
            intent_type=metric.intent_type,
            success=metric.success,
            duration_ms=metric.duration_ms,
            timestamp=datetime.now(),
            source=metric.source,
            user_id=metric.user_id,
            error=metric.error
        ))
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/stats")
async def get_analytics_stats():
    """Отримати статистику аналітики"""
    try:
        return analytics.get_dashboard_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/success-rate")
async def get_success_rate(hours: int = 24):
    """Success rate за останні N годин"""
    try:
        return analytics.get_success_rate(hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/performance")
async def get_performance(hours: int = 24):
    """Статистика продуктивності"""
    try:
        return analytics.get_performance_stats(hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/top-commands")
async def get_top_commands(limit: int = 10):
    """Топ команд"""
    try:
        top = analytics.get_top_commands(limit)
        return {"commands": [{"command": cmd, "count": cnt} for cmd, cnt in top]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analytics/analyze")
async def analyze_patterns():
    """Запустити аналіз патернів"""
    try:
        patterns = analytics.analyze_and_update_patterns()
        return {
            "ok": True,
            "patterns_found": len(patterns),
            "patterns": [
                {
                    "type": p.pattern_type,
                    "description": p.description,
                    "confidence": p.confidence
                }
                for p in patterns
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === Habit Learning Endpoints ===

@router.get("/habits")
async def get_habits(min_confidence: float = 0.5):
    """Отримати активні звички"""
    try:
        habits = habit_learner.get_active_habits(min_confidence)
        return {
            "habits": [
                {
                    "id": h.habit_id,
                    "type": h.habit_type,
                    "description": h.description,
                    "confidence": h.confidence,
                    "times_observed": h.times_observed,
                    "times_accepted": h.times_accepted,
                    "times_rejected": h.times_rejected,
                    "suggested_action": h.suggested_action
                }
                for h in habits
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/habits/learn")
async def learn_habits():
    """Запустити навчання на звичках"""
    try:
        habit_learner.learn_from_analytics()
        habits = habit_learner.get_active_habits()
        return {
            "ok": True,
            "message": "Learning completed",
            "habits_found": len(habits)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/habits/interact")
async def interact_with_habit(interaction: HabitInteractionRequest):
    """Записати взаємодію зі звичкою"""
    try:
        habit_learner.record_interaction(interaction.habit_id, interaction.action)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/habits/suggestions")
async def get_suggestions(last_command: Optional[str] = None):
    """Отримати пропозиції на основі контексту"""
    try:
        context = {"last_command": last_command}
        suggestion = habit_learner.get_suggestion(context)

        if suggestion:
            return {"ok": True, "suggestion": suggestion}
        else:
            return {"ok": True, "suggestion": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preferences")
async def get_preferences(preference_type: Optional[str] = None):
    """Отримати вподобання користувача"""
    try:
        prefs = habit_learner.get_preferences(preference_type)
        return {
            "preferences": [
                {
                    "type": p.preference_type,
                    "key": p.key,
                    "value": p.value,
                    "confidence": p.confidence,
                    "learned_from": p.learned_from
                }
                for p in prefs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === Feedback Endpoints ===

@router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Подати зворотний зв'язок"""
    try:
        feedback_id = feedback_system.submit_feedback(Feedback(
            feedback_id=None,
            feedback_type=feedback.feedback_type,
            command=feedback.command,
            response=feedback.response,
            user_input=feedback.user_input,
            rating=feedback.rating,
            comment=feedback.comment,
            timestamp=datetime.now()
        ))
        return {"ok": True, "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback/rate")
async def rate_response(rating: RatingRequest):
    """Оцінити відповідь"""
    try:
        if not 1 <= rating.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        feedback_id = feedback_system.rate_response(
            rating.command,
            rating.response,
            rating.rating,
            rating.comment
        )
        return {"ok": True, "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback/stats")
async def get_feedback_stats():
    """Статистика feedback"""
    try:
        return feedback_system.get_feedback_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback/average-rating")
async def get_average_rating(days: int = 7):
    """Середня оцінка"""
    try:
        avg = feedback_system.get_average_rating(days)
        return {"average_rating": round(avg, 2), "days": days}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback/learn")
async def learn_from_feedback():
    """Навчання на основі feedback"""
    try:
        feedback_system.learn_from_feedback()
        return {"ok": True, "message": "Learning from feedback completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback/corrections")
async def get_corrections():
    """Аналіз виправлень"""
    try:
        return feedback_system.analyze_corrections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === Combined Learning Endpoint ===

@router.post("/learn-all")
async def learn_all():
    """Запустити всі системи навчання"""
    try:
        # 1. Аналіз патернів
        patterns = analytics.analyze_and_update_patterns()

        # 2. Навчання на звичках
        habit_learner.learn_from_analytics()
        habits = habit_learner.get_active_habits()

        # 3. Навчання на feedback
        feedback_system.learn_from_feedback()

        return {
            "ok": True,
            "message": "All learning systems completed",
            "results": {
                "patterns_found": len(patterns),
                "habits_found": len(habits),
                "feedback_processed": True
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
async def get_learning_dashboard():
    """Повна статистика для dashboard"""
    try:
        return {
            "analytics": analytics.get_dashboard_stats(),
            "habits": {
                "active": len(habit_learner.get_active_habits()),
                "preferences": len(habit_learner.get_preferences())
            },
            "feedback": feedback_system.get_feedback_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
