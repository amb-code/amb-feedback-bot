__all__ = ('User', 'UserLog')
import datetime

from sqlalchemy import BigInteger, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from feedbackbot.core.db import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(default=0)
    is_banned: Mapped[bool] = mapped_column(default=False)


class UserLog(Base):
    __tablename__ = 'user_logs'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'))
    user: Mapped['User'] = relationship('User', backref='logs', lazy='joined')

    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    field: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()

