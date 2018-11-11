import os
from aiotg import Bot

bot = Bot(api_token=os.environ["API_TOKEN"])


@bot.command(r"/echo (.+)")
def echo(chat, match):
    return chat.reply(match.group(1))


bot.run_webhook(webhook_url="https://yourserver.com/webhook/fdhgufdgh98498gvneriug489")
