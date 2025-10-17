__all__ = ('Topic', 'Message', 'Reply', '')
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from feedbackbot.core.db import Base


class Topic(Base):
    __tablename__ = 'topics'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'))
    user: Mapped['User'] = relationship('User', backref='topics', lazy='joined')

    version: Mapped[int] = mapped_column(default=0)
    is_open: Mapped[bool] = mapped_column(default=True)


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    topic_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('topics.id'))
    topic: Mapped['Topic'] = relationship('Topic', backref='messages', lazy='joined')

    version: Mapped[int] = mapped_column(default=0)
    bot_message_id: Mapped[int] = mapped_column(BigInteger)


class Reply(Base):
    __tablename__ = 'replies'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    topic_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('topics.id'))
    topic: Mapped['Topic'] = relationship('Topic', backref='replies', lazy='joined')

    version: Mapped[int] = mapped_column(default=0)
    bot_message_id: Mapped[int] = mapped_column(BigInteger)
