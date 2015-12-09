import re
import logging
import asyncio
import aiohttp
import json

from functools import partialmethod
from . chat import TgChat

__author__ = "Stepan Zastupov"
__copyright__ = "Copyright 2015, Stepan Zastupov"
__license__ = "MIT"

API_URL = "https://api.telegram.org"
API_TIMEOUT = 60
RETRY_TIMEOUT = 30
RETRY_CODES = [429, 500, 502, 503, 504]
BOTAN_URL = "https://api.botan.io/track"

MESSAGE_TYPES = [
    "location", "photo", "document", "audio", "voice", "sticker", "contact"
]


logger = logging.getLogger("aiotg")


class TgBot:

    """Telegram bot framework designed for asyncio"""

    def __init__(self, api_token, api_timeout=API_TIMEOUT,
                 botan_token=None, name=None):
        """
        api_token - Telegram bot token, ask @BotFather for this
        api_timeout (optional) - Timeout for long polling
        botan_token (optional) - Token for http://botan.io
        name (optional) - Bot name
        """
        self.api_token = api_token
        self.api_timeout = api_timeout
        self.botan_token = botan_token
        self.name = name

        self._running = False
        self._offset = 0
        self._default = lambda c, m: None

        def no_handle(mt):
            return lambda chat, msg: logger.debug("no handle for %s", mt)

        self._handlers = {mt: no_handle(mt) for mt in MESSAGE_TYPES}
        self._commands = []

    @asyncio.coroutine
    def api_call(self, method, **params):
        """Call Telegram API
        See https://core.telegram.org/bots/api for the reference
        """
        url = "{0}/bot{1}/{2}".format(API_URL, self.api_token, method)
        response = yield from aiohttp.post(url, data=params)

        if response.status == 200:
            return (yield from response.json())
        elif response.status in RETRY_CODES:
            logger.info("Server returned %d, retrying in %d sec.",
                        response.status, RETRY_TIMEOUT)
            yield from response.release()
            yield from asyncio.sleep(RETRY_TIMEOUT)
            return (yield from self.api_call(method, **params))
        else:
            if response.headers['content-type'] == 'application/json':
                err_msg = (yield from response.json())["description"]
            else:
                err_msg = yield from response.read()
            logger.error(err_msg)
            raise RuntimeError(err_msg)

    _send_message = partialmethod(api_call, "sendMessage")

    def send_message(self, chat_id, text, **kwargs):
        """Send a text message to chat"""
        return self._send_message(chat_id=chat_id, text=text, **kwargs)

    def command(self, regexp):
        """Decorator for registering commands

        Example:
        @bot.command(r"/(start|help)")
        def usage(message, match):
            pass
        """
        def decorator(fn):
            self._commands.append((regexp, fn))
            return fn
        return decorator

    def default(self, callback):
        """Set callback for default command
        Default command is called on unrecognized commands for 1to1 chats
        """
        self._default = callback
        return callback

    def handle(self, msg_type):
        """Set handler for specific message type

        Example:
        @bot.handle("audio")
        def handle(chat, audio):
            pass
        """
        def wrap(callback):
            self._handlers[msg_type] = callback
            return callback
        return wrap

    @asyncio.coroutine
    def _track(self, message, name):
        response = yield from aiohttp.post(
            BOTAN_URL,
            params={
                "token": self.botan_token,
                "uid": message["from"]["id"],
                "name": name
            },
            data=json.dumps(message),
            headers={'content-type': 'application/json'}
        )
        if response.status != 200:
            logger.info("error submiting stats %d", response.status)
        yield from response.release()

    def track(self, message, name="Message"):
        if self.botan_token:
            asyncio.async(self._track(message, name))

    def _process_message(self, message):
        chat = TgChat.from_message(self, message)

        for mt in MESSAGE_TYPES:
            if mt in message:
                self.track(message, mt)
                return self._handlers[mt](chat, message[mt])

        text = message.get("text")
        if not text:
            return

        for patterns, handler in self._commands:
            m = re.search(patterns, text, re.I)
            if m:
                self.track(message, handler.__name__)
                return handler(chat, m)

        # No match, run default if it's a 1to1 chat
        if not chat.is_group():
            self.track(message, "default")
            return self._default(chat, message)

    def _process_updates(self, updates):
        if not updates["ok"]:
            logger.error("getUpdates error: %s", updates.get("description"))
            return

        for update in updates["result"]:
            logger.debug("update %s", update)
            self._offset = max(self._offset, update["update_id"])
            message = update["message"]
            coro = self._process_message(message)
            if coro:
                asyncio.async(coro)

    @asyncio.coroutine
    def loop(self):
        """Return bot's main loop as coroutine

        Use it with asyncio:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.loop())

        or:
        loop.create_task(bot.loop())
        """
        self._running = True
        while self._running:
            updates = yield from self.api_call(
                'getUpdates',
                offset=self._offset + 1,
                timeout=self.api_timeout
            )
            self._process_updates(updates)

    def stop(self):
        self._running = False

    def run(self):
        """Convenience method for running bots

        Example:
        if __name__ == '__main__':
            bot.run()
        """
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.loop())
        except KeyboardInterrupt:
            self.stop()
