import os
from aiotg import Bot

bot = Bot(os.environ["API_TOKEN"])


@bot.command("whoami")
def whoami(chat, match):
    return chat.reply(chat.sender["id"])


if __name__ == '__main__':
    bot.run()
