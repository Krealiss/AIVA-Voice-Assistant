"""
Sentiment Analyzer - аналіз настрою та емоцій в командах користувача
Визначає тон команди для адаптації відповідей AIVA
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger("sentiment_analyzer")


class Sentiment(Enum):
    """Типи настрою"""
    POSITIVE = "positive"      # Позитивний, дружній
    NEUTRAL = "neutral"        # Нейтральний
    NEGATIVE = "negative"      # Негативний, роздратований
    URGENT = "urgent"          # Терміново, важливо
    POLITE = "polite"          # Ввічливий, з проханням
    COMMAND = "command"        # Наказовий тон


class Emotion(Enum):
    """Типи емоцій"""
    HAPPY = "happy"            # Радість
    ANGRY = "angry"            # Злість
    FRUSTRATED = "frustrated"  # Роздратування
    CALM = "calm"              # Спокій
    EXCITED = "excited"        # Захоплення
    IMPATIENT = "impatient"    # Нетерпіння


@dataclass
class SentimentResult:
    """Результат аналізу настрою"""
    sentiment: Sentiment
    emotion: Optional[Emotion]
    confidence: float          # 0.0 - 1.0
    urgency_level: int         # 0-5 (0=низька, 5=критична)
    politeness_score: float    # 0.0 - 1.0
    markers: List[str]         # Знайдені маркери

    def to_dict(self) -> Dict[str, Any]:
        """Конвертує в словник"""
        return {
            "sentiment": self.sentiment.value,
            "emotion": self.emotion.value if self.emotion else None,
            "confidence": self.confidence,
            "urgency_level": self.urgency_level,
            "politeness_score": self.politeness_score,
            "markers": self.markers
        }


class SentimentAnalyzer:
    """Аналізатор настрою та емоцій"""

    def __init__(self):
        # Маркери позитивного настрою
        self.positive_markers = [
            "дякую", "спасибі", "чудово", "супер", "класно", "круто",
            "добре", "гарно", "відмінно", "прекрасно", "дуже добре",
            "thanks", "great", "awesome", "cool", "nice", "perfect"
        ]

        # Маркери негативного настрою
        self.negative_markers = [
            "не працює", "не виходить", "помилка", "проблема", "зламалось",
            "не можу", "не вдається", "погано", "жахливо", "кошмар",
            "doesn't work", "error", "problem", "broken", "bad", "terrible"
        ]

        # Маркери терміновості
        self.urgency_markers = {
            5: ["негайно", "зараз же", "терміново", "швидко", "immediately", "now", "urgent", "asap"],
            4: ["швидше", "поспішай", "скоріше", "hurry", "quick", "fast"],
            3: ["якнайшвидше", "як можна швидше", "as soon as possible"],
            2: ["коли зможеш", "при нагоді", "when you can"],
            1: ["потім", "пізніше", "later", "eventually"]
        }

        # Маркери ввічливості
        self.polite_markers = [
            "будь ласка", "прошу", "можеш", "міг би", "чи не міг би",
            "please", "could you", "would you", "can you", "may i"
        ]

        # Маркери наказового тону
        self.command_markers = [
            "зроби", "виконай", "запусти", "відкрий", "закрий", "вимкни",
            "do", "execute", "run", "open", "close", "shut down"
        ]

        # Маркери емоцій
        self.emotion_markers = {
            Emotion.HAPPY: ["ура", "ого", "вау", "йой", "yay", "wow", "yey"],
            Emotion.ANGRY: ["блін", "чорт", "damn", "hell", "wtf"],
            Emotion.FRUSTRATED: ["знову", "опять", "ще раз", "again", "still"],
            Emotion.EXCITED: ["!", "!!", "!!!", "круто", "супер", "awesome"],
            Emotion.IMPATIENT: ["ну", "давай", "швидше", "come on", "hurry"]
        }

        # Статистика
        self.stats = {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "urgent": 0,
            "polite": 0
        }

    def analyze(self, text: str) -> SentimentResult:
        """
        Аналізує настрій команди

        Args:
            text: Текст команди

        Returns:
            SentimentResult з повною інформацією
        """
        if not text or not text.strip():
            return SentimentResult(
                sentiment=Sentiment.NEUTRAL,
                emotion=None,
                confidence=1.0,
                urgency_level=0,
                politeness_score=0.5,
                markers=[]
            )

        text_lower = text.lower()
        markers_found = []

        # 1. Визначаємо базовий настрій
        sentiment, sentiment_confidence, sentiment_markers = self._detect_sentiment(text_lower)
        markers_found.extend(sentiment_markers)

        # 2. Визначаємо емоцію
        emotion, emotion_markers = self._detect_emotion(text_lower, text)
        markers_found.extend(emotion_markers)

        # 3. Визначаємо рівень терміновості
        urgency_level, urgency_markers = self._detect_urgency(text_lower)
        markers_found.extend(urgency_markers)

        # 4. Визначаємо ввічливість
        politeness_score, polite_markers = self._detect_politeness(text_lower)
        markers_found.extend(polite_markers)

        # 5. Коригуємо sentiment на основі інших факторів
        if urgency_level >= 4 and sentiment == Sentiment.NEUTRAL:
            sentiment = Sentiment.URGENT
            sentiment_confidence = 0.8

        if politeness_score > 0.7 and sentiment == Sentiment.NEUTRAL:
            sentiment = Sentiment.POLITE
            sentiment_confidence = 0.8

        # Оновлюємо статистику
        self.stats["total"] += 1
        self.stats[sentiment.value] = self.stats.get(sentiment.value, 0) + 1
        if urgency_level >= 3:
            self.stats["urgent"] += 1
        if politeness_score > 0.5:
            self.stats["polite"] += 1

        result = SentimentResult(
            sentiment=sentiment,
            emotion=emotion,
            confidence=sentiment_confidence,
            urgency_level=urgency_level,
            politeness_score=politeness_score,
            markers=markers_found
        )

        logger.info(
            f"😊 Sentiment: {sentiment.value}, emotion={emotion.value if emotion else None}, "
            f"urgency={urgency_level}, politeness={politeness_score:.2f}"
        )

        return result

    def _detect_sentiment(self, text: str) -> tuple[Sentiment, float, List[str]]:
        """Визначає базовий настрій"""
        positive_count = 0
        negative_count = 0
        markers = []

        # Рахуємо позитивні маркери
        for marker in self.positive_markers:
            if marker in text:
                positive_count += 1
                markers.append(f"+{marker}")

        # Рахуємо негативні маркери
        for marker in self.negative_markers:
            if marker in text:
                negative_count += 1
                markers.append(f"-{marker}")

        # Визначаємо настрій
        if positive_count > negative_count:
            confidence = min(0.6 + (positive_count * 0.1), 1.0)
            return Sentiment.POSITIVE, confidence, markers
        elif negative_count > positive_count:
            confidence = min(0.6 + (negative_count * 0.1), 1.0)
            return Sentiment.NEGATIVE, confidence, markers
        else:
            # Перевіряємо чи є наказовий тон
            for marker in self.command_markers:
                if text.startswith(marker):
                    return Sentiment.COMMAND, 0.7, [f"cmd:{marker}"]

            return Sentiment.NEUTRAL, 0.8, []

    def _detect_emotion(self, text: str, original_text: str) -> tuple[Optional[Emotion], List[str]]:
        """Визначає емоцію"""
        for emotion, markers in self.emotion_markers.items():
            for marker in markers:
                if marker in text or marker in original_text:
                    return emotion, [f"emo:{marker}"]

        return None, []

    def _detect_urgency(self, text: str) -> tuple[int, List[str]]:
        """Визначає рівень терміновості (0-5)"""
        for level, markers in sorted(self.urgency_markers.items(), reverse=True):
            for marker in markers:
                if marker in text:
                    return level, [f"urg:{marker}"]

        return 0, []

    def _detect_politeness(self, text: str) -> tuple[float, List[str]]:
        """Визначає рівень ввічливості (0.0-1.0)"""
        polite_count = 0
        markers = []

        for marker in self.polite_markers:
            if marker in text:
                polite_count += 1
                markers.append(f"polite:{marker}")

        # Базовий рівень 0.5, +0.2 за кожен маркер
        score = min(0.5 + (polite_count * 0.2), 1.0)

        return score, markers

    def get_response_style(self, sentiment_result: SentimentResult) -> Dict[str, Any]:
        """
        Повертає рекомендований стиль відповіді на основі sentiment

        Returns:
            Dict з рекомендаціями для формування відповіді
        """
        style = {
            "tone": "neutral",
            "formality": "normal",
            "speed": "normal",
            "empathy": False,
            "suggestions": []
        }

        # Адаптуємо тон
        if sentiment_result.sentiment == Sentiment.POSITIVE:
            style["tone"] = "friendly"
            style["suggestions"].append("Додати позитивну емоцію")

        elif sentiment_result.sentiment == Sentiment.NEGATIVE:
            style["tone"] = "supportive"
            style["empathy"] = True
            style["suggestions"].append("Запропонувати допомогу")

        elif sentiment_result.sentiment == Sentiment.URGENT:
            style["speed"] = "fast"
            style["suggestions"].append("Відповісти швидко, без зайвих деталей")

        elif sentiment_result.sentiment == Sentiment.POLITE:
            style["formality"] = "polite"
            style["suggestions"].append("Відповісти ввічливо")

        # Адаптуємо на основі терміновості
        if sentiment_result.urgency_level >= 4:
            style["speed"] = "immediate"
            style["suggestions"].append("Пріоритет виконання")

        # Адаптуємо на основі ввічливості
        if sentiment_result.politeness_score > 0.7:
            style["formality"] = "polite"

        return style

    def get_stats(self) -> Dict[str, Any]:
        """Повертає статистику аналізу"""
        total = self.stats["total"]
        if total == 0:
            return self.stats

        return {
            **self.stats,
            "positive_rate": (self.stats.get("positive", 0) / total * 100),
            "negative_rate": (self.stats.get("negative", 0) / total * 100),
            "urgent_rate": (self.stats["urgent"] / total * 100),
            "polite_rate": (self.stats["polite"] / total * 100)
        }


# Глобальний екземпляр
sentiment_analyzer = SentimentAnalyzer()
