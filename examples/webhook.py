import os
from aiotg import Bot

bot = Bot(api_token=os.environ["API_TOKEN"])
bot.set_webhook(url='https://yourserver.com/webhook/fdhgufdgh98498gvneriug489')


@bot.command(r"/echo (.+)")
def echo(chat, match):
    return chat.reply(match.group(1))


bot.run()
