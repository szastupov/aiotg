import os
from aiotg import TgBot

bot = TgBot(os.environ["API_TOKEN"])

@bot.command(r"/getimage")
def getimage(chat, match):
    return chat.send_photo(photo=open("cc.large.png", "rb"))

if __name__ == '__main__':
    bot.run()
