import logging

from telegram import User as TGUser, Bot, Message

from feedbackbot import settings
from feedbackbot.topics.repos import TopicRepo
from feedbackbot.users.enums import UserLogField, UserLogValue
from feedbackbot.users.models import User as DBUser
from feedbackbot.users.repos import UserRepo, UserLogRepo

logger = logging.getLogger(__name__)


class UserService:
    USERLOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    FIELD_NAME_HUMAN_READABLE_MAPPING = {
        'full_name': 'полное имя',
        'username': 'имя пользователя',
        'is_banned': 'статус бана',
    }

    def __init__(self, bot: Bot, topic_repo: TopicRepo, user_repo: UserRepo, user_log_repo: UserLogRepo):
        self._bot = bot
        self._topic_repo = topic_repo
        self._user_repo = user_repo
        self._user_log_repo = user_log_repo

    async def get_or_create_user(self, tg_user: TGUser) -> DBUser:
        db_user = await self._user_repo.get(id=tg_user.id)

        if not db_user:
            db_user = await self._user_repo.create_user(tg_user.id)

        return db_user

    async def set_user_ban_by_topic(self, message_thread_id: int, ban_status: bool):
        """
        Забанить/разбанить пользователя данного топика по ID топика.
        """
        db_topic = await self._topic_repo.get_topic(message_thread_id)

        if db_topic:
            logger.debug(f'Setting user {db_topic.user_id} ban status  for the topic: {message_thread_id}')
            await self._user_repo.update_user(db_topic.user_id, is_banned=ban_status)
            await self._log_user_detail_change(
                db_topic.user_id,
                UserLogValue.TRUE.value if ban_status else UserLogValue.FALSE.value,
                UserLogField.IS_BANNED.value,
                db_topic.id
            )

        else:
            logger.debug(f'Not a tracked topic, no external user associated with it: {message_thread_id}')

    async def log_user_changes(self, tg_user: TGUser, topic_id: int):
        """
        Логгирует в базу и топик изменения деталей пользователя

        :param tg_user: объект пользователя Телеграм
        :param topic_id: ID топика для вывода оповещения об изменении
        """
        await self._log_user_detail_change(
            tg_user.id, tg_user.full_name,
            UserLogField.FULL_NAME.value,
            topic_id
        )
        # имя пользователя можно удалить совсем
        await self._log_user_detail_change(
            tg_user.id, tg_user.username or UserLogValue.EMPTY.value,
            UserLogField.USERNAME.value,
            topic_id
        )

    async def send_userlog_message(self, message_thread_id) -> Message:
        """
        Вывести в топик сообщение с информацией о пользователе и его изменениях.

        :param message_thread_id: ID топика для вывода юзерлога
        """
        db_topic = await self._topic_repo.get_topic(message_thread_id)

        if not db_topic:
            logger.warning(f'Not a tracked telegram topic, skipping: {message_thread_id}')

        user_info_msg = await self._build_user_info(db_topic.user_id)
        message = await self._bot.send_message(
            settings.CHAT_ID, message_thread_id=db_topic.id, text=user_info_msg, parse_mode='Markdown'
        )

        return message

    async def _log_user_detail_change(self, user_id: int, new_value: str, field_name: str, topic_id: int):
        prev_value = None

        logs = await self._user_log_repo.filter_user_logs(user_id, field_name)
        if logs:
            prev_value = logs[-1].value

        if new_value != prev_value:
            # оповещаем только если уже есть история
            if prev_value:
                await self._bot.send_message(
                    settings.CHAT_ID,
                    message_thread_id=topic_id,
                    text=(
                        f'Пользователь изменил поле "{self._get_hr_field_name(field_name)}": '
                        f'`{prev_value}` -> `{new_value}`'
                    ),
                    parse_mode='Markdown'
                )
            await self._user_log_repo.create_user_log(user_id, field=field_name, value=new_value)

    async def _build_user_info(self, user_id: int) -> str:
        all_logs = await self._user_log_repo.filter_user_logs(user_id, ordering=('timestamp', 'asc'))
        full_name_logs = list(filter(lambda e: e.field == UserLogField.FULL_NAME.value, all_logs))
        username_logs = list(filter(lambda e: e.field == UserLogField.USERNAME.value, all_logs))

        msg = (f'Пользователь {user_id}:\n'
               f'\n'
               f'*Первичная информация*\n'
               f'Полное имя: {full_name_logs[0].value}\n'
               f'Имя пользователя: '
               f'[@{self._escape_username(username_logs[0].value)}](tg://user?id={user_id})\n'
               f'\n')

        # если есть записи, кроме первичного лога
        if len(all_logs) > 2:
            msg += f'*Полная история изменений*\n'
            for log_record in all_logs[2:]:
                msg += (
                    f'- {log_record.timestamp.strftime(self.USERLOG_DATE_FORMAT)}: '
                    f'Поле "{self._get_hr_field_name(log_record.field)}" изменено на `{log_record.value}`\n'
                )

        return msg

    def _get_hr_field_name(self, field_name):
        return self.FIELD_NAME_HUMAN_READABLE_MAPPING.get(field_name) or field_name

    def _escape_username(self, s):
        return (
            s
            .replace('[', '')
            .replace(']', '')
        )
