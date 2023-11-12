from enum import Enum


class CityEnum(str, Enum):
    Torino = "Torino"


class AnswerType(str, Enum):
    ai = "ai"
    blocked = "blocked"
    template = "template"
    failed = "failed"
    unanswered = "unanswered"


class PriceLevel(str, Enum):
    free = "Free"
    inexpensive = "€"
    moderate = "€€"
    expensive = "€€€"
    very_expensive = "€€€€"
