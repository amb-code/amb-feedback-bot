import logging
import traceback

import sentry_sdk
from telegram import Update
from telegram.ext import ContextTypes

from feedbackbot import settings

logger = logging.getLogger(__name__)


class RootErrorHandler:

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if settings.SENTRY_DSN:
            logger.debug(f'Logging error to Sentry: {context.error}')
            sentry_sdk.capture_exception(context.error)
        else:
            logger.error(
                f'Update {update} caused error: {context.error}\n'
                f'\n'
                f'{traceback.format_exc()}'
            )
