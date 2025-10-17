import logging

from telegram import Update, Bot
from telegram.ext import ContextTypes

from feedbackbot import settings
from feedbackbot.core.handlers import BaseCommandHandler
from feedbackbot.topics.services import TopicService
from feedbackbot.users.constants import USER_BANNED
from feedbackbot.users.services import UserService

logger = logging.getLogger(__name__)


class ForwardMessageHandler:
    """ Обработчик сообщений от пользователя """

    def __init__(self, bot: Bot, user_service: UserService, topic_service: TopicService):
        self._bot = bot
        self._user_service = user_service
        self._topic_service = topic_service

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            # когда пользователь редактирует старое сообщение
            return

        tg_user = update.message.from_user

        db_user = await self._user_service.get_or_create_user(tg_user)

        # Проверяем бан
        if db_user.is_banned:
            await update.message.reply_text(USER_BANNED)
            return

        created, db_topic = await self._topic_service.get_or_create_user_topic(tg_user, db_user)

        await self._user_service.log_user_changes(tg_user, db_topic.id)

        # при создании топика прикрепляем начальную карточку пользователя
        if created:
            message = await self._user_service.send_userlog_message(db_topic.id)
            await self._bot.pin_chat_message(settings.CHAT_ID, message_id=message.id)

        await self._topic_service.forward_user_pm(update.message, db_topic)


class BanCommandHandler(BaseCommandHandler):
    name = 'ban'
    help = 'Забанить пользователя'

    def __init__(self, user_service: UserService):
        self._user_service = user_service

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            # когда оператор редактирует старое сообщение
            return

        await self._user_service.set_user_ban_by_topic(update.message.message_thread_id, True)


class UnbanCommandHandler(BaseCommandHandler):
    name = 'unban'
    help = 'Разбанить пользователя'

    def __init__(self, user_service: UserService):
        self._user_service = user_service

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # когда оператор редактирует старое сообщение
        if not update.message:
            return

        await self._user_service.set_user_ban_by_topic(update.message.message_thread_id, False)


class UserLogCommandHandler(BaseCommandHandler):
    name = 'userlog'
    help = 'Вывести историю изменений данных пользователя'

    def __init__(self, user_service: UserService):
        self._user_service = user_service

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # когда оператор редактирует старое сообщение
        if not update.message:
            return

        message_thread_id = update.message.message_thread_id
        await self._user_service.send_userlog_message(message_thread_id)

