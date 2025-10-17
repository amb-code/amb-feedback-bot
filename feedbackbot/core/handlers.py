from abc import abstractmethod, ABCMeta

from telegram import Update
from telegram.ext import ContextTypes, Application


class BaseCommandHandler(metaclass=ABCMeta):
    name: str
    help: str

    @abstractmethod
    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    @classmethod
    def install(cls, app: Application):
        pass

    @classmethod
    def help_for_role(cls, role: str):
        return f'{cls.help} ({role})'
