from enum import Enum


class AnalysisKind(Enum):
    TYPE_APRIORI = "APRIORI"
    TYPE_COLLABORATIVE = "COLLABORATIVE"


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
    PURCHASED = "구매"
    REFUNDED = "환불"
    CANCELLED = "취소"