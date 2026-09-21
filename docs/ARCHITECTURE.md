# Архитектура

Карта текущего кода: куда смотреть, а не как устроен каждый метод. Зачем система устроена так — в [концепции](CONCEPT.md). Как запускать — в [README](../README.md).

## С высоты

Два входа в один процесс, который ходит в Telegram и в PostgreSQL.

1. Личка. `MessageHandler` на приватный чат вызывает `ForwardMessageHandler`: пользователь в БД, топик в супергруппе, `forward` сообщения, лог имени.
2. Топик колл-центра. Команды (`/ban`, `/delete` и остальные) и `MessageHandler` на reply вызывают сервисы: ответ или правка уходят в личку, бан пишется в БД.

Оба пути сходятся в PostgreSQL (SQLAlchemy async) и в `telegram.Bot`. Граф зависимостей собирает `DIAsync`. Handlers регистрирует `post_init` в `bot.py`. Вход процесса — polling в `main.py`.

## Карта кода

Пакет приложения — `feedbackbot`. `users` и `topics` держат свой кусок предметной области: handlers, services, repos, models.

- `bot.py` — `Application`, роли (`ptbcontrib.roles`), `set_my_commands`, порядок handlers.
- `main.py` — `run_polling`.
- `settings.py` — env: токен, `TG_CHAT_ID`, `DB_*`, Sentry.
- `core/di.py` — `DIAsync`: repos, services, handlers, engine и session.
- `core/db.py` — `Base`, `BaseAsyncDBRepo`, сессии.
- `core/handlers.py` — `BaseCommandHandler`.
- `core/management.py` и `core/commands.py` — `createdb` / `cleandb` через `manage.py`.
- `common/handlers.py` — `/start`, `/help`.
- `users/` — `User`, `UserLog`; `ForwardMessageHandler`, `UserService`; бан и userlog.
- `topics/` — `Topic`; `Message` (личка и форвард в группе) и `Reply` (сообщение оператора и копия в личке); `ReplyMessageHandler`, `TopicService`; удаление; имя топика — `sanitize_topic_name`.
- `handlers.py` в корне пакета — `RootErrorHandler`.

Тесты зеркалят пакеты: `tests/unit/` (сервис и подставные repos), `tests/integration/` (handler, `MockBot`, mocked DB). Фабрики — `tests/factories/`.

## Границы и инварианты

Слойность и запреты, которые из кода не очевидны.

**Architecture Invariant.** Handler не ходит в repo. Только service.

**Architecture Invariant.** Ответ пользователю — только reply на форвард бота (`forward_origin` и `from_user.id` бота). Прочий трафик топика в личку не уходит.

**Architecture Invariant.** Операторские команды и reply в группе обёрнуты в `RolesHandler`: админы группы плюс роль `operators` на `CHAT_ID`. Личка открыта всем.

**Architecture Invariant.** Команды регистрируются до `MessageHandler`, иначе команда в топике обрабатывается как обычное сообщение.

**API Boundary.** Внешний протокол — Telegram `Update`. Сервисы принимают типы python-telegram-bot (`User`, `Message`, `Bot`) и вызывают Bot API сами. Отдельного слоя DTO нет.

Отсутствия: HTTP API нет; webhook нет (только polling); синхронного SQLAlchemy нет; очереди и второго процесса нет; миграций схемы нет (`create_all` при старте).

## Сквозное

То, что не живёт в одном пакете.

- DI: зависимости в конструктор, `dependencies.Injector`. Глобального сервис-локатора в пакетах нет.
- БД: `postgresql+asyncpg`, `NullPool`, `async_sessionmaker`.
- Конфиг: только env, секреты не в репозитории.
- Логи: `logging.getLogger(__name__)`, dictConfig из settings.
- Ошибки Telegram: `Forbidden`, если пользователь заблокировал бота; `BadRequest` с кодами топика. Без Sentry — в лог, с `SENTRY_DSN` — ещё и в Sentry.
- Лимит Bot API: `AIORateLimiter` на `Application`.
- Деплой: Docker (Python 3.12), Compose, Ansible — снаружи пакета приложения.
