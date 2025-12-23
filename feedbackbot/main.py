from feedbackbot.bot import app


if __name__ == '__main__':
    app.run_polling(
        poll_interval=1,
        # установить на True чтобы бот не получал пропущенные уведомления
        drop_pending_updates=False
    )
