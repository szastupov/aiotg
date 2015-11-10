import pytest
from aiotg import TgBot
from aiotg import MESSAGE_TYPES

API_TOKEN = "test_token"

def text_msg(text):
    return {
        "message_id": 0,
        "from": {},
        "chat": { "id": 0, "type": "private" },
        "text": text
    }

def test_command():
    bot = TgBot(API_TOKEN)
    called_with = None

    @bot.command(r"/echo (.+)")
    def echo(chat, match):
        nonlocal called_with
        called_with = match.group(1)

    bot._process_message(text_msg("/echo foo"))

    assert called_with == "foo"

def test_default():
    bot = TgBot(API_TOKEN)
    called_with = None

    @bot.default
    def default(chat, message):
        nonlocal called_with
        called_with = message["text"]

    bot._process_message(text_msg("foo bar"))

    assert called_with == "foo bar"
