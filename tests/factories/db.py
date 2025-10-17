__all__ = ('DbUserFactory', 'DbUserLogFactory', 'DbTopicFactory', 'DbMessageFactory', 'DbReplyFactory')

import factory
import factory.alchemy
import factory.fuzzy

from feedbackbot.users.enums import UserLogField
from feedbackbot.users.models import User, UserLog
from feedbackbot.topics.models import Topic, Message, Reply


# Users

class DbUserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User

    id =  factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    version = factory.Faker('pyint', max_value=100)
    is_banned = False


class DbUserLogFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = UserLog

    id =  factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    user = factory.SubFactory(DbUserFactory)

    timestamp = factory.Faker('date_time')
    field = factory.fuzzy.FuzzyChoice([v.value for v in UserLogField])
    value = factory.Faker('word')


# Topics

class DbTopicFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Topic

    id =  factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    user = factory.SubFactory(DbUserFactory)

    version = factory.Faker('pyint', max_value=100)


class DbMessageFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Message

    id =  factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    topic = factory.SubFactory(DbTopicFactory)

    version = factory.Faker('pyint', max_value=100)
    bot_message_id = factory.Faker('pyint', min_value=1000000000, max_value=9999999999)


class DbReplyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Reply

    id =  factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
    topic = factory.SubFactory(DbTopicFactory)

    version = factory.Faker('pyint', max_value=100)
    bot_message_id = factory.Faker('pyint', min_value=1000000000, max_value=9999999999)
