import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')


# Paths

ROOT_PATH = Path(__file__).resolve().parents[1]
TMP_PATH = ROOT_PATH / 'data' / 'tmp'


# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%d%b %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'cloudwatch': {
            'format': '%(levelname)s [%(name)s:%(lineno)s] %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'cloudwatch': {
            'class': 'logging.StreamHandler',
            'formatter': 'cloudwatch',
        },
    },
    'loggers': {
        'feedbackbot': {
            'handlers': ['cloudwatch'],
            'level': 'DEBUG',
            'propagate': False,
        }
    },
}


# DB

DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_URI = f'postgresql+asyncpg://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


# Commands

COMMANDS = {
    'createdb': 'feedbackbot.core.commands.create_db',
    'cleandb': 'feedbackbot.core.commands.clean_db',
}


# Telegram

TOKEN = os.getenv('TG_TOKEN')
BOT_ID = int(TOKEN.split(':')[0]) if TOKEN else None
CHAT_ID = os.getenv('TG_CHAT_ID')


# Sentry

SENTRY_DSN = os.getenv('SENTRY_DSN')
