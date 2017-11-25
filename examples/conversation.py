import os
from random import randint
from aiotg import Bot, Chat

bot = Bot(os.environ["API_TOKEN"])


@bot.command(r"^/game$")
async def echo(chat: Chat, match):
    number = randint(1, 1000)
    await chat.send_text("Hello, give me a number")
    while True:
        response = await chat.response(r'^\d+$', unexpected='Sorry, I did not understand.')
        if response:
            response = int(response.group())
            if response > number:
                await chat.send_text('high')
            elif response < number:
                await chat.send_text('low')
            else:
                await chat.send_text('Correct!')
                break


if __name__ == '__main__':
    bot.run(debug=True)
