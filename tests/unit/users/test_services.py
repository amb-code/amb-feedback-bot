from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from telegram import Update
from telegram.error import BadRequest

from feedbackbot import settings
from feedbackbot.users.enums import UserLogField, UserLogValue
from feedbackbot.users.services import UserService


class TestUserService:

    @pytest.fixture(autouse=True)
    def setup_method(self, session_wrapper, bot, db_user_factory):
        self.under_test: UserService = UserService(
            bot=bot,
            topic_repo=AsyncMock(),
            user_repo=AsyncMock(**{
                'get.return_value': db_user_factory(),
                'create_user.return_value': db_user_factory()
            }),
            user_log_repo=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, tg_user_factory, db_user_factory):
        # given
        tg_user = tg_user_factory()
        db_user = db_user_factory(id=tg_user.id)
        self.under_test._user_repo.get.return_value = db_user

        # when
        actual_user = await self.under_test.get_or_create_user(tg_user)

        # then
        assert actual_user == db_user
        self.under_test._user_repo.create_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self, tg_user_factory):
        # given
        tg_user = tg_user_factory()
        self.under_test._user_repo.get.return_value = None

        # when
        actual_user = await self.under_test.get_or_create_user(tg_user)

        # then
        self.under_test._user_repo.create_user.assert_called_once_with(tg_user.id)
        assert actual_user == self.under_test._user_repo.create_user.return_value

    @pytest.mark.asyncio
    async def test_set_user_ban_by_topic(self, db_topic_factory):
        # given
        db_topic = db_topic_factory()
        self.under_test._topic_repo.get_topic.return_value = db_topic

        # when
        await self.under_test.set_user_ban_by_topic(db_topic.id, True)

        # then
        self.under_test._user_repo.update_user.assert_called_once_with(db_topic.user_id, is_banned=True)
        self.under_test._user_log_repo.create_user_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_user_changes(self, tg_user_factory, db_topic_factory):
        # given
        tg_user = tg_user_factory()
        db_topic = db_topic_factory()
        self.under_test._user_log_repo.filter_user_logs.return_value = []

        # when
        await self.under_test.log_user_changes(tg_user, db_topic.id)

        # then
        self.under_test._user_log_repo.create_user_log.assert_any_call(
            tg_user.id, field=UserLogField.FULL_NAME.value, value=tg_user.full_name
        )
        self.under_test._user_log_repo.create_user_log.assert_any_call(
            tg_user.id, field=UserLogField.USERNAME.value, value=tg_user.username or UserLogValue.EMPTY.value
        )

    @pytest.mark.asyncio
    async def test_log_user_changes_notifies_with_html(self, mocker: MockerFixture, tg_user_factory,
                                                       db_topic_factory, db_user_log_factory):  # yapf: disable
        # given
        tg_user = tg_user_factory(first_name='New', last_name='Name')
        db_topic = db_topic_factory()
        prev_full_name = db_user_log_factory(field='full_name', value='Old <Name>')
        self.under_test._user_log_repo.filter_user_logs.side_effect = [
            [prev_full_name],
            [],
        ]
        mocker.spy(self.under_test._bot, 'send_message')

        # when
        await self.under_test.log_user_changes(tg_user, db_topic.id)

        # then
        send_kwargs = self.under_test._bot.send_message.call_args.kwargs
        assert send_kwargs['parse_mode'] == 'HTML'
        assert '<code>Old &lt;Name&gt;</code>' in send_kwargs['text']
        assert f'<code>{tg_user.full_name}</code>' in send_kwargs['text']

    @pytest.mark.asyncio
    async def test_log_user_changes_saves_when_notify_fails(self, mocker: MockerFixture, tg_user_factory,
                                                            db_topic_factory, db_user_log_factory):  # yapf: disable
        # given
        tg_user = tg_user_factory()
        db_topic = db_topic_factory()
        prev_full_name = db_user_log_factory(field='full_name', value='Old Name')
        self.under_test._user_log_repo.filter_user_logs.side_effect = [
            [prev_full_name],
            [],
        ]
        mocker.patch.object(
            self.under_test._bot, 'send_message', side_effect=BadRequest("Can't parse entities")
        )

        # when
        await self.under_test.log_user_changes(tg_user, db_topic.id)

        # then
        self.under_test._user_log_repo.create_user_log.assert_any_call(
            tg_user.id, field=UserLogField.FULL_NAME.value, value=tg_user.full_name
        )

    @pytest.mark.asyncio
    async def test_send_userlog_message(self, mocker: MockerFixture, tg_update_factory, db_user_factory,
                                        db_user_log_factory, db_topic_factory, ):
        # given
        tg_update: Update = tg_update_factory()
        db_user = db_user_factory(id=tg_update.message.from_user.id)
        db_topic = db_topic_factory(
            id=tg_update.message.message_thread_id, user=db_user, user_id=db_user.id
        )
        db_logs = [
            db_user_log_factory(
                user=db_user, field='full_name', value='Вася Пупкин',
            ),
            db_user_log_factory(
                user=db_user, field='username', value='abc',
            ),
        ]

        mocker.spy(self.under_test._bot, 'send_message')
        self.under_test._topic_repo.get_topic.return_value = db_topic
        self.under_test._user_log_repo.filter_user_logs.return_value = db_logs

        # when
        await self.under_test.send_userlog_message(db_topic.id)

        # then
        self.under_test._bot.send_message.assert_called_once_with(
            settings.CHAT_ID,
            message_thread_id=db_topic.id,
            text=(
                f'Пользователь {db_user.id}:\n'
                '\n'
                '<b>Первичная информация</b>\n'
                'Полное имя: Вася Пупкин\n'
                f'Имя пользователя: <a href="tg://user?id={db_user.id}">@abc</a>\n'
                '\n'
            ),
            parse_mode='HTML',
        )

    @pytest.mark.asyncio
    async def test_send_userlog_message_escapes_html(self, mocker: MockerFixture, db_user_factory,
                                                     db_user_log_factory, db_topic_factory):  # yapf: disable
        # given
        db_user = db_user_factory()
        db_topic = db_topic_factory(user=db_user)
        db_logs = [
            db_user_log_factory(user=db_user, field='full_name', value='看*主页 <admin>'),
            db_user_log_factory(user=db_user, field='username', value='a_b&c'),
        ]
        mocker.spy(self.under_test._bot, 'send_message')
        self.under_test._topic_repo.get_topic.return_value = db_topic
        self.under_test._user_log_repo.filter_user_logs.return_value = db_logs

        # when
        await self.under_test.send_userlog_message(db_topic.id)

        # then
        send_kwargs = self.under_test._bot.send_message.call_args.kwargs
        assert send_kwargs['parse_mode'] == 'HTML'
        assert '看*主页 &lt;admin&gt;' in send_kwargs['text']
        assert '@a_b&amp;c' in send_kwargs['text']