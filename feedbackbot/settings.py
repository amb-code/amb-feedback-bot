from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from environs import env

load_dotenv()

ENVIRONMENT = env('ENVIRONMENT', 'development')
DEBUG = (
    env.bool('DEBUG', False)
    or env.bool('CI', False)
    or env.bool('PYTEST_RUN_CONFIG', False)
)  # yapf: disable

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
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'feedbackbot': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        }
    },
}

# DB

DB_USERNAME = env('DB_USERNAME', 'postgres')
DB_PASSWORD = env('DB_PASSWORD', 'postgres')
DB_HOST = env('DB_HOST', 'localhost')
DB_PORT = env.int('DB_PORT', 5432)
DB_NAME = env('DB_NAME', 'feedback_bot')

DB_URI = (
    f'postgresql+asyncpg://{quote_plus(DB_USERNAME)}:{quote_plus(DB_PASSWORD)}'
    f'@{DB_HOST}:{DB_PORT}/{quote_plus(DB_NAME)}'
)

# Commands

COMMANDS = {
    'createdb': 'feedbackbot.core.commands.create_db',
    'cleandb': 'feedbackbot.core.commands.clean_db',
}

# Telegram

TOKEN = env('TG_TOKEN')
BOT_ID = int(TOKEN.split(':')[0]) if TOKEN else None
CHAT_ID = env.int('TG_CHAT_ID')

# Sentry

SENTRY_DSN = env('SENTRY_DSN', None)
