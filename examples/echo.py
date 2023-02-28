from aiotg import Bot, Chat

bot = Bot(api_token="API_TOKEN")


@bot.command(r"/echo (.+)")
def echo(chat: Chat, match):
    return chat.reply(match.group(1))


if __name__ == "__main__":
    bot.run(debug=True)
