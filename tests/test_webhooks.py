import asyncio
import pytest
from urllib.parse import urlparse
from aiohttp import web
from aiotg.mock import MockBot
from threading import Thread, Event

# ⚠️  beware, this test is a total hack ⚠️

webhook_url = "http://localhost:6666/webhook"
server_started = Event()


def bot_loop(bot):
    url = urlparse(webhook_url)
    loop = asyncio.new_event_loop()
    app = bot.create_webhook_app(url.path, loop)
    server_started.set()
    web.run_app(app, port=url.port)


@pytest.mark.skip()
def test_webhooks_integration():
    bot = MockBot()
    called_with = None

    @bot.command(r"/echo (.+)")
    def echo(chat, match):
        nonlocal called_with
        called_with = match.group(1)
        # Let's check sender repr as well
        assert repr(chat.sender) == "John"

    bot.set_webhook(webhook_url)
    assert "setWebhook" in bot.calls

    thread = Thread(target=bot_loop, args=[bot], daemon=True)
    thread.start()
    server_started.wait()

    update = {
        "update_id": 0,
        "message": {
            "message_id": 0,
            "from": {"first_name": "John"},
            "chat": {"id": 0, "type": "private"},
            "text": "/echo foo",
        },
    }

    import requests

    requests.post(webhook_url, json=update)
    assert called_with == "foo"


def test_set_webhook():
    bot = MockBot()
    bot.set_webhook(webhook_url)
    assert "setWebhook" in bot.calls
    assert "secret_token" in bot.calls["setWebhook"]


def test_delete_webhook():
    bot = MockBot()
    bot.delete_webhook()
    assert "deleteWebhook" in bot.calls
