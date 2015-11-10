import pytest
import random

from aiotg import TgBot
from aiotg import MESSAGE_TYPES

API_TOKEN = "test_token"
bot = TgBot(API_TOKEN)

def custom_msg(msg):
    template = {
        "message_id": 0,
        "from": {},
        "chat": { "id": 0, "type": "private" }
    }
    template.update(msg)
    return template


def text_msg(text):
    return custom_msg({ "text": text })


def test_command():
    called_with = None

    @bot.command(r"/echo (.+)")
    def echo(chat, match):
        nonlocal called_with
        called_with = match.group(1)

    bot._process_message(text_msg("/echo foo"))
    assert called_with == "foo"


def test_default():
    called_with = None

    @bot.default
    def default(chat, message):
        nonlocal called_with
        called_with = message["text"]

    bot._process_message(text_msg("foo bar"))
    assert called_with == "foo bar"


@pytest.mark.parametrize("mt", MESSAGE_TYPES)
def test_handle(mt):
    called_with = None

    @bot.handle(mt)
    def handle(chat, media):
        nonlocal called_with
        called_with = media

    value = random.random()
    bot._process_message(custom_msg({ mt: value }))
    assert called_with == value
