import pytest
import random

import asyncio
from tempfile import mkstemp
from urllib.request import urlretrieve

from aiotg import TgBot
from aiotg import MESSAGE_TYPES
from testfixtures import LogCapture

API_TOKEN = "test_token"
bot = TgBot(API_TOKEN)

def custom_msg(msg):
    template = {
        "message_id": 0,
        "from": { "first_name": "John" },
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
        # Let's check sender repr as well
        assert repr(chat.sender) == "John"

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


def test_updates():
    update = {
        "update_id" : 0,
        "message": text_msg("foo bar")
    }
    updates = { "result": [update], "ok": True }
    called_with = None

    @bot.default
    def default(chat, message):
        nonlocal called_with
        called_with = message["text"]

    bot._process_updates(updates)
    assert called_with == "foo bar"


def test_updates_failed():
    updates = {
        "ok": False,
        "description": "Opps"
    }

    with LogCapture() as l:
        bot._process_updates(updates)
        l.check(('aiotg', 'ERROR', 'getUpdates error: Opps'))


def get_some_image_file_path(extension=None):
    if extension is None:
        extension = 'jpg'

    _, image_path = mkstemp(suffix='.' + extension)

    urlretrieve('https://avatars3.githubusercontent.com/u/24799',
                filename=image_path)

    return image_path


def test_apicall_sendphoto():
    loop = asyncio.get_event_loop()

    chat_id = text_msg({'foo'})['chat']['id']
    fp = open(get_some_image_file_path('jpg'), 'rb')

    res = loop.run_until_complete(bot.api_call('sendPhoto', chat_id=chat_id, photo=fp))

    assert res['ok'] == True
    assert 'result' in res
    assert 'photo' in res['result']


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
