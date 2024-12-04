from enum import Enum


class AnalysisKind(Enum):
    ASSOCIATION = "ASSOCIATION"
    PERSONALIZED = "PERSONALIZED"

class CustomerGender(Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class CustomerGrade(Enum):
    BABY = "BABY"
    PINK = "PINK"
    GREEN = "GREEN"
    BLACK = "BLACK"
    GOLD = "GOLD"

class OrderState(Enum):
    PURCHASED = "PURCHASED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"