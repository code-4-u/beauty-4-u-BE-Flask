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
    ORDERED = "구매"
    REFUND = "환불"
    TAKE_BACK = "반품"