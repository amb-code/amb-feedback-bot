from unittest.mock import MagicMock

import pytest
from pytest_factoryboy import register
from telegram import PhotoSize

from tests.factories import (
    DbUserFactory,
    DbUserLogFactory,
    DbTopicFactory,
    DbMessageFactory,
    DbReplyFactory,
    TgUserFactory,
    TgChatFactory,
    TgMessageFactory,
    TgMessageOriginFactory,
    TgUpdateFactory,
)  # yapf: disable
from tests.factories.telegram import MockBot
from tests.utils.db import AsyncContextManagerWrapper, AsyncSessionMock


# Factories

register(TgUserFactory)
register(TgChatFactory)
register(TgMessageFactory)
register(TgUpdateFactory)

register(DbUserFactory)
register(DbUserLogFactory)
register(DbTopicFactory)
register(DbMessageFactory)
register(TgMessageOriginFactory)
register(DbReplyFactory)


# DB

@pytest.fixture(scope='function')
def sqlalchemy_declarative_base():
    from feedbackbot.core.db import Base

    return Base


@pytest.fixture(scope='function')
def session_wrapper(mocked_session):
    return MagicMock(
        return_value=AsyncContextManagerWrapper(
            AsyncSessionMock(mocked_session)
        )
    )


@pytest.fixture(scope='function')
def sqlalchemy_mock_config():
    return [
        ('users', [
            {
                'id': 1,
            },
            {
                'id': 2,
            },
            {
                'id': 3,
                'is_banned': True,
            },
        ]),
    ]


@pytest.fixture(scope='function', autouse=True)
def setup_factory_session(mocked_session):
    """
    Это важная часть, которая предоставляет сессию вем фабрикам. Поскольку сессия это фикстура, указать ее в классе
    фабрики возможности нет.
    """
    DbUserFactory._meta.sqlalchemy_session = mocked_session
    DbUserLogFactory._meta.sqlalchemy_session = mocked_session
    DbTopicFactory._meta.sqlalchemy_session = mocked_session
    DbMessageFactory._meta.sqlalchemy_session = mocked_session
    DbReplyFactory._meta.sqlalchemy_session = mocked_session


# Telegram

@pytest.fixture(scope='function')
def bot():
    return MockBot()


@pytest.fixture(scope='function')
def tg_photo_attachment(bot):
    photo_size = PhotoSize('a', 'b', 1, 1, 1)
    photo_size._bot = bot
    return photo_size
