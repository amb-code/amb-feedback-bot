import pytest

from feedbackbot.core.db import BaseAsyncDBRepo
from feedbackbot.core.di import DIAsync
from feedbackbot.users.models import User


class TestBaseAsyncDBRepo:
    new_obj_id = 999999

    @pytest.fixture(autouse=True)
    def setup_method(self, session_wrapper):

        class TestRepo(BaseAsyncDBRepo[User]):
            model_class = User

        self.under_test: TestRepo = DIAsync(
            session=session_wrapper,
            test_repo=TestRepo,
        ).test_repo

    @pytest.mark.asyncio
    async def test_create(self, mocked_session):
        # given/when
        actual = await self.under_test.create(id=self.new_obj_id)
        db_user = mocked_session.query(User).filter_by(id=self.new_obj_id).first()

        # then
        assert isinstance(actual, User)
        assert actual.id == self.new_obj_id
        assert actual == db_user

    @pytest.mark.asyncio
    async def test_get(self, mocked_session):
        actual = await self.under_test.get(id=1)

        assert isinstance(actual, User)
        assert actual.id == 1


    @pytest.mark.asyncio
    async def test_get_may(self):
        actual = await self.under_test.get_many(User.is_banned == False, ordering=('id', 'desc'))

        assert isinstance(actual, list)
        assert len(actual) == 2

        # ordering works
        assert actual[0].id == 2
        assert actual[1].id == 1

    @pytest.mark.asyncio
    async def test_update(self):
        actual = await self.under_test.update(User.id == 1, is_banned=True)

        assert actual.id == 1
        assert actual.is_banned == True

    @pytest.mark.asyncio
    async def test_delete(self, mocked_session):
        # given
        await self.under_test.create(id=self.new_obj_id)  # Create a user to delete

        # when
        await self.under_test.delete(User.id == self.new_obj_id)

        # then
        db_user = mocked_session.query(User).filter_by(id=self.new_obj_id).first()
        assert db_user is None  # User should be deleted

    @pytest.mark.asyncio
    async def test_filter(self, mocked_session):
        # given/when
        actual = await self.under_test.filter(is_banned=False)

        # then
        assert isinstance(actual, list)
        assert len(actual) == 2
        assert actual[0].id == 1
        assert actual[1].id == 2
