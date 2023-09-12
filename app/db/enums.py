from enum import Enum


class CityEnum(str, Enum):
    Torino = "Torino"


class AnswerType(str, Enum):
    ai = "ai"
    blocked = "blocked"
    template = "template"
    unanswered = "unanswered"
