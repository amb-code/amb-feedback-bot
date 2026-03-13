#!/usr/bin/env python
import os

from dotenv import load_dotenv


def main():
    """ Run administrative tasks. """
    load_dotenv()
    # os.environ.setdefault('APP_MODULE', 'feedbackbot.bot.app')
    os.environ.setdefault('SETTINGS_MODULE', 'feedbackbot.settings')
    try:
        from feedbackbot.core.management import ManagementRunner
    except ImportError as exc:
        raise ImportError(
            "Couldn't import management runner. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    ManagementRunner().run()


if __name__ == '__main__':
    main()
