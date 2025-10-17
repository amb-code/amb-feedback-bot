from feedbackbot.core.db import BaseAsyncDBRepo
from feedbackbot.users.models import User, UserLog


class UserRepo(BaseAsyncDBRepo[User]):
    model_class = User

    async def create_user(self, user_id: int):
        return await self.create(
            id=user_id,
        )

    async def get_user(self, user_id: int):
        return await self.get(id=user_id)

    async def update_user(self, user_id: int, **kwargs):
        return await self.update(self.model_class.id==user_id, **kwargs)


class UserLogRepo(BaseAsyncDBRepo[UserLog]):
    model_class = UserLog

    async def create_user_log(self, user_id: int, field: str, value: str):
        return await self.create(
            user_id=user_id,
            field=field,
            value=value,
        )

    async def filter_user_logs(self, user_id: int, field: str | None = None, **kwargs):
        return await self.filter(user_id=user_id, field=field, **kwargs)
