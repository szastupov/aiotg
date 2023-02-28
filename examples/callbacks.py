import json
import os
from aiotg import Bot

bot = Bot(api_token=os.environ["API_TOKEN"])


@bot.command(r"/start")
def start(chat, match):
    markup = {
        "type": "InlineKeyboardMarkup",
        "inline_keyboard": [
            [
                {
                    "type": "InlineKeyboardButton",
                    "text": "Button A",
                    "callback_data": "buttonclick-A",
                },
                {
                    "type": "InlineKeyboardButton",
                    "text": "Button B",
                    "callback_data": "buttonclick-B",
                },
            ],
            [
                {
                    "type": "InlineKeyboardButton",
                    "text": "Nohandle Button",
                    "callback_data": "no_callback_data",
                }
            ],
        ],
    }

    chat.send_text("Hello", reply_markup=json.dumps(markup))


@bot.callback(r"buttonclick-(\w+)")
def buttonclick(chat, cq, match):
    chat.send_text("You clicked {}".format(match.group(1)))


@bot.default_callback
def unhandled_callbacks(chat, cq):
    chat.send_text("Unhandled callback fired")


bot.run(debug=True)
