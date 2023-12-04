from enum import Enum


class CityEnum(str, Enum):
    Torino = "Torino"


class AnswerType(str, Enum):
    """Type of answers to send to the user."""

    ai = "ai"  # ai answer with events recommendations
    blocked = "blocked"  # ai blocked message for invalid query
    conversational = "conversational"  # ai conversational answer
    failed = "failed"  # answer failed to be elaborated
    template = "template"  # template message
    unanswered = "unanswered"  # no answer delivered


class PriceLevel(str, Enum):
    free = "Free"
    inexpensive = "€"
    moderate = "€€"
    expensive = "€€€"
    very_expensive = "€€€€"
