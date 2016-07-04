import pytest
import random

from aiotg import Bot, Chat, InlineQuery
from aiotg import MESSAGE_TYPES
from testfixtures import LogCapture

API_TOKEN = "test_token"
bot = Bot(API_TOKEN)


def custom_msg(msg):
    template = {
        "message_id": 0,
        "from": {"first_name": "John"},
        "chat": {"id": 0, "type": "private"}
    }
    template.update(msg)
    return template


def text_msg(text):
    return custom_msg({"text": text})


def inline_query(query):
    return {
        "from": {"first_name": "John"},
        "offset": "",
        "query": query,
        "id": "9999"
    }


def callback_query(data):
    return {
        "from": {"first_name": "John"},
        "data": data,
        "id": "9999",
        "message": custom_msg({})
    }


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


def test_inline():
    called_with = None

    @bot.inline
    def inline(query):
        nonlocal called_with
        called_with = query.query

    bot._process_inline_query(inline_query("foo bar"))
    assert called_with == "foo bar"


def test_callback_default():
    bot._process_callback_query(callback_query("foo"))


def test_callback():
    called_with = None

    @bot.callback
    def callback(chat, cq):
        nonlocal called_with
        called_with = cq.data

    bot._process_callback_query(callback_query("foo"))
    assert called_with == "foo"


def test_updates():
    update = {
        "update_id": 0,
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


class MockBot:
    def __init__(self):
        self.calls = {}

    def api_call(self, method, **params):
        self.calls[method] = params

    def send_message(self, chat_id, text, **kwargs):
        return self.api_call(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            **kwargs
        )

    def edit_message_text(self, chat_id, message_id, text, **kwargs):
        return self.api_call(
            "editMessageText",
            message_id=message_id,
            text=text,
            **kwargs
       )


def test_chat_methods():
    bot = MockBot()
    chat_id = 42
    chat = Chat(bot, chat_id)

    chat.send_text("hello")
    assert "sendMessage" in bot.calls
    assert bot.calls["sendMessage"]["text"] == "hello"

    # Just test a single wrapper, the rest are same
    chat.send_photo()
    assert "sendPhoto" in bot.calls
    assert isinstance(bot.calls["sendPhoto"]["chat_id"], str)


def test_chat_reply():
    bot = MockBot()
    msg = text_msg("Reply!")
    chat = Chat.from_message(bot, msg)

    chat.reply("Hi " + repr(chat.sender))
    assert "sendMessage" in bot.calls
    assert bot.calls["sendMessage"]["text"] == "Hi John"


def test_inline_answer():
    bot = MockBot()
    src = inline_query("Answer!")
    iq = InlineQuery(bot, src)

    results = [{
        "type": "article", "id": "000",
        "title": "test", "message_text": "Foo bar"
    }]
    iq.answer(results)
    assert "answerInlineQuery" in bot.calls
    assert isinstance(bot.calls["answerInlineQuery"]["results"], str)

def test_edit_message():
    bot = MockBot()
    chat_id = 42
    message_id = 1337
    chat = Chat(bot, chat_id)

    chat.edit_text(message_id, "bye")
    assert "editMessageText" in bot.calls
    assert bot.calls["editMessageText"]["text"] == "bye"
    assert bot.calls["editMessageText"]["message_id"] == message_id
