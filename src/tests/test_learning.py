"""
Тести для системи самонавчання
"""
import pytest
import os
import tempfile
from datetime import datetime, timedelta

from analytics_engine import AnalyticsEngine, CommandMetric
from habit_learner import HabitLearner, Habit
from feedback_system import FeedbackSystem, Feedback, FeedbackType

# === Analytics Tests ===

@pytest.fixture
def analytics_db():
    """Тимчасова БД для тестів"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)

def test_analytics_track_command(analytics_db):
    """Тест запису метрики"""
    analytics = AnalyticsEngine(analytics_db)

    metric = CommandMetric(
        command="запусти chrome",
        intent_type="run",
        success=True,
        duration_ms=150.5,
        timestamp=datetime.now(),
        source="voice"
    )

    analytics.track_command(metric)

    stats = analytics.get_success_rate(hours=1)
    assert stats["total_commands"] == 1
    assert stats["successful"] == 1

def test_analytics_success_rate(analytics_db):
    """Тест підрахунку success rate"""
    analytics = AnalyticsEngine(analytics_db)

    # 3 успішні, 1 невдала
    for i in range(3):
        analytics.track_command(CommandMetric(
            command=f"test {i}",
            intent_type="run",
            success=True,
            duration_ms=100,
            timestamp=datetime.now(),
            source="voice"
        ))

    analytics.track_command(CommandMetric(
        command="failed",
        intent_type="run",
        success=False,
        duration_ms=50,
        timestamp=datetime.now(),
        source="voice"
    ))

    stats = analytics.get_success_rate(hours=1)
    assert stats["total_commands"] == 4
    assert stats["successful"] == 3
    assert stats["failed"] == 1
    assert stats["success_rate"] == 75.0

def test_analytics_performance_stats(analytics_db):
    """Тест статистики продуктивності"""
    analytics = AnalyticsEngine(analytics_db)

    durations = [100, 200, 300]
    for d in durations:
        analytics.track_command(CommandMetric(
            command="test",
            intent_type="run",
            success=True,
            duration_ms=d,
            timestamp=datetime.now(),
            source="voice"
        ))

    stats = analytics.get_performance_stats(hours=1)
    assert stats["avg_duration_ms"] == 200.0
    assert stats["min_duration_ms"] == 100
    assert stats["max_duration_ms"] == 300

def test_analytics_top_commands(analytics_db):
    """Тест топ команд"""
    analytics = AnalyticsEngine(analytics_db)

    # Chrome 3 рази, Steam 2 рази
    for _ in range(3):
        analytics.track_command(CommandMetric(
            command="запусти chrome",
            intent_type="run",
            success=True,
            duration_ms=100,
            timestamp=datetime.now(),
            source="voice"
        ))

    for _ in range(2):
        analytics.track_command(CommandMetric(
            command="запусти steam",
            intent_type="run",
            success=True,
            duration_ms=100,
            timestamp=datetime.now(),
            source="voice"
        ))

    top = analytics.get_top_commands(limit=2)
    assert len(top) == 2
    assert top[0][0] == "запусти chrome"
    assert top[0][1] == 3

def test_analytics_pattern_detection(analytics_db):
    """Тест виявлення патернів"""
    analytics = AnalyticsEngine(analytics_db)

    # Створюємо патерн: команда о 9:00
    now = datetime.now().replace(hour=9, minute=0)
    for _ in range(5):
        analytics.track_command(CommandMetric(
            command="запусти vscode",
            intent_type="run",
            success=True,
            duration_ms=100,
            timestamp=now,
            source="voice"
        ))

    patterns = analytics.detect_time_patterns(min_occurrences=3)
    assert len(patterns) > 0
    assert any(p.pattern_type == "time_of_day" for p in patterns)

# === Habit Learner Tests ===

@pytest.fixture
def habit_db():
    """Тимчасова БД для звичок"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)

@pytest.fixture
def habit_analytics_db():
    """Тимчасова analytics БД"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Заповнюємо тестовими даними
    analytics = AnalyticsEngine(path)
    now = datetime.now().replace(hour=9)

    for _ in range(5):
        analytics.track_command(CommandMetric(
            command="запусти vscode",
            intent_type="run",
            success=True,
            duration_ms=100,
            timestamp=now,
            source="voice"
        ))

    yield path
    os.unlink(path)

def test_habit_learner_time_routine(habit_db, habit_analytics_db):
    """Тест виявлення рутини за часом"""
    learner = HabitLearner(habit_db, habit_analytics_db)
    learner.learn_from_analytics()

    habits = learner.get_active_habits(min_confidence=0.3)
    assert len(habits) > 0

    routine_habits = [h for h in habits if h.habit_type == "routine"]
    assert len(routine_habits) > 0

def test_habit_interaction_accepted(habit_db, habit_analytics_db):
    """Тест прийняття звички"""
    learner = HabitLearner(habit_db, habit_analytics_db)
    learner.learn_from_analytics()

    habits = learner.get_active_habits()
    if habits:
        habit = habits[0]
        initial_confidence = habit.confidence

        learner.record_interaction(habit.habit_id, "accepted")

        updated_habits = learner.get_active_habits()
        updated_habit = next(h for h in updated_habits if h.habit_id == habit.habit_id)

        assert updated_habit.times_accepted == 1
        assert updated_habit.confidence >= initial_confidence

def test_habit_interaction_rejected(habit_db, habit_analytics_db):
    """Тест відхилення звички"""
    learner = HabitLearner(habit_db, habit_analytics_db)
    learner.learn_from_analytics()

    habits = learner.get_active_habits()
    if habits:
        habit = habits[0]

        # Відхиляємо 3 рази
        for _ in range(3):
            learner.record_interaction(habit.habit_id, "rejected")

        # Звичка має бути деактивована
        updated_habits = learner.get_active_habits()
        assert not any(h.habit_id == habit.habit_id for h in updated_habits)

def test_habit_preferences(habit_db, habit_analytics_db):
    """Тест вподобань"""
    learner = HabitLearner(habit_db, habit_analytics_db)
    learner.learn_from_analytics()

    prefs = learner.get_preferences("favorite_app")
    assert len(prefs) > 0

# === Feedback System Tests ===

@pytest.fixture
def feedback_db():
    """Тимчасова БД для feedback"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)

def test_feedback_submit(feedback_db):
    """Тест подачі feedback"""
    system = FeedbackSystem(feedback_db)

    feedback = Feedback(
        feedback_id=None,
        feedback_type=FeedbackType.RATING.value,
        command="запусти chrome",
        response="Запускаю Chrome",
        user_input="",
        rating=5,
        comment="Відмінно!",
        timestamp=datetime.now()
    )

    feedback_id = system.submit_feedback(feedback)
    assert feedback_id > 0

def test_feedback_rating(feedback_db):
    """Тест оцінки"""
    system = FeedbackSystem(feedback_db)

    system.rate_response("test command", "test response", 5)
    system.rate_response("test command", "test response", 3)

    avg = system.get_average_rating(days=1)
    assert avg == 4.0

def test_feedback_low_rated_commands(feedback_db):
    """Тест команд з низькими оцінками"""
    system = FeedbackSystem(feedback_db)

    # Низька оцінка для однієї команди
    for _ in range(3):
        system.rate_response("bad command", "bad response", 1)

    low_rated = system.get_low_rated_commands(threshold=2)
    assert len(low_rated) > 0
    assert low_rated[0]["command"] == "bad command"

def test_feedback_stats(feedback_db):
    """Тест статистики feedback"""
    system = FeedbackSystem(feedback_db)

    system.rate_response("cmd1", "resp1", 5)
    system.rate_response("cmd2", "resp2", 3)
    system.report_error("cmd3", "resp3", "Error occurred")

    stats = system.get_feedback_stats()
    assert stats["total_feedback"] == 3
    assert stats["average_rating"] > 0
    assert "rating" in stats["by_type"]
    assert "complaint" in stats["by_type"]

def test_feedback_learn(feedback_db):
    """Тест навчання на feedback"""
    system = FeedbackSystem(feedback_db)

    system.rate_response("cmd1", "resp1", 1, "Bad response")
    system.rate_response("cmd2", "resp2", 5, "Great!")

    system.learn_from_feedback()

    stats = system.get_feedback_stats()
    assert stats["processed"] == 2
