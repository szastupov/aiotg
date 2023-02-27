import pytest
import random

from aiotg import Bot, Chat, InlineQuery
from aiotg import MESSAGE_TYPES, MESSAGE_UPDATES
from aiotg.mock import MockBot
from testfixtures import LogCapture

API_TOKEN = "test_token"
bot = Bot(API_TOKEN)


def custom_msg(msg):
    template = {
        "message_id": 0,
        "from": {"first_name": "John"},
        "chat": {"id": 0, "type": "private"},
    }
    template.update(msg)
    return template


def text_msg(text):
    return custom_msg({"text": text})


def inline_query(query):
    return {"from": {"first_name": "John"}, "offset": "", "query": query, "id": "9999"}


def chosen_inline_result(query):
    return {"from": {"first_name": "John"}, "query": query, "result_id": "9999"}


def callback_query(data):
    return {
        "from": {"first_name": "John"},
        "data": data,
        "id": "9999",
        "message": custom_msg({}),
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


def test_default_inline():
    called_with = None

    @bot.inline
    def inline(query):
        nonlocal called_with
        called_with = query.query

    bot._process_inline_query(inline_query("foo bar"))
    assert called_with == "foo bar"


def test_inline():
    called_with = None

    @bot.inline(r"query-(\w+)")
    def inline(query, match):
        nonlocal called_with
        called_with = match.group(1)

    bot._process_inline_query(inline_query("query-foo"))
    assert called_with == "foo"


def test_default_chosen_inline_result():
    called_with = None

    @bot.chosen_inline_result_callback
    def chosen_inline_result_callback(query):
        nonlocal called_with
        called_with = query.query

    bot._process_chosen_inline_result(chosen_inline_result("foo bar"))
    assert called_with == "foo bar"


def test_chosen_inline_result():
    called_with = None

    @bot.chosen_inline_result_callback(r"query-(\w+)")
    def chosen_inline_result_callback(query, match):
        nonlocal called_with
        called_with = match.group(1)

    bot._process_chosen_inline_result(chosen_inline_result("query-foo"))
    assert called_with == "foo"


def test_callback_default():
    bot._process_callback_query(callback_query("foo"))


def test_default_callback():
    called_with = None

    @bot.callback
    def callback(chat, cq):
        nonlocal called_with
        called_with = cq.data

    bot._process_callback_query(callback_query("foo"))
    assert called_with == "foo"


def test_callback():
    called_with = None

    @bot.callback(r"click-(\w+)")
    def click_callback(chat, cq, match):
        nonlocal called_with
        called_with = match.group(1)

    bot._process_callback_query(callback_query("click-foo"))
    assert called_with == "foo"


@pytest.mark.parametrize("upd_type", MESSAGE_UPDATES)
def test_message_updates(upd_type):
    update = {"update_id": 0, upd_type: text_msg("foo bar")}
    updates = {"result": [update], "ok": True}
    called_with = None

    @bot.default
    def default(chat, message):
        nonlocal called_with
        called_with = message["text"]

    bot._process_updates(updates)
    assert called_with == "foo bar"


def test_updates_failed():
    updates = {"ok": False, "description": "Opps"}

    with LogCapture() as log:
        bot._process_updates(updates)
        log.check(("aiotg", "ERROR", "getUpdates error: Opps"))


@pytest.mark.parametrize("mt", MESSAGE_TYPES)
def test_handle(mt):
    called_with = None

    @bot.handle(mt)
    def handle(chat, media):
        nonlocal called_with
        called_with = media

    value = random.random()
    bot._process_message(custom_msg({mt: value}))
    assert called_with == value


@pytest.mark.parametrize(
    "ctype,id", [("channel", "@foobar"), ("private", "111111"), ("group", "222222")]
)
def test_channel_constructors(ctype, id):
    chat = getattr(bot, ctype)(id)
    assert chat.id == id
    assert chat.type == ctype


def test_chat_methods():
    bot = MockBot()
    chat_id = 42
    chat = Chat(bot, chat_id)

    chat.send_text("hello")
    assert "sendMessage" in bot.calls
    assert bot.calls["sendMessage"]["text"] == "hello"


def test_send_methods():
    bot = MockBot()
    chat_id = 42
    chat = Chat(bot, chat_id)

    chat.send_audio(b"foo")
    assert "sendAudio" in bot.calls

    chat.send_voice(b"foo")
    assert "sendVoice" in bot.calls

    chat.send_photo(b"foo")
    assert "sendPhoto" in bot.calls

    chat.send_sticker(b"foo")
    assert "sendSticker" in bot.calls

    chat.send_video(b"foo")
    assert "sendVideo" in bot.calls

    chat.send_document(b"foo")
    assert "sendDocument" in bot.calls

    chat.send_location(13.0, 37.0)
    assert "sendLocation" in bot.calls

    chat.send_venue(13.0, 37.0, b"foo", b"foo")
    assert "sendVenue" in bot.calls

    chat.send_contact("+79260000000", b"foo")
    assert "sendContact" in bot.calls

    chat.send_chat_action("typing")
    assert "sendChatAction" in bot.calls

    chat.send_media_group("foo")
    assert "sendMediaGroup" in bot.calls

    chat.delete_message(1111)
    assert "deleteMessage" in bot.calls


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

    results = [
        {"type": "article", "id": "000", "title": "test", "message_text": "Foo bar"}
    ]
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


def test_edit_reply_markup():
    bot = MockBot()
    chat_id = 42
    message_id = 1337
    chat = Chat(bot, chat_id)

    chat.edit_reply_markup(message_id, {"inline_keyboard": [["ok", "cancel"]]})
    assert "editMessageReplyMarkup" in bot.calls
    call = bot.calls["editMessageReplyMarkup"]
    assert call["reply_markup"] == '{"inline_keyboard": [["ok", "cancel"]]}'
    assert call["message_id"] == message_id
