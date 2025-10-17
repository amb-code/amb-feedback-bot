from collections.abc import Sequence
from typing import Callable, Type, TypeVar, Generic

from sqlalchemy import update, select, delete, BIGINT, NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import Session, DeclarativeBase

from feedbackbot import settings


class Base(DeclarativeBase):
    type_annotation_map = {
        int: BIGINT,
    }


T = TypeVar('T', bound=Base)


class BaseAsyncDBRepo(Generic[T]):
    model_class: Type[T]

    def __init__(self, session: Callable[..., AsyncSession]):
        self._session = session

    # Низкоуровневые методы

    async def create(self, **model_kwargs) -> T:
        instance = self.model_class(**model_kwargs)

        async with self._session() as session:
            async with session.begin():
                session.add(instance)

                return instance

    async def get(self, **get_kwargs) -> T:
        async with self._session() as session:
            user = await session.get(self.model_class, get_kwargs)

            return user

    async def get_many(self, *filter_criteria, ordering: tuple[str, str] | None =None) -> Sequence[T]:
        """

        :param filter_criteria:
        :param ordering: ('timestamp', 'desc')
        :return:
        """
        async with self._session() as session:
            q = select(self.model_class).where(*filter_criteria)
            if ordering:
                q = q.order_by(getattr(getattr(self.model_class, ordering[0]), ordering[1])())
            res = await session.execute(q)
            return res.scalars().all()

    async def update(self, lookup_expr, **update_kwargs) -> T:
        async with self._session() as session:
            async with session.begin():
                await session.execute(
                    update(self.model_class)
                    .where(lookup_expr)
                    .values(**update_kwargs)
                )
                await session.commit()

            res = await session.execute(select(self.model_class).where(lookup_expr))
            instance = res.scalar_one()

            return instance

    async def delete(self, lookup_expr):
        async with self._session() as session:
            async with session.begin():
                await session.execute(
                    delete(self.model_class)
                    .where(lookup_expr)
                )
                await session.commit()

    # Удобные методы

    async def filter(self, ordering: tuple[str, str] | None =None, **kwargs):
        criteria = []

        for name, value in kwargs.items():
            if value is not None:
                criteria.append(getattr(self.model_class, name) == value)

        return await self.get_many(*criteria, ordering=ordering)


class DBRefs:

    def __init__(self, engine: AsyncEngine, session: Callable[..., AsyncSession]):
        self.engine = engine
        self.session = session


def get_engine():
    from feedbackbot.users.models import User, UserLog
    from feedbackbot.topics.models import Topic, Message, Reply
    return create_async_engine(settings.DB_URI, echo=False, poolclass=NullPool)
