[![Master branch PR merge pipeline](https://github.com/amb-code/amb-feedback-bot/actions/workflows/master.yml/badge.svg)](https://github.com/amb-code/amb-feedback-bot/actions/workflows/master.yml)

# AMB Feedback Bot

A Telegram feedback bot for teams.

At the moment, the bot has the following features:
- allows you to anonymously communicate with users in Telegram
- dialogue with each user is conducted in a separate topic
- issuing and removing bans
- editing previous messages
- control of the chat history: the chat operator can delete a user or their own
  messages, or completely clear the chat history on the user side
- control of the user data history: the bot notifies about a change in the full 
  name or user name, it is possible to see the full history of changes
- Sentry error monitoring


## Running the  bot

### Telegram prerequisites

To run the bot you'll need to do the following on the Telegram side:

- Bot token, the one you got from the [@BotFather](https://t.me/BotFather) when you created your bot
- Create a private group chat
- Get chat ID: [how to get a group chat id](https://stackoverflow.com/questions/32423837/telegram-bot-how-to-get-a-group-chat-id)
- Add the bot to the chat
- Give it the required permissions

  ![required_permissions](./docs/bot_premissions.png)

### Enable monitoring 

Optionally: create a Sentry project and get a Sentry DSN. However, it's not 
required to run the bot. 

### Running with docker compose
- clone the repo
- create `db.env` from [db.env.example](env/db.env.example)
- create `bot.env` from [bot.env.example](env/bot.env.example) using the values 
  from the previous steps 
- run `docker compose up -d`


## Local development

The recommended way is to use virtualenv. Note that project conventions
suggest that you keep your venv inside the VCS root.

Clone the repo:

    $ git clone git@github.com:amb-code/amb-feedback-bot.git

Create the environment:

    $ cd amb-feedback-bot
    $ virtualenv -p python3 venv

Install development packages:

    $ source venv/bin/activate
    $ pip install -r requirements.txt
    $ pip install -r requirements-dev.txt

Create an .env file from [.env.example](.env.example).

Run the development server:

    $ python main.py 


## Release flow

- create a feature branch
- update the code and tests
- open an PRR
- make sure the branch has been deployed successfully, unit and integration 
  tests pass
- merge rge PR
