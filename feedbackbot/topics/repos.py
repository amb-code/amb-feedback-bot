from feedbackbot.core.db import BaseAsyncDBRepo
from feedbackbot.topics.models import Topic, Reply, Message
from feedbackbot.users.models import User


class TopicRepo(BaseAsyncDBRepo[Topic]):
    model_class = Topic

    async def create_topic(self, topic_id: int, user: User):
        return await self.create(
            id=topic_id,
            user=user
        )

    async def get_topic(self, topic_id: int):
        return await self.get(id=topic_id)

    async def filter_topics(self, user: User | int | None = None, **kwargs):
        return await self.filter(user=user, **kwargs)


class MessageRepo(BaseAsyncDBRepo[Message]):
    model_class = Message

    async def create_message(self, message_id: int, bot_message_id: int, topic: Topic):
        return await self.create(
            id=message_id,
            bot_message_id=bot_message_id,
            topic=topic,
        )

    async def get_message(self, message_id: int):
        return await self.get(id=message_id)

    async def filter_messages(self, bot_message_id: int | None = None, topic_id: int | None = None):
        return await self.filter(bot_message_id=bot_message_id, topic_id=topic_id)

    async def delete_message(self, message_id: int):
        return await self.delete(self.model_class.id==message_id)


class ReplyRepo(BaseAsyncDBRepo[Reply]):
    model_class = Reply

    async def create_reply(self, reply_id: int, bot_message_id: int, topic: Topic):
        return await self.create(
            id=reply_id,
            bot_message_id=bot_message_id,
            topic=topic,
        )

    async def get_reply(self, reply_id: int):
        return await self.get(id=reply_id)

    async def filter_replies(self, bot_message_id: int | None = None, topic_id: int | None = None):
        return await self.filter(bot_message_id=bot_message_id, topic_id=topic_id)

    async def delete_reply(self, reply_id: int):
        return await self.delete(self.model_class.id==reply_id)
