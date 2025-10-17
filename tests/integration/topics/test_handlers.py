import random
from unittest.mock import call

import pytest
from faker import Generator
from pytest_mock import MockerFixture
from telegram import Update

from feedbackbot import settings
from feedbackbot.core.di import DIAsync
from feedbackbot.topics.constants import UNSUPPORTED_CONTENT
from feedbackbot.topics.handlers import ReplyMessageHandler, DeleteCommandHandler, DeleteHistoryCommandHandler
from feedbackbot.topics.models import Reply, Message


class TestReplyMessageHandler:
    BOT_ID = 1

    @pytest.fixture(autouse=True)
    def setup_method(self, bot, session_wrapper):
        self.under_test: ReplyMessageHandler = DIAsync(
            session=session_wrapper,
            bot=bot,
        ).reply_message_handler

    @pytest.mark.asyncio
    async def test_call_reply_happy_path_text(self, mocker: MockerFixture, bot, mocked_session, tg_update_factory,
                                              tg_user_factory, tg_message_factory, tg_message_origin_factory,
                                              db_user_factory, db_topic_factory):  # yapf: disable
        # given
        tg_update = tg_update_factory(
            message=tg_message_factory(
                text='any',
                reply_to_message=tg_message_factory(
                    from_user=tg_user_factory(id=self.BOT_ID),
                    forward_origin=tg_message_origin_factory()
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        reply_user_pm_spy = mocker.spy(self.under_test._service, 'reply_user_pm')
        bot_send_message_spy = mocker.spy(bot, 'send_message')

        # when
        await self.under_test(tg_update, {})

        # then
        reply_user_pm_spy.assert_called_once()
        # ответ отправлен
        bot_send_message_spy.assert_called_once_with(chat_id=db_topic.user.id, text=tg_update.message.text)
        # запись создана
        actual_reply = mocked_session.query(Reply).filter_by(topic_id=db_topic.id).first()
        assert actual_reply is not None

    @pytest.mark.asyncio
    async def test_call_reply_happy_path_photo(self, mocker: MockerFixture, bot, mocked_session, tg_update_factory,
                                               tg_user_factory, tg_message_factory, tg_message_origin_factory,
                                               tg_photo_attachment, db_user_factory, db_topic_factory):  # yapf: disable
        # given
        tg_update: Update = tg_update_factory(
            message=tg_message_factory(
                photo=(tg_photo_attachment,),
                reply_to_message=tg_message_factory(
                    from_user=tg_user_factory(id=self.BOT_ID),
                    forward_origin=tg_message_origin_factory()
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        reply_user_pm_spy = mocker.spy(self.under_test._service, 'reply_user_pm')
        bot_send_photo_spy = mocker.spy(bot, 'send_photo')

        # when
        await self.under_test(tg_update, {})

        # then
        reply_user_pm_spy.assert_called_once()

        # ответ отправлен
        bot_send_photo_spy.assert_called_once()
        bot.attachment_file.download_to_drive.assert_called_once()
        assert str(bot.attachment_file.download_to_drive.call_args[0][0]).startswith(str(settings.TMP_PATH))

        # запись создана
        actual_reply = mocked_session.query(Reply).filter_by(topic_id=db_topic.id).first()
        assert actual_reply is not None

    @pytest.mark.asyncio
    async def test_call_reply_unknown_content_type(self, mocker: MockerFixture, bot, tg_update_factory,
                                                   tg_user_factory, tg_message_factory, tg_message_origin_factory,
                                                   tg_photo_attachment, db_user_factory, db_topic_factory):  # yapf: disable
        # given
        tg_update: Update = tg_update_factory(
            message=tg_message_factory(
                bot=bot,
                reply_to_message=tg_message_factory(
                    bot=bot,
                    from_user=tg_user_factory(id=self.BOT_ID),
                    forward_origin=tg_message_origin_factory()
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        reply_user_pm_spy = mocker.spy(self.under_test._service, 'reply_user_pm')
        create_reply_spy = mocker.spy(self.under_test._service._reply_repo, 'create_reply')

        # when
        await self.under_test(tg_update, {})

        # then
        reply_user_pm_spy.assert_called_once()

        assert bot.sent_messages[0].text == UNSUPPORTED_CONTENT

        create_reply_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_reply_not_forwarded_by_bot(self, mocker: MockerFixture, tg_update_factory, tg_user_factory,
                                                   tg_message_factory, db_user_factory, db_topic_factory):
        # given
        tg_update = tg_update_factory(
            message=tg_message_factory(
                text='any',
                reply_to_message=tg_message_factory(
                    from_user=tg_user_factory(id=self.BOT_ID)
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        reply_user_pm_spy = mocker.spy(self.under_test._service, 'reply_user_pm')

        # when
        await self.under_test(tg_update, {})

        # then
        reply_user_pm_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_reply_not_reply_to_bot_forwarded(self, mocker: MockerFixture, faker: Generator,
                                                         tg_update_factory, tg_user_factory, tg_message_factory,
                                                         tg_message_origin_factory, db_user_factory,
                                                         db_topic_factory):  # yapf: disable
        # given
        tg_update = tg_update_factory(
            message=tg_message_factory(
                text='any',
                reply_to_message=tg_message_factory(
                    from_user=tg_user_factory(id=faker.pyint(min_value=self.BOT_ID + 1)),
                    forward_origin=tg_message_origin_factory()
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.message.message_thread_id, user=db_user)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        reply_user_pm_spy = mocker.spy(self.under_test._service, 'reply_user_pm')

        # when
        await self.under_test(tg_update, {})

        # then
        reply_user_pm_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_edit_happy_path_text(self, mocker: MockerFixture, bot, tg_update_factory, tg_user_factory,
                                             tg_message_factory, db_user_factory, db_topic_factory,
                                             db_reply_factory):  # yapf: disable
        # given
        tg_update = tg_update_factory(
            message=None,
            edited_message=tg_message_factory(
                text='edited text',
                reply_to_message=tg_message_factory(
                    from_user=tg_user_factory(id=self.BOT_ID)
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.edited_message.message_thread_id, user=db_user)
        db_reply = db_reply_factory(id=tg_update.edited_message.id, topic=db_topic)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        edit_operator_reply_spy = mocker.spy(self.under_test._service, 'edit_operator_reply')
        bot_edit_message_text_spy = mocker.spy(bot, 'edit_message_text')

        # when
        await self.under_test(tg_update, {})

        # then
        edit_operator_reply_spy.assert_called_once()
        bot_edit_message_text_spy.assert_called_once_with(
            text=tg_update.edited_message.text, chat_id=db_topic.user.id, message_id=db_reply.bot_message_id
        )
        assert bot.edited_messages[-1].text == 'edited text'

    @pytest.mark.asyncio
    async def test_call_edit_happy_path_photo(self, mocker: MockerFixture, bot, tg_update_factory, tg_user_factory,
                                              tg_message_factory, tg_photo_attachment, db_user_factory,
                                              db_topic_factory, db_reply_factory):  # yapf: disable
        # given
        tg_update = tg_update_factory(
            message=None,
            edited_message=tg_message_factory(
                photo=(tg_photo_attachment,),
                caption='edited caption',
                reply_to_message=tg_message_factory(
                    from_user=tg_user_factory(id=self.BOT_ID)
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.edited_message.message_thread_id, user=db_user)
        db_reply = db_reply_factory(id=tg_update.edited_message.id, topic=db_topic)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        edit_operator_reply_spy = mocker.spy(self.under_test._service, 'edit_operator_reply')
        bot_edit_message_media_spy = mocker.spy(bot, 'edit_message_media')

        # when
        await self.under_test(tg_update, {})

        # then
        edit_operator_reply_spy.assert_called_once()
        bot_edit_message_media_spy.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_edit_unknown_content_type(self, mocker: MockerFixture, bot, tg_update_factory, tg_user_factory,
                                                  tg_message_factory, db_user_factory, db_topic_factory,
                                                  db_reply_factory):  # yapf: disable
        # given
        tg_update = tg_update_factory(
            message=None,
            edited_message=tg_message_factory(
                bot=bot,
                reply_to_message=tg_message_factory(
                    bot=bot,
                    from_user=tg_user_factory(id=self.BOT_ID)
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.edited_message.message_thread_id, user=db_user)
        db_reply = db_reply_factory(id=tg_update.edited_message.id, topic=db_topic)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        edit_operator_reply_spy = mocker.spy(self.under_test._service, 'edit_operator_reply')

        # when
        await self.under_test(tg_update, {})

        # then
        edit_operator_reply_spy.assert_called_once()
        assert bot.sent_messages[0].text == UNSUPPORTED_CONTENT

    @pytest.mark.asyncio
    async def test_call_edit_not_reply_to_bot_forwarded(self, mocker: MockerFixture, faker: Generator,
                                                        tg_update_factory, tg_user_factory, tg_message_factory,
                                                        db_user_factory, db_topic_factory):  # yapf: disable
        # given
        tg_update = tg_update_factory(
            message=None,
            edited_message=tg_message_factory(
                text='edited text',
                reply_to_message=tg_message_factory(
                    from_user=tg_user_factory(id=faker.pyint(min_value=self.BOT_ID + 1))
                )
            )
        )

        db_user = db_user_factory()
        db_topic = db_topic_factory(id=tg_update.edited_message.message_thread_id, user=db_user)

        mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        edit_operator_reply_spy = mocker.spy(self.under_test._service, 'edit_operator_reply')

        # when
        await self.under_test(tg_update, {})

        # then
        edit_operator_reply_spy.assert_not_called()


class TestDeleteCommandHandler:

    @pytest.fixture(autouse=True)
    def setup_method(self, bot, session_wrapper):
        self.under_test: DeleteCommandHandler = DIAsync(
            session=session_wrapper,
            bot=bot,
        ).delete_command_handler

    @pytest.mark.asyncio
    async def test_call_happy_path_user_forwarded_message(self, mocker: MockerFixture, bot, mocked_session,
                                                          tg_update_factory, tg_message_factory,
                                                          tg_message_origin_factory, db_topic_factory,
                                                          db_message_factory):  # yapf: disable
        # given
        tg_user_forwarded_message = tg_message_factory(
            forward_origin=tg_message_origin_factory()
        )
        tg_update = tg_update_factory(
            message=tg_message_factory(
                reply_to_message=tg_user_forwarded_message
            )
        )

        db_topic = db_topic_factory(id=tg_update.message.message_thread_id)
        db_message = db_message_factory(bot_message_id=tg_user_forwarded_message.message_id, topic=db_topic)

        delete_message_operator_spy = mocker.spy(self.under_test._topic_service, 'delete_message_operator')
        delete_reply_spy = mocker.spy(self.under_test._topic_service, 'delete_reply')
        bot_delete_message_spy = mocker.spy(bot, 'delete_message')

        # when
        await self.under_test(tg_update, {})

        # then
        # вызван нужный метод сервиса
        delete_message_operator_spy.assert_called_once_with(tg_update.message.reply_to_message.message_id)
        delete_reply_spy.assert_not_called()
        # бот выполнил удаление в чате с пользователем
        bot_delete_message_spy.assert_called_once_with(db_topic.user.id, db_message.id)
        # сообщение в базе удалено
        actual_db_message = mocked_session.query(Message).get(db_message.id)
        assert actual_db_message is None

    @pytest.mark.asyncio
    async def test_call_happy_path_operator_reply(self, mocker: MockerFixture, bot, mocked_session, tg_update_factory,
                                                  tg_user_factory, tg_message_factory,db_topic_factory,
                                                  db_reply_factory):  # yapf: disable
        # given
        tg_operator_user = tg_user_factory()
        tg_bot_operator_reply_message = tg_message_factory(
            from_user=tg_operator_user
        )
        tg_update = tg_update_factory(
            message=tg_message_factory(
                from_user=tg_operator_user,
                reply_to_message=tg_bot_operator_reply_message,
            )
        )

        db_topic = db_topic_factory()
        db_reply = db_reply_factory(id=tg_bot_operator_reply_message.message_id, topic=db_topic)

        # mocker.patch('feedbackbot.settings.BOT_ID', self.BOT_ID)
        delete_message_operator_spy = mocker.spy(self.under_test._topic_service, 'delete_message_operator')
        delete_reply_spy = mocker.spy(self.under_test._topic_service, 'delete_reply')
        bot_delete_message_spy = mocker.spy(bot, 'delete_message')

        # when
        await self.under_test(tg_update, {})

        # then
        # вызван нужный метод сервиса
        delete_message_operator_spy.assert_not_called()
        delete_reply_spy.assert_called_once_with(tg_update.message.reply_to_message.message_id)
        # бот выполнил удаление в чате с пользователем
        bot_delete_message_spy.assert_called_once_with(db_topic.user.id, db_reply.bot_message_id)
        # сообщение в базе удалено
        actual_db_reply = mocked_session.query(Reply).get(db_reply.id)
        assert actual_db_reply is None

    # todo: not a reply
    # todo: not a tracked message


class TestDeleteHistoryCommandHandler:

    @pytest.fixture(autouse=True)
    def setup_method(self, bot, session_wrapper):
        self.under_test: DeleteHistoryCommandHandler = DIAsync(
            session=session_wrapper,
            bot=bot,
        ).delete_history_command_handler

    @pytest.mark.asyncio
    async def test_call_happy_path_user_forwarded_message(self, mocker: MockerFixture, bot, mocked_session,
                                                          tg_update_factory, tg_message_factory,
                                                          tg_message_origin_factory, db_user_factory, db_topic_factory,
                                                          db_message_factory, db_reply_factory):  # yapf: disable
        # given
        tg_user_forwarded_message = tg_message_factory(
            forward_origin=tg_message_origin_factory()
        )
        tg_update = tg_update_factory(
            message=tg_message_factory(
                reply_to_message=tg_user_forwarded_message
            )
        )

        db_topic = db_topic_factory(id=tg_update.message.message_thread_id)
        db_messages = [db_message_factory(topic=db_topic) for _ in range(random.randint(1, 5))]
        db_replies = [db_reply_factory(topic=db_topic) for _ in range(random.randint(1, 5))]

        delete_history_spy = mocker.spy(self.under_test._topic_service, 'delete_history')
        # delete_reply_spy = mocker.spy(self.under_test._topic_service, 'delete_reply')
        bot_delete_message_spy = mocker.spy(bot, 'delete_message')

        # when
        await self.under_test(tg_update, {})

        # then
        # вызван нужный метод сервиса
        delete_history_spy.assert_called_once_with(tg_update.message.message_thread_id)

        for db_message in db_messages:
            # бот выполнил удаление в чате с пользователем
            bot_delete_message_spy.assert_has_calls([call(db_topic.user.id, db_message.id)])
            # сообщения в базе удалены
            actual_db_message = mocked_session.query(Message).get(db_message.id)
            assert actual_db_message is None

        for db_reply in db_replies:
            # бот выполнил удаление в чате с пользователем
            bot_delete_message_spy.assert_has_calls([call(db_topic.user.id, db_reply.bot_message_id)])
            # сообщения в базе удалены
            actual_db_reply = mocked_session.query(Reply).get(db_reply.id)
            assert actual_db_reply is None
