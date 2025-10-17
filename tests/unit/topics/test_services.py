from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from telegram.error import BadRequest, Forbidden

from feedbackbot import settings
from feedbackbot.core.di import DIAsync
from feedbackbot.topics.constants import UNSUPPORTED_CONTENT
from feedbackbot.topics.models import Topic
from feedbackbot.topics.services import TopicService
from feedbackbot.users.constants import USER_BLOCKED_BOT


class TestTopicService:
    CHAT_ID = -1

    @pytest.fixture(autouse=True)
    def setup_method(self, session_wrapper, bot, db_topic_factory):
        self.under_test: TopicService = DIAsync(
            session=session_wrapper,
            bot=bot,
            topic_repo=AsyncMock(**{
                'create_topic.return_value': db_topic_factory()
            }),
            message_repo=AsyncMock(),
            reply_repo=AsyncMock(),
        ).topic_service

    @pytest.mark.asyncio
    async def test_get_or_create_user_topic_create_fresh(self, tg_user_factory, db_user_factory):  # yapf: disable
        # given
        tg_user = tg_user_factory()
        db_user = db_user_factory(id=tg_user.id)

        self.under_test._topic_repo.filter_topics.return_value = []

        # when
        actual_created, actual_topic = await self.under_test.get_or_create_user_topic(tg_user, db_user)

        # then
        assert actual_created is True
        assert isinstance(actual_topic, Topic)

    @pytest.mark.asyncio
    async def test_get_or_create_user_topic_use_existing_tg_topic_present(self, bot, mocker: MockerFixture,
                                                                          tg_user_factory, db_user_factory,
                                                                          db_topic_factory):  # yapf: disable
        # given
        tg_user = tg_user_factory()
        db_user = db_user_factory(id=tg_user.id)
        db_topic = db_topic_factory()

        mocker.patch.object(bot, 'edit_forum_topic', side_effect=BadRequest('Topic_not_modified'))
        self.under_test._topic_repo.filter_topics.return_value = [db_topic]

        # when
        actual_created, actual_topic = await self.under_test.get_or_create_user_topic(tg_user, db_user)

        # then
        assert actual_created is False
        assert isinstance(actual_topic, Topic)
        # использован существующий топик
        assert actual_topic == db_topic

    @pytest.mark.asyncio
    async def test_get_or_create_user_topic_use_existing_tg_topic_missing(self, bot, mocker: MockerFixture,
                                                                          tg_user_factory, db_user_factory,
                                                                          db_topic_factory):  # yapf: disable
        # given
        tg_user = tg_user_factory()
        db_user = db_user_factory(id=tg_user.id)
        db_topic = db_topic_factory()

        mocker.patch.object(bot, 'edit_forum_topic', side_effect=BadRequest('Topic_id_invalid'))
        bot.create_forum_topic = AsyncMock(return_value=AsyncMock(message_thread_id=123))
        self.under_test._topic_repo.filter_topics.return_value = [db_topic]

        # when
        actual_created, actual_topic = await self.under_test.get_or_create_user_topic(tg_user, db_user)

        # then
        assert actual_created is True
        assert isinstance(actual_topic, Topic)

    @pytest.mark.asyncio
    async def test_forward_user_pm(self, mocker: MockerFixture, bot, tg_message_factory, db_topic_factory):
        # given
        tg_message = tg_message_factory(bot=bot)
        db_topic = db_topic_factory(id=tg_message.message_thread_id)

        mocker.patch('feedbackbot.settings.CHAT_ID', self.CHAT_ID)
        mocker.spy(bot, 'forward_message')

        # when
        await self.under_test.forward_user_pm(tg_message, db_topic)

        # then
        # проверяем, что сообщение было перенаправлено
        assert bot.forward_message.call_count == 1
        assert bot.forward_message.call_args_list[0][1]['chat_id'] == settings.CHAT_ID
        assert bot.forward_message.call_args_list[0][1]['message_thread_id'] == db_topic.id
        # проверяем, что сообщение было записано в базу данных
        self.under_test._message_repo.create_message.assert_called_once_with(
            tg_message.id, bot.forwarded_messages[0].id, db_topic
        )

    @pytest.mark.asyncio
    async def test_reply_user_pm_text(self, mocker: MockerFixture, bot, tg_message_factory, db_topic_factory):
        # given
        tg_message = tg_message_factory(bot=bot, text='Hello')
        db_topic = db_topic_factory(id=tg_message.message_thread_id)

        mocker.spy(bot, 'send_message')
        mocker.spy(bot, 'send_photo')
        self.under_test._topic_repo.get_topic.return_value = db_topic

        # when
        await self.under_test.reply_user_pm(tg_message)

        # then
        bot.send_photo.assert_not_called()
        bot.send_message.assert_called_once_with(chat_id=db_topic.user.id, text=tg_message.text)
        self.under_test._reply_repo.create_reply.assert_called_once_with(
            tg_message.id, bot_message_id=bot.sent_messages[0].id, topic=db_topic
        )

    @pytest.mark.asyncio
    async def test_reply_user_pm_photo(self, mocker: MockerFixture, bot, tg_photo_attachment, tg_message_factory,
                                       db_topic_factory):  # yapf:disable
        # given
        tg_message = tg_message_factory(bot=bot, photo=(tg_photo_attachment,))
        db_topic = db_topic_factory(id=tg_message.message_thread_id)

        mocker.spy(bot, 'send_message')
        mocker.spy(bot, 'send_photo')
        self.under_test._topic_repo.get_topic.return_value = db_topic

        # when
        await self.under_test.reply_user_pm(tg_message)

        # then
        bot.send_message.assert_not_called()
        bot.send_photo.assert_called_once()
        self.under_test._reply_repo.create_reply.assert_called_once_with(
            tg_message.id, bot_message_id=bot.sent_messages[0].id, topic=db_topic
        )

    @pytest.mark.asyncio
    async def test_reply_user_pm_unsupported_content(self, mocker: MockerFixture, bot, tg_message_factory):
        # given
        tg_message = tg_message_factory(bot=bot, text=None, photo=None)

        # when
        await self.under_test.reply_user_pm(tg_message)

        # then
        assert bot.sent_messages[0].text == UNSUPPORTED_CONTENT

    @pytest.mark.asyncio
    async def test_reply_user_pm_forbidden(self, mocker: MockerFixture, bot, tg_message_factory, db_topic_factory):
        # given
        tg_message = tg_message_factory(bot=bot, text='Hello')
        db_topic = db_topic_factory(id=tg_message.message_thread_id)

        mocker.patch.object(bot, 'send_message', side_effect=[Forbidden('Forbidden'), None])
        self.under_test._topic_repo.get_topic.return_value = db_topic

        # when
        await self.under_test.reply_user_pm(tg_message)

        # then
        assert bot.send_message.call_args_list[1][1]['text'] == USER_BLOCKED_BOT

    @pytest.mark.asyncio
    async def test_edit_operator_reply_text(self, mocker: MockerFixture, bot, tg_message_factory, db_topic_factory,
                                            db_reply_factory):  # yapf: disable
        # given
        tg_message = tg_message_factory(bot=bot, text='Updated text')
        db_topic = db_topic_factory(id=tg_message.message_thread_id)
        db_reply = db_reply_factory(id=tg_message.id, topic_id=db_topic.id)

        mocker.spy(bot, 'edit_message_text')
        mocker.spy(bot, 'edit_message_media')
        self.under_test._topic_repo.get_topic.return_value = db_topic
        self.under_test._reply_repo.get_reply.return_value = db_reply

        # when
        await self.under_test.edit_operator_reply(tg_message)

        # then
        bot.edit_message_text.assert_called_once_with(
            text='Updated text', chat_id=db_topic.user.id, message_id=db_reply.bot_message_id
        )
        bot.edit_message_media.assert_not_called()

    @pytest.mark.asyncio
    async def test_edit_operator_reply_photo(self, mocker: MockerFixture, bot, tg_photo_attachment, tg_message_factory,
                                             db_topic_factory, db_reply_factory):  # yapf: disable
        # given
        tg_message = tg_message_factory(bot=bot, photo=(tg_photo_attachment,), caption='Updated caption')
        db_topic = db_topic_factory(id=tg_message.message_thread_id)
        db_reply = db_reply_factory(id=tg_message.id, topic_id=db_topic.id)

        mocker.spy(bot, 'edit_message_text')
        mocker.spy(bot, 'edit_message_media')
        self.under_test._topic_repo.get_topic.return_value = db_topic
        self.under_test._reply_repo.get_reply.return_value = db_reply

        # when
        await self.under_test.edit_operator_reply(tg_message)

        # then
        bot.edit_message_text.assert_not_called()
        bot.edit_message_media.assert_called_once()
        # Проверяем, что media содержит правильные параметры
        call_args = bot.edit_message_media.call_args
        assert call_args[1]['chat_id'] == db_topic.user.id
        assert call_args[1]['message_id'] == db_reply.bot_message_id

    @pytest.mark.asyncio
    async def test_edit_operator_reply_topic_not_found(self, mocker: MockerFixture, bot, tg_message_factory):
        # given
        tg_message = tg_message_factory(bot=bot, text='Updated text')

        mocker.spy(bot, 'edit_message_text')
        self.under_test._topic_repo.get_topic.return_value = None

        # when
        await self.under_test.edit_operator_reply(tg_message)

        # then
        bot.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_edit_operator_reply_reply_not_found(self, mocker: MockerFixture, bot, tg_message_factory, db_topic_factory):
        # given
        tg_message = tg_message_factory(bot=bot, text='Updated text')
        db_topic = db_topic_factory(id=tg_message.message_thread_id)

        mocker.spy(bot, 'edit_message_text')
        self.under_test._topic_repo.get_topic.return_value = db_topic
        self.under_test._reply_repo.get_reply.return_value = None

        # when
        await self.under_test.edit_operator_reply(tg_message)

        # then
        bot.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_edit_operator_reply_unsupported_content(self, mocker: MockerFixture, bot, tg_message_factory,
                                                           db_topic_factory, db_reply_factory):  # yapf: disable
        # given
        tg_message = tg_message_factory(bot=bot, text=None, photo=None)
        db_topic = db_topic_factory(id=tg_message.message_thread_id)
        db_reply = db_reply_factory(id=tg_message.id, topic_id=db_topic.id)

        mocker.spy(bot, 'edit_message_text')
        mocker.spy(bot, 'edit_message_media')
        self.under_test._topic_repo.get_topic.return_value = db_topic
        self.under_test._reply_repo.get_reply.return_value = db_reply

        # when
        await self.under_test.edit_operator_reply(tg_message)

        # then
        bot.edit_message_text.assert_not_called()
        bot.edit_message_media.assert_not_called()
        assert bot.sent_messages[0].text == UNSUPPORTED_CONTENT

    @pytest.mark.asyncio
    async def test_edit_operator_reply_forbidden(self, mocker: MockerFixture, bot, tg_message_factory, db_topic_factory,
                                                 db_reply_factory):  # yapf: disable
        # given
        tg_message = tg_message_factory(bot=bot, text='Updated text')
        db_topic = db_topic_factory(id=tg_message.message_thread_id)
        db_reply = db_reply_factory(id=tg_message.id, topic_id=db_topic.id)

        mocker.patch.object(bot, 'edit_message_text', side_effect=[Forbidden('Forbidden'), None])
        self.under_test._topic_repo.get_topic.return_value = db_topic
        self.under_test._reply_repo.get_reply.return_value = db_reply

        # when
        await self.under_test.edit_operator_reply(tg_message)

        # then
        assert bot.sent_messages[0].text == USER_BLOCKED_BOT

    @pytest.mark.asyncio
    async def test_delete_message_user_exists(self, mocker: MockerFixture, bot, db_message_factory, db_topic_factory):
        # given
        db_message = db_message_factory()
        db_topic = db_topic_factory(id=db_message.topic_id)

        mocker.spy(bot, 'delete_message')
        self.under_test._message_repo.get_message.return_value = db_message
        self.under_test._topic_repo.get_topic.return_value = db_topic

        # when
        await self.under_test.delete_message_user(db_message.id)

        # then
        bot.delete_message.assert_any_call(db_topic.user.id, db_message.id)
        self.under_test._message_repo.delete_message.assert_called_once_with(db_message.id)
        bot.delete_message.assert_any_call(settings.CHAT_ID, db_message.bot_message_id)

    @pytest.mark.asyncio
    async def test_delete_message_user_not_exists(self, mocker: MockerFixture, bot):
        # given
        mocker.spy(bot, 'delete_message')
        self.under_test._message_repo.get_message.return_value = None

        # when
        await self.under_test.delete_message_user(123)

        # then
        bot.delete_message.assert_not_called()
        self.under_test._message_repo.delete_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_message_operator_exists(self, mocker: MockerFixture, bot, db_message_factory,
                                                  db_topic_factory):  # yapf: disable
        # given
        db_message = db_message_factory()
        db_topic = db_topic_factory(id=db_message.topic_id)

        mocker.spy(bot, 'delete_message')
        self.under_test._message_repo.filter_messages.return_value = [db_message]
        self.under_test._topic_repo.get_topic.return_value = db_topic

        # when
        await self.under_test.delete_message_operator(db_message.bot_message_id)

        # then
        bot.delete_message.assert_called_once_with(db_topic.user.id, db_message.id)
        self.under_test._message_repo.delete_message.assert_called_once_with(db_message.id)

    @pytest.mark.asyncio
    async def test_delete_message_operator_not_exists(self, mocker: MockerFixture, bot):
        # given
        mocker.spy(bot, 'delete_message')
        self.under_test._message_repo.filter_messages.return_value = []

        # when
        await self.under_test.delete_message_operator(123)

        # then
        bot.delete_message.assert_not_called()
        self.under_test._message_repo.delete_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_reply_exists(self, mocker: MockerFixture, bot, db_reply_factory, db_topic_factory):
        # given
        db_reply = db_reply_factory()
        db_topic = db_topic_factory(id=db_reply.topic_id)

        mocker.spy(bot, 'delete_message')
        self.under_test._reply_repo.get_reply.return_value = db_reply
        self.under_test._topic_repo.get_topic.return_value = db_topic

        # when
        await self.under_test.delete_reply(db_reply.id)

        # then
        bot.delete_message.assert_called_once_with(db_topic.user.id, db_reply.bot_message_id)
        self.under_test._reply_repo.delete_reply.assert_called_once_with(db_reply.id)

    @pytest.mark.asyncio
    async def test_delete_reply_not_exists(self, mocker: MockerFixture, bot):
        # given
        mocker.spy(bot, 'delete_message')
        self.under_test._reply_repo.get_reply.return_value = None

        # when
        await self.under_test.delete_reply(123)

        # then
        bot.delete_message.assert_not_called()
        self.under_test._reply_repo.delete_reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_history(self, mocker: MockerFixture, bot, db_topic_factory, db_message_factory,
                                  db_reply_factory):  # yapf: disable
        # given
        db_topic = db_topic_factory()
        db_messages = [db_message_factory(topic_id=db_topic.id) for _ in range(3)]
        db_replies = [db_reply_factory(topic_id=db_topic.id) for _ in range(2)]

        mocker.spy(bot, 'delete_message')
        self.under_test._topic_repo.get_topic.return_value = db_topic
        self.under_test._message_repo.filter_messages.return_value = db_messages
        self.under_test._reply_repo.filter_replies.return_value = db_replies

        # when
        await self.under_test.delete_history(db_topic.id)

        # then
        assert bot.delete_message.call_count == len(db_messages) + len(db_replies)
        assert self.under_test._message_repo.delete_message.call_count == len(db_messages)
        assert self.under_test._reply_repo.delete_reply.call_count == len(db_replies)
