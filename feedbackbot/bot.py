import logging.config
import warnings

import sentry_sdk
from ptbcontrib.roles import setup_roles
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from telegram import BotCommandScopeChat, BotCommandScopeChatAdministrators
from telegram.ext import Application, CommandHandler, MessageHandler, filters, AIORateLimiter

from feedbackbot import settings
from feedbackbot.core.di import DIAsync
from feedbackbot.core.db import Base
from feedbackbot.core.enums import Role
from feedbackbot.common.handlers import StartCommandHandler, HelpCommandHandler
from feedbackbot.users.handlers import BanCommandHandler, UnbanCommandHandler, UserLogCommandHandler
from feedbackbot.topics.handlers import DeleteCommandHandler, DeleteHistoryCommandHandler

logger = logging.getLogger(__name__)


# Отключаем ненужные варнинги в отношении форматирования MarkdownV2
warnings.filterwarnings(
    action='ignore',
    category=SyntaxWarning,
    module=r'.*common.handlers'
)


async def post_init(app: Application) -> None:
    # Logging
    if getattr(settings, 'LOGGING'):
        logging.config.dictConfig(settings.LOGGING)

    # DI
    logger.debug('POST-INIT: Setting up DI')
    di = DIAsync(bot=app.bot)

    # DB
    logger.debug('POST-INIT: Setting up DB')
    async with di.db.engine.begin() as con:
        await con.run_sync(Base.metadata.create_all)

    # Sentry
    logger.debug('POST-INIT: Setting up Sentry monitoring')
    if getattr(settings, 'SENTRY_DSN'):
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            send_default_pii=True,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            integrations=[
                AsyncioIntegration(),
            ],
            environment=settings.ENVIRONMENT,
        )

    # # Roles
    logger.debug('POST-INIT: Setting up roles')
    roles = setup_roles(app)

    # Handlers
    logger.debug('POST-INIT: Setting up handlers')
    app.add_handler(CommandHandler(StartCommandHandler.name, di.start_command_handler))
    app.add_handler(CommandHandler(HelpCommandHandler.name, di.help_command_handler))

    # users
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, di.forward_message_handler))

    app.add_handler(CommandHandler(BanCommandHandler.name, di.ban_command_handler))
    app.add_handler(CommandHandler(UnbanCommandHandler.name, di.unban_command_handler))
    app.add_handler(CommandHandler(UserLogCommandHandler.name, di.userlog_command_handler))

    # topics
    app.add_handler(MessageHandler(filters.REPLY, di.reply_message_handler))

    app.add_handler(CommandHandler(DeleteCommandHandler.name, di.delete_command_handler))
    app.add_handler(CommandHandler(DeleteHistoryCommandHandler.name, di.delete_history_command_handler))

    # обработчик ошибок
    app.add_error_handler(di.root_error_handler)

    # Commands
    logger.debug('POST-INIT: Setting up commands')

    # пользователь чата
    await app.bot.set_my_commands(
        [
            (StartCommandHandler.name, StartCommandHandler.help),
            (HelpCommandHandler.name, HelpCommandHandler.help),
        ],
    )

    # оператор чата
    await app.bot.set_my_commands(
        [
            (DeleteCommandHandler.name, DeleteCommandHandler.help_for_role(Role.OPERATOR.value)),
            (BanCommandHandler.name, BanCommandHandler.help_for_role(Role.OPERATOR.value)),
            (UnbanCommandHandler.name, UnbanCommandHandler.help_for_role(Role.OPERATOR.value)),
            (DeleteHistoryCommandHandler.name, DeleteHistoryCommandHandler.help_for_role(Role.OPERATOR.value)),
            (UserLogCommandHandler.name, UserLogCommandHandler.help_for_role(Role.OPERATOR.value)),
        ],
        scope=BotCommandScopeChat(chat_id=settings.CHAT_ID),
    )

    # админ
    await app.bot.set_my_commands(
        [
            (DeleteCommandHandler.name, DeleteCommandHandler.help_for_role(Role.ADMIN.value)),
            (BanCommandHandler.name, BanCommandHandler.help_for_role(Role.ADMIN.value)),
            (UnbanCommandHandler.name, UnbanCommandHandler.help_for_role(Role.ADMIN.value)),
            (DeleteHistoryCommandHandler.name, DeleteHistoryCommandHandler.help_for_role(Role.ADMIN.value)),
            (UserLogCommandHandler.name, UserLogCommandHandler.help_for_role(Role.ADMIN.value)),
        ],
        scope=BotCommandScopeChatAdministrators(chat_id=settings.CHAT_ID),
    )


    logger.info('POST-INIT: Bot ready, listening...')


app: Application = (
    Application
    .builder()
    .token(settings.TOKEN)
    .post_init(post_init)
    .rate_limiter(AIORateLimiter())
    .build()
)
