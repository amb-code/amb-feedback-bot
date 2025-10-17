from dependencies import Injector, value
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from feedbackbot import settings
from feedbackbot.common.handlers import StartCommandHandler, HelpCommandHandler
from feedbackbot.core.db import DBRefs
from feedbackbot.handlers import RootErrorHandler
from feedbackbot.topics.handlers import (
    ReplyMessageHandler, DeleteCommandHandler, DeleteHistoryCommandHandler
)
from feedbackbot.topics.repos import TopicRepo, ReplyRepo, MessageRepo
from feedbackbot.topics.services import TopicService
from feedbackbot.users.handlers import (
    ForwardMessageHandler, BanCommandHandler, UnbanCommandHandler, UserLogCommandHandler
)
from feedbackbot.users.repos import UserRepo, UserLogRepo
from feedbackbot.users.services import UserService


# noinspection PyMethodParameters
class DIAsync(Injector):
    db = DBRefs
    root_error_handler = RootErrorHandler

    # common
    start_command_handler = StartCommandHandler
    help_command_handler = HelpCommandHandler

    # users
    user_service = UserService
    user_repo = UserRepo
    user_log_repo = UserLogRepo

    forward_message_handler = ForwardMessageHandler
    ban_command_handler = BanCommandHandler
    unban_command_handler = UnbanCommandHandler
    userlog_command_handler = UserLogCommandHandler

    # topics
    topic_service = TopicService
    topic_repo = TopicRepo
    message_repo = MessageRepo
    reply_repo = ReplyRepo

    reply_message_handler = ReplyMessageHandler
    delete_command_handler = DeleteCommandHandler
    delete_history_command_handler = DeleteHistoryCommandHandler

    @value
    def engine():
        return create_async_engine(settings.DB_URI, echo=False, poolclass=NullPool)

    @value
    def session(engine):
        return async_sessionmaker(engine, expire_on_commit=False)
