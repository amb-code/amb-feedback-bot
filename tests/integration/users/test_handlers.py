import datetime

import pytest
from pytest_mock import MockerFixture
from telegram import Update

from feedbackbot.core.di import DIAsync
from feedbackbot.topics.models import Topic, Message
from feedbackbot.users.handlers import (
    ForwardMessageHandler, BanCommandHandler, UnbanCommandHandler,
    UserLogCommandHandler
)
from feedbackbot.users.models import User, UserLog


class TestForwardMessageHandler:

    @pytest.fixture(autouse=True)
    def setup_method(self, bot, session_wrapper):
        self.under_test: ForwardMessageHandler = DIAsync(
            session=session_wrapper,
            bot=bot,
        ).forward_message_handler

    @pytest.mark.asyncio
    async def test_call_happy_path_new_topic(self, mocker: MockerFixture, bot, mocked_session, tg_update_factory):
        # given
        tg_update: Update = tg_update_factory()
        expected_user_id = tg_update.message.from_user.id
        expected_user_full_name = tg_update.message.from_user.full_name
        expected_user_username = tg_update.message.from_user.username

        mocker.spy(bot, 'send_message')
        mocker.spy(bot, 'pin_chat_message')

        # when
        await self.under_test(tg_update, {})

        # then
        # пользователь создан
        actual_user = mocked_session.query(User).filter_by(id=tg_update.message.from_user.id).first()
        assert actual_user is not None
        assert actual_user.id == expected_user_id

        # топик создан
        actual_topics = mocked_session.query(Topic).filter_by(user_id=actual_user.id).all()
        # только один
        assert len(actual_topics) == 1
        actual_topic = actual_topics[0]
        assert actual_topic is not None
        assert actual_topic.user_id == expected_user_id

        # начальные логи созданы: полное имя и username
        actual_logs = mocked_session.query(UserLog).filter_by(user_id=actual_user.id).all()
        assert len(actual_logs) == 2
        assert actual_logs[0].field == 'full_name'
        assert actual_logs[0].value == expected_user_full_name
        assert actual_logs[1].field == 'username'
        assert actual_logs[1].value == expected_user_username

        # начальная информация отправлена в чат
        # call('-1002173328097', message_thread_id=1, text='Пользователь 2181914066:\n\n*Первичная информация*\n
        # Полное имя: black number\nИмя пользователя: [@return](tg://user?id=2181914066)\n\n', parse_mode='Markdown')
        bot.send_message.assert_called_once()

        # сообщение закреплено
        bot.pin_chat_message.assert_called_once()

        # сообщение создано
        actual_messages = mocked_session.query(Message).filter_by(topic_id=actual_topic.id).all()
        assert len(actual_messages) == 1

    @pytest.mark.asyncio
    async def test_call_happy_path_existing_topic(self, mocker: MockerFixture, bot, mocked_session, tg_update_factory, db_user_factory, db_topic_factory):
        # given
        tg_update: Update = tg_update_factory()
        db_user = db_user_factory(id=tg_update.message.from_user.id)
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        mocker.spy(bot, 'send_message')
        mocker.spy(bot, 'pin_chat_message')

        # when
        await self.under_test(tg_update, {})

        # then
        # пользователь уже существует, новый не создан
        actual_user = mocked_session.query(User).filter_by(id=tg_update.message.from_user.id).first()
        assert actual_user is not None

        # топик уже существует
        actual_topics = mocked_session.query(Topic).filter_by(user_id=actual_user.id).all()
        assert len(actual_topics) == 1

        # начальная информация не отправляется повторно
        bot.send_message.assert_not_called()

        # сообщение не закрепляется повторно
        bot.pin_chat_message.assert_not_called()

        # сообщение добавлено в существующий топик
        actual_messages = mocked_session.query(Message).filter_by(topic_id=actual_topics[0].id).all()
        assert len(actual_messages) == 1

    @pytest.mark.asyncio
    async def test_call_user_is_banned(self, mocker: MockerFixture, tg_update_factory, db_user_factory,
                                       db_topic_factory):  # yapf: disable
        # given
        tg_update: Update = tg_update_factory()
        db_user = db_user_factory(id=tg_update.message.from_user.id, is_banned=True)
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        mocker.spy(self.under_test._topic_service, 'get_or_create_user_topic')
        mocker.spy(self.under_test._user_service, 'log_user_changes')
        mocker.spy(self.under_test._topic_service, 'forward_user_pm')

        # when
        await self.under_test(tg_update, {})

        # then
        self.under_test._topic_service.get_or_create_user_topic.assert_not_called()
        self.under_test._user_service.log_user_changes.assert_not_called()
        self.under_test._topic_service.forward_user_pm.assert_not_called()


class TestBanCommandHandler:

    @pytest.fixture(autouse=True)
    def setup_method(self, session_wrapper, bot):
        self.under_test: BanCommandHandler = DIAsync(
            session=session_wrapper,
            bot=bot,
        ).ban_command_handler

    @pytest.mark.asyncio
    async def test_call_happy_path(self, mocked_session, tg_update_factory, db_user_factory, db_topic_factory):
        pass
        # given
        tg_update: Update = tg_update_factory()
        db_user = db_user_factory(id=tg_update.message.from_user.id)
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        # when
        await self.under_test(tg_update, {})
        actual_db_user = mocked_session.query(User).filter_by(id=db_user.id).first()

        # then
        assert actual_db_user.is_banned


class TestUnbanCommandHandler:

    @pytest.fixture(autouse=True)
    def setup_method(self, session_wrapper, bot):
        self.under_test: UnbanCommandHandler = DIAsync(
            session=session_wrapper,
            bot=bot,
        ).unban_command_handler

    @pytest.mark.asyncio
    async def test_call_happy_path(self, mocked_session, tg_update_factory, db_user_factory, db_topic_factory):
        pass
        # given
        tg_update: Update = tg_update_factory()
        db_user = db_user_factory(id=tg_update.message.from_user.id, is_banned=True)
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        # when
        await self.under_test(tg_update, {})
        actual_db_user = mocked_session.query(User).filter_by(id=db_user.id).first()

        # then
        assert not actual_db_user.is_banned


class TestUserLogCommandHandler:

    @pytest.fixture(autouse=True)
    def setup_method(self, session_wrapper, bot):
        self.under_test: UserLogCommandHandler = DIAsync(
            session=session_wrapper,
            bot=bot,
        ).userlog_command_handler

    @pytest.mark.asyncio
    async def test_call_happy_path(self, bot, tg_update_factory, db_user_factory, db_topic_factory,
                                   db_user_log_factory):  # yapf: disable
        # given
        tg_update: Update = tg_update_factory()
        db_user = db_user_factory(id=tg_update.message.from_user.id)
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)
        db_logs = [
            db_user_log_factory(
                user=db_user, field='full_name', value='Вася Пупкин',
                timestamp=datetime.datetime(2025, 3, 12, 16, 14, 0)
            ),
            db_user_log_factory(
                user=db_user, field='username', value='abc',
                timestamp=datetime.datetime(2025, 3, 12, 16, 14, 1)
            ),
            db_user_log_factory(
                user=db_user, field='full_name', value='Иван Иванов',
                timestamp=datetime.datetime(2025, 3, 12, 16, 14, 2)
            ),
            db_user_log_factory(
                user=db_user, field='username', value='def',
                timestamp=datetime.datetime(2025, 3, 12, 16, 14, 3)
            ),
            db_user_log_factory(
                user=db_user, field='is_banned', value='да',
                timestamp=datetime.datetime(2025, 3, 12, 16, 14, 4)
            ),
        ]

        # when
        await self.under_test(tg_update, {})

        # then
        assert bot.sent_messages[0].text == (
            f'Пользователь {str(db_user.id)}:\n'
            '\n'
            '*Первичная информация*\n'
            'Полное имя: Вася Пупкин\n'
            f'Имя пользователя: [@abc](tg://user?id={str(db_user.id)})\n'
            '\n'
            '*Полная история изменений*\n'
            '- 2025-03-12 16:14:02: Поле "полное имя" изменено на `Иван Иванов`\n'
            '- 2025-03-12 16:14:03: Поле "имя пользователя" изменено на `def`\n'
            '- 2025-03-12 16:14:04: Поле "статус бана" изменено на `да`\n'
        )
