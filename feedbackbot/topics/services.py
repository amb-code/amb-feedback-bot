import logging
from uuid import uuid4

from telegram import Bot, Chat, User as TGUser, Message, InputMediaPhoto
from telegram.error import Forbidden, BadRequest

from feedbackbot import settings
from feedbackbot.topics.constants import UNSUPPORTED_CONTENT
from feedbackbot.users.constants import USER_BLOCKED_BOT
from feedbackbot.users.models import User as DBUSer
from feedbackbot.topics.models import Topic
from feedbackbot.topics.repos import TopicRepo, ReplyRepo, MessageRepo

logger = logging.getLogger(__name__)


class TopicService:

    def __init__(self, bot: Bot, topic_repo: TopicRepo, message_repo: MessageRepo, reply_repo: ReplyRepo):
        self._bot = bot
        self._chat = Chat(settings.CHAT_ID, Chat.SUPERGROUP)

        self._topic_repo = topic_repo
        self._reply_repo = reply_repo
        self._message_repo = message_repo

    async def get_or_create_user_topic(self, tg_user: TGUser, db_user: DBUSer) -> tuple[bool, Topic]:
        topic_name = f'{tg_user.full_name} ({tg_user.username})'
        db_topics = await self._topic_repo.filter_topics(db_user, ordering=('id', 'desc'))

        # 1 вариант: топиков нет, и мы создаем новый
        if not db_topics:
            tg_topic = await self._bot.create_forum_topic(settings.CHAT_ID, topic_name)
            db_topic = await self._topic_repo.create_topic(tg_topic.message_thread_id, db_user)
            return True, db_topic

        # Топики создаются в возрастающем порядке, мы всегда берем последний созданный.
        # Такая ситуация может возникнуть если оператор удалил предыдущий чат, а пользователь снова написал.
        db_topic = db_topics[0]
        try:
            await self._bot.edit_forum_topic(settings.CHAT_ID, db_topic.id, name=topic_name)

        except BadRequest as e:
            # 2 вариант: топик есть в базе и в телеге
            if e.message == 'Topic_not_modified':
                return False, db_topic

            # 3 вариант: топик есть в базе, но был удален в телеге
            if e.message == 'Topic_id_invalid':
                tg_topic = await self._bot.create_forum_topic(settings.CHAT_ID, topic_name)
                db_topic = await self._topic_repo.create_topic(tg_topic.message_thread_id, db_user)
                return True, db_topic

            else:
                raise

        # 4 вариант: топик есть в базе и в телеге, но оператор переименовал его
        return False, db_topic

    async def forward_user_pm(self, message: Message, db_topic: Topic):
        """
        Метод перенаправляет сообщение пользователя из чата пользователь-бот в чат операторов.

        :param message: Оригинальное сообщение пользователя
        :param db_topic: ID топика
        """
        bot_message = await message.forward(chat_id=settings.CHAT_ID, message_thread_id=db_topic.id)
        await self._message_repo.create_message(message.id, bot_message.id, db_topic)

    async def reply_user_pm(self, message: Message):
        """
        Отправляет ответ пользователю и логирует ответ в базу.

        :param message: Пользовательское сообщение, на которое мы отвечаем
        """
        db_topic = await self._topic_repo.get_topic(message.message_thread_id)

        if not db_topic:
            logger.warning(f'Not a tracked telegram topic, skipping: {message.message_thread_id}')
            return

        try:
            if message.text:
                bot_message = await self._bot.send_message(chat_id=db_topic.user.id, text=message.text)

            elif message.photo:
                if not settings.TMP_PATH.exists():
                    settings.TMP_PATH.mkdir(parents=True, exist_ok=True)
                save_path = settings.TMP_PATH / str(uuid4())
                msg_file = await message.effective_attachment[-1].get_file()
                dl_file = await msg_file.download_to_drive(save_path)
                bot_message = await self._bot.send_photo(
                    chat_id=db_topic.user.id,
                    photo=dl_file,
                    caption=message.caption
                )
                dl_file.unlink(missing_ok=True)

            else:
                await message.reply_text(UNSUPPORTED_CONTENT)
                return

            await self._reply_repo.create_reply(
                message.id,
                bot_message_id=bot_message.id,
                topic=db_topic
            )

        except Forbidden:
            await message.reply_text(USER_BLOCKED_BOT)

    async def edit_operator_reply(self, message: Message):
        """
        Редактирует ответ оператора.

        :param message: edited_message на оригинальное сообщение оператора
        """
        db_topic = await self._topic_repo.get_topic(message.message_thread_id)
        db_reply = await self._reply_repo.get_reply(message.id)

        if not db_topic:
            logger.warning(f'Not a tracked telegram topic, skipping: {message.message_thread_id}')
            return
        if not db_reply:
            logger.warning(f'Not a tracked telegram message, skipping: {message.id}')
            return

        try:
            if message.text:
                bot_message = await self._bot.edit_message_text(
                    text=message.text,
                    chat_id=db_topic.user.id,
                    message_id=db_reply.bot_message_id
                )

            elif message.photo:
                # Для редактирования медиа нужно использовать file_id
                # Сначала получаем file_id из оригинального фото
                photo_file_id = message.effective_attachment[-1].file_id
                media = InputMediaPhoto(media=photo_file_id, caption=message.caption)
                bot_message = await self._bot.edit_message_media(
                    media=media,
                    chat_id=db_topic.user.id,
                    message_id=db_reply.bot_message_id
                )

            else:
                await message.reply_text(UNSUPPORTED_CONTENT)
                return

        except Forbidden:
            await message.reply_text(USER_BLOCKED_BOT)

    async def delete_message_user(self, message_id: int):
        """
        Удаляет собственное сообщение пользователя

        :param message_id: ID оригинального сообщения пользователя
        """
        db_message = await self._message_repo.get_message(message_id)

        # Удаляем только если сообщение есть в базе
        if db_message:
            db_topic = await self._topic_repo.get_topic(db_message.topic_id)
            await self._bot.delete_message(db_topic.user.id, db_message.id)
            await self._message_repo.delete_message(db_message.id)
            await self._bot.delete_message(settings.CHAT_ID, db_message.bot_message_id)
        else:
            logger.debug(f'delete_message_user: Not a tracked message')

    async def delete_message_operator(self, message_id: int):
        """
        Удаление сообщения пользователя оператором.

        :param message_id: ID перенаправленного сообщения от пользователя (сообщение бота)
        """
        db_messages = await self._message_repo.filter_messages(bot_message_id=message_id)

        # Удаляем только если сообщение есть в базе
        if db_messages:
            # В пользовательском чате у этого сообщения есть одно соответствие
            db_message = db_messages[0]
            db_topic = await self._topic_repo.get_topic(db_message.topic_id)
            await self._bot.delete_message(db_topic.user.id, db_message.id)
            # решено, что оператор чата чистит руками
            # await self._bot.delete_message(settings.CHAT_ID, message_id)
            await self._message_repo.delete_message(db_message.id)
        else:
            logger.debug(f'delete_message_operator: Not a tracked message')

    async def delete_reply(self, message_id: int):
        """
        Удаление ответа оператора

        :param message_id: ID сообщения оператора
        :return:
        """
        db_reply = await self._reply_repo.get_reply(message_id)

        # Удаляем только если ответ еще не удален
        if db_reply:
            db_topic = await self._topic_repo.get_topic(db_reply.topic_id)
            await self._bot.delete_message(db_topic.user.id, db_reply.bot_message_id)
            # решено, что оператор чата чистит руками
            # await self._bot.delete_message(settings.CHAT_ID, message_id)
            await self._reply_repo.delete_reply(db_reply.id)
        else:
            logger.debug(f'delete_reply: Not a tracked reply')

    async def delete_history(self, message_thread_id: int):
        db_topic = await self._topic_repo.get_topic(message_thread_id)
        db_messages = await self._message_repo.filter_messages(topic_id=db_topic.id)
        db_replies = await self._reply_repo.filter_replies(topic_id=db_topic.id)

        for db_message in db_messages:
            await self._bot.delete_message(db_topic.user.id, db_message.id)
            await self._message_repo.delete_message(db_message.id)

        for db_reply in db_replies:
            await self._bot.delete_message(db_topic.user.id, db_reply.bot_message_id)
            await self._reply_repo.delete_reply(db_reply.id)
