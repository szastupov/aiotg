import os
from aiotg import TgBot

bot = TgBot(os.environ["API_TOKEN"])

@bot.command(r"/echo (.+)")
def wiki_de(message, match):
    return message.reply(match.group(1))

if __name__ == '__main__':
    bot.run()
