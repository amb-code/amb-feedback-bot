import logging

from telegram import Update
from telegram.ext import ContextTypes

from feedbackbot import settings
from feedbackbot.core.handlers import BaseCommandHandler
from feedbackbot.topics.services import TopicService

logger = logging.getLogger(__name__)

class ReplyMessageHandler:
    """
    Обработчик сообщений оператора чата пользователю.

    Несколько важных пунктов:

    1. Все сообщения в топике считаются ответами: то есть подходят под фильтр filters.REPLY
    2. У форварднутого сообщения от пользователя будет update.message.reply_to_message.api_kwargs['forward_date'] или
       есть update.message.reply_to_message.forward_origin
    3. Из форвардов нас интересует тот, у которого reply_to_message.from_user.id == id бота (бот делал форвард)
    """
    def __init__(self, topic_service: TopicService):
        self._service = topic_service

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Редактируем
        if update.message is None and update.edited_message is not None:
            is_reply_to_bot_forwarded = update.edited_message.reply_to_message.from_user.id == settings.BOT_ID
            if is_reply_to_bot_forwarded:
                await self._service.edit_operator_reply(update.edited_message)

        # Отвечаем
        else:
            is_reply_to_bot_forwarded = update.message.reply_to_message.from_user.id == settings.BOT_ID
            is_forwarded = getattr(update.message.reply_to_message, 'forward_origin', None) is not None

            # Отвечаем только если это форвард от бота
            if is_forwarded and is_reply_to_bot_forwarded:
                await self._service.reply_user_pm(update.message)


class DeleteCommandHandler(BaseCommandHandler):
    """
    Команда удаления единичного сообщения.

    Доступна только операторам чата, поскольку учет пользовательских сообщений не ведется.
    """
    name = 'delete'
    help = 'Удалить ответ'

    def __init__(self, topic_service: TopicService):
        self._topic_service = topic_service

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # когда оператор редактирует старое сообщение
        if not update.message:
            return

        target_message = update.message.reply_to_message.message_id
        logger.debug(f'Deleting a message: {target_message}')

        # Проверяем, что команда – ответ на сообщение
        if update.message.reply_to_message is None:
            return

        # Сообщение пользователя в чате с ботом
        is_user_own_message = update.message.chat.id == update.message.from_user.id
        # Форвард ботом сообщения пользователя
        is_user_forwarded_message = getattr(update.message.reply_to_message, 'forward_origin', None) is not None
        # Ответ оператора в операторском чате
        is_operator_reply = update.message.reply_to_message.from_user.id == update.message.from_user.id

        if not (is_user_own_message or is_user_forwarded_message or is_operator_reply):
            return

        # решено, что пользователь не может удалять свои сообщения
        # if is_user_own_message:
        #     logger.debug('Deleting as user own message')
        #     await self._topic_service.delete_message_user(target_message)
        if is_user_forwarded_message:
            logger.debug('Deleting as user message by operator')
            await self._topic_service.delete_message_operator(target_message)
        elif is_operator_reply:
            logger.debug('Deleting as operator reply')
            await self._topic_service.delete_reply(target_message)
        else:
            logger.debug(f'Message cannot be deleted by the requester: {target_message}')


class DeleteHistoryCommandHandler(BaseCommandHandler):
    name = 'delhistory'
    help = 'Очистить историю у пользователя'

    def __init__(self, topic_service: TopicService):
        self._topic_service = topic_service

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # когда оператор редактирует старое сообщение
        if not update.message:
            return

        topic_id = update.message.message_thread_id
        logger.debug(f'Deleting user history for topic: {topic_id}')

        await self._topic_service.delete_history(topic_id)
