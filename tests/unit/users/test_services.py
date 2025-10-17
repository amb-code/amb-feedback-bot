from unittest.mock import AsyncMock, call

import pytest
from pytest_mock import MockerFixture
from telegram import User as TGUser, Update

from feedbackbot.users.services import UserService
from feedbackbot.users.models import User as DBUser
from feedbackbot.users.enums import UserLogField, UserLogValue


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
    async def test_send_userlog_message(self, mocker: MockerFixture, tg_update_factory, db_user_factory,
                                        db_user_log_factory, db_topic_factory, ):
        # given
        tg_update: Update = tg_update_factory()
        db_user = db_user_factory(id=tg_update.message.from_user.id)
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)
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
        self.under_test._bot.send_message.assert_called_once()