import re
import logging
import asyncio
import aiohttp

from functools import partialmethod

from . message import *

__author__ = "Stepan Zastupov"
__copyright__ = "Copyright 2015, Stepan Zastupov"
__license__ = "MIT"

API_URL = "https://api.telegram.org"
API_TIMEOUT = 60


class TgBot:

    """Telegram bot framework designed for asyncio"""

    def __init__(self, api_token, api_timeout=API_TIMEOUT):
        """
        api_token - Telegram bot token, ask @BotFather for this
        api_timeout (optional) - Timeout for long polling
        """
        self.api_token = api_token
        self.api_timeout = api_timeout
        self.commands = []
        self._running = True

        self._default = lambda m: None

        def no_handle(mt):
            return lambda msg: logging.debug("no handle for %s", mt)
        self._handlers = {mt: no_handle(mt) for mt in MESSAGE_TYPES}

    @asyncio.coroutine
    def api_call(self, method, **params):
        """Call Telegram API
        See https://core.telegram.org/bots/api for the reference
        """
        url = "{0}/bot{1}/{2}".format(API_URL, self.api_token, method)
        response = yield from aiohttp.post(url, data=params)
        if response.status != 200:
            err_msg = yield from response.read()
            raise RuntimeError(err_msg)
        return (yield from response.json())

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
            self.commands.append((regexp, fn))
            return fn
        return decorator

    def default(self, callback):
        """Set callback for default command
        Default command is called on unrecognized commands for 1to1 chats
        """
        self._default = callback
        return callback

    def handle(self, msg_type):
        """Set handler for specific message type"""
        def wrap(callback):
            self._handlers[msg_type] = callback
            return callback
        return wrap

    @asyncio.coroutine
    def _process_message(self, message):
        chat = TgChat(self, message["chat"])

        for mt in MESSAGE_TYPES:
            if mt in message:
                return self._handlers[mt](chat, message[mt])

        if "text" not in message:
            return

        text = message["text"].lower()
        tgm = TgMessage(self, message)

        for patterns, handler in self.commands:
            m = re.search(patterns, text)
            if m:
                return handler(tgm, m)

        # No match, run default if it's a 1to1 chat
        if not chat.is_group():
            return self._default(tgm)

    def stop(self):
        self._running = False

    @asyncio.coroutine
    def loop(self):
        """Return bot's main loop as coroutine

        Use it with asyncio:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.loop())

        or:
        loop.create_task(bot.loop())
        """
        offset = 0
        while self._running:
            resp = yield from self.api_call(
                'getUpdates',
                offset=offset + 1,
                timeout=self.api_timeout)

            for update in resp["result"]:
                logging.debug("update %s", update)
                offset = max(offset, update["update_id"])
                message = update["message"]
                asyncio.async(self._process_message(message))

    def run(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.loop())
        except KeyboardInterrupt:
            self.stop()
