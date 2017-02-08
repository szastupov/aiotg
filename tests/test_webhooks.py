import requests
import asyncio
from urllib.parse import urlparse
from aiohttp import web
from aiotg.mock import MockBot
from threading import Thread

# ⚠️  beware, this test is a total hack ⚠️

webhook_url = 'http://localhost:9999/webhook'


def bot_loop(bot):
    url = urlparse(webhook_url)
    loop = asyncio.new_event_loop()
    app = bot.create_webhook_app(url.path, loop)
    web.run_app(app, port=url.port)


def test_webhooks():
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

    update = {
        "update_id": 0,
        "message": {
            "message_id": 0,
            "from": {"first_name": "John"},
            "chat": {"id": 0, "type": "private"},
            "text": "/echo foo"
        }
    }

    requests.post(webhook_url, json=update)
    assert called_with == "foo"
