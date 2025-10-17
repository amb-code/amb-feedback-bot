from enum import Enum


class Role(str, Enum):
    ADMIN = "админ"
    OPERATOR = "оператор"
