from enum import Enum


class UserLogField(str, Enum):
    FULL_NAME = 'full_name'
    USERNAME = 'username'
    IS_BANNED = 'is_banned'


class UserLogValue(str, Enum):
    TRUE = 'да'
    FALSE = 'нет'
    EMPTY = '[пусто]'
