from telegram import Update
from telegram.ext import ContextTypes

from feedbackbot.core.handlers import BaseCommandHandler


class StartCommandHandler(BaseCommandHandler):
    name = 'start'
    help = 'Начать работу'

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text_md = (f'Добро пожаловать в бот обратной связи нашей команды\.\n'
                   f'\n'
                   f'Напишите кратко суть вашего обращения, и мы постараемся ответить как можно скорее\.')
        await update.message.reply_text(text_md, parse_mode='MarkdownV2')


class HelpCommandHandler(BaseCommandHandler):
    name = 'help'
    help = 'Вывести справку'

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text_md = (
            f'Использовать бот обратной связи просто:\n'
            f'\n'
            f'\- Вы отправляете в бот сообщения, оператор отвечает вам\.\n'
            f'\- Введите символ `/`, и бот покажет вам список доступных команд\.\n'
        )

        await update.message.reply_text(text_md, parse_mode='MarkdownV2')
