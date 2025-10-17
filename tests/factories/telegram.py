__all__ = ('MockBot', 'TgUserFactory', 'TgChatFactory', 'TgMessageFactory', 'TgMessageOriginFactory', 'TgUpdateFactory')

from unittest.mock import AsyncMock

import factory
import factory.fuzzy
from faker import Faker
from telegram import Update, Message, Chat, User, ForumTopic, MessageOrigin
from telegram.constants import ChatType

fake = Faker()


class MockBot:
    def __init__(self):
        self.sent_messages = []
        self.forwarded_messages = []
        self.edited_messages = []
        self.attachment_file = AsyncMock()

    async def send_message(self, *args, **kwargs):
        init_kwargs = {}

        if kwargs.get('text'):
            init_kwargs.update({'text': kwargs['text']})

        msg = TgMessageFactory(**init_kwargs)
        msg._bot = self

        self.sent_messages.append(msg)

        return msg

    async def send_photo(self, *args, **kwargs):
        msg = TgMessageFactory()
        msg._bot = self

        self.sent_messages.append(msg)

        return msg

    async def forward_message(self, *args, **kwargs):
        msg = TgMessageFactory()
        msg._bot = self

        self.forwarded_messages.append(msg)

        return msg

    async def delete_message(self, *args, **kwargs):
        pass

    async def pin_chat_message(self, *args, **kwargs):
        pass

    async def create_forum_topic(self, *args, **kwargs):
        topic = TgForumTopicFactory()
        return topic

    async def edit_forum_topic(self, *args, **kwargs):
        topic = TgForumTopicFactory()
        return topic

    async def get_file(self, *args, **kwargs):
        return self.attachment_file

    async def edit_message_text(self, *args, **kwargs):
        init_kwargs = {}

        if kwargs.get('text'):
            init_kwargs.update({'text': kwargs['text']})

        msg = TgMessageFactory(**init_kwargs)
        msg._bot = self

        self.edited_messages.append(msg)

        return msg

    async def edit_message_media(self, *args, **kwargs):
        msg = TgMessageFactory()
        msg._bot = self

        self.edited_messages.append(msg)

        return msg


class TgUserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    first_name = factory.Faker('word')
    last_name = factory.Faker('word')
    username = factory.Faker('word')
    is_bot = False


class TgChatFactory(factory.Factory):
    class Meta:
        model = Chat

    id = factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    type = factory.fuzzy.FuzzyChoice([v for v in ChatType])


class TgMessageFactory(factory.Factory):
    class Meta:
        model = Message

    bot = factory.LazyFunction(MockBot)
    message_id = factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    date = factory.Faker('date_time')
    chat = factory.SubFactory(TgChatFactory)
    from_user = factory.SubFactory(TgUserFactory)
    message_thread_id = factory.Faker('pyint', min_value=100, max_value=999)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        try:
            bot = kwargs.pop('bot')
        except KeyError:
            bot = MockBot()

        obj = model_class(*args, **kwargs)

        if obj._bot is None:
            obj._bot = bot

        return obj


class TgMessageOriginFactory(factory.Factory):
    class Meta:
        model = MessageOrigin

    type = factory.Faker('word')
    date = factory.Faker('date_time')


class TgUpdateFactory(factory.Factory):
    class Meta:
        model = Update

    bot = factory.LazyFunction(MockBot)
    update_id = factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    message = factory.SubFactory(TgMessageFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        try:
            bot = kwargs.pop('bot')
        except KeyError:
            bot = MockBot()

        obj = model_class(*args, **kwargs)
        if obj.message and obj.message._bot is None:
            obj.message._bot = bot

        if obj.edited_message and obj.edited_message._bot is None:
            obj.edited_message._bot = bot

        return obj


class TgForumTopicFactory(factory.Factory):
    class Meta:
        model = ForumTopic

    message_thread_id =  factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    name = factory.Faker('word')
    icon_color = 112233
