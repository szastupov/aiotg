import re
import logging
import asyncio
import aiohttp

from functools import partialmethod

__author__ = "Stepan Zastupov"
__copyright__ = "Copyright 2015, Stepan Zastupov"
__license__ = "MIT"

API_URL = "https://api.telegram.org"
API_TIMEOUT = 60


class TgMessage:
    """High-level wrapper around Telegram message"""
    def __init__(self, bot, data):
        self.bot = bot
        self.data = data
        self.sender = data['from'].get('username', data['from']['first_name'])

    def reply(self, text):
        """Reply to this message"""
        return self.bot._send_message(
            chat_id=self.data["chat"]["id"],
            text=text,
            disable_web_page_preview='true',
            reply_to_message_id=self.data["message_id"]
        )

    def is_group(self):
        return "chat" in self.data and "title" in self.data["chat"]


class TextMessage(TgMessage):
    @property
    def text(self):
        return self.data["text"]


class LocationMessage(TgMessage):
    @property
    def location(self):
        return self.data["location"]


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
        conn = aiohttp.TCPConnector(verify_ssl=False)
        self.session = aiohttp.ClientSession(connector=conn)
        self._running = True
        self._default = lambda m: None
        self._location = lambda m: None

    @asyncio.coroutine
    def api_call(self, method, **params):
        """Call Telegram API
        See https://core.telegram.org/bots/api for the reference
        """
        url = "{0}/bot{1}/{2}".format(API_URL, self.api_token, method)
        response = yield from self.session.request('POST', url, data=params)
        assert response.status == 200
        return (yield from response.json())

    _send_message = partialmethod(api_call, "sendMessage")

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

    def location(self, callback):
        """Set callback for location messages"""
        self._location = callback
        return callback

    @asyncio.coroutine
    def _process_message(self, message):
        if "location" in message:
            return self._location(LocationMessage(self, message))

        if "text" not in message:
            return

        text = message["text"].lower()
        tgm = TextMessage(self, message)

        for patterns, handler in self.commands:
            m = re.search(patterns, text)
            if m:
                return handler(tgm, m)

        # No match, run default if it's a 1to1 chat
        if not tgm.is_group():
            return self._default(tgm)

    def stop(self):
        self._running = False
        self.session.close()

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
                offset=offset+1,
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
