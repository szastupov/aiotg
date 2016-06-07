import re
import logging
import asyncio
import aiohttp
import json

from functools import partialmethod
from . chat import Chat, Sender

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


class Bot:
    """Telegram bot framework designed for asyncio

    :param api_token: Telegram bot token, ask @BotFather for this
    :param api_timeout: Timeout for long polling
    :param botan_token: Token for http://botan.io
    :param name: Bot name
    """

    _running = False
    _offset = 0

    def __init__(self, api_token, api_timeout=API_TIMEOUT,
                 botan_token=None, name=None):
        self.api_token = api_token
        self.api_timeout = api_timeout
        self.botan_token = botan_token
        self.name = name

        def no_handle(mt):
            return lambda chat, msg: logger.debug("no handle for %s", mt)

        self._handlers = {mt: no_handle(mt) for mt in MESSAGE_TYPES}
        self._commands = []
        self._default = lambda c, m: None
        self._inline = lambda iq: None
        self._callback = lambda c, cq: None

    @asyncio.coroutine
    def loop(self):
        """
        Return bot's main loop as coroutine

        Use it with asyncio:
        >>> loop = asyncio.get_event_loop()
        >>> loop.run_until_complete(bot.loop())

        or:
        >>> loop.create_task(bot.loop())
        """
        self._running = True
        while self._running:
            updates = yield from self.api_call(
                'getUpdates',
                offset=self._offset + 1,
                timeout=self.api_timeout
            )
            self._process_updates(updates)

    def run(self):
        """
        Convenience method for running bots

        :Example:
        >>> if __name__ == '__main__':
        >>>     bot.run()
        """
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.loop())
        except KeyboardInterrupt:
            self.stop()

    def command(self, regexp):
        """
        Register a new command

        :Example:
        >>> @bot.command(r"/echo (.+)")
        >>> def echo(chat, match):
        >>>     return chat.reply(match.group(1))
        """
        def decorator(fn):
            self._commands.append((regexp, fn))
            return fn
        return decorator

    def default(self, callback):
        """
        Set callback for default command that is
        called on unrecognized commands for 1to1 chats

        :Example:
        >>> @bot.default
        >>> def echo(chat, message):
        >>>     return chat.reply(message["text"])
        """
        self._default = callback
        return callback

    def inline(self, callback):
        """
        Set callback for inline queries

        :Example:
        >>> @bot.inline
        >>> def echo(iq):
        >>>     return iq.answer([
        >>>         {"type": "text", "title": "test", "id", "0"}
        >>>     ])
        """
        self._inline = callback
        return callback

    def callback(self, callback):
        """
        Set callback for callback queries

        :Example:
        >>> @bot.callback
        >>> def echo(chat, cq):
        >>>     return cq.answer()
        """
        self._callback = callback
        return callback

    def handle(self, msg_type):
        """
        Set handler for specific message type

        :Example:
        >>> @bot.handle("audio")
        >>> def handle(chat, audio):
        >>>     pass
        """
        def wrap(callback):
            self._handlers[msg_type] = callback
            return callback
        return wrap

    async def api_call(self, method, **params):
        """
        Call Telegram API
        See https://core.telegram.org/bots/api for the reference
        """
        url = "{0}/bot{1}/{2}".format(API_URL, self.api_token, method)
        logger.debug("api_call %s, %s", method, params)
        response = await aiohttp.post(url, data=params)

        if response.status == 200:
            return (await response.json())
        elif response.status in RETRY_CODES:
            logger.info("Server returned %d, retrying in %d sec.",
                        response.status, RETRY_TIMEOUT)
            await response.release()
            await asyncio.sleep(RETRY_TIMEOUT)
            return (await self.api_call(method, **params))
        else:
            if response.headers['content-type'] == 'application/json':
                err_msg = (await response.json())["description"]
            else:
                err_msg = await response.read()
            logger.error(err_msg)
            raise RuntimeError(err_msg)

    _send_message = partialmethod(api_call, "sendMessage")

    def send_message(self, chat_id, text, **options):
        """Send a text message to chat"""
        return self._send_message(chat_id=chat_id, text=text, **options)

    @asyncio.coroutine
    def get_file(self, file_id):
        """
        https://core.telegram.org/bots/api#getfile
        """
        json = yield from self.api_call("getFile", file_id=file_id)
        return json["result"]

    def download_file(self, file_path, range=None):
        """
        Dowload a file from Telegram servers
        """
        headers = {"range": range} if range else None
        url = "{0}/file/bot{1}/{2}".format(API_URL, self.api_token, file_path)
        return aiohttp.get(url, headers=headers)

    def track(self, message, name="Message"):
        """
        Track message using http://botan.io
        Set botak_token to make it work
        """
        if self.botan_token:
            asyncio.async(self._track(message, name))

    def stop(self):
        self._running = False

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

    def _process_message(self, message):
        chat = Chat.from_message(self, message)

        for mt in MESSAGE_TYPES:
            if mt in message:
                self.track(message, mt)
                return self._handlers[mt](chat, message[mt])

        if "text" not in message:
            return

        for patterns, handler in self._commands:
            m = re.search(patterns, message["text"], re.I)
            if m:
                self.track(message, handler.__name__)
                return handler(chat, m)

        # No match, run default if it's a 1to1 chat
        if not chat.is_group():
            self.track(message, "default")
            return self._default(chat, message)

    def _process_inline_query(self, query):
        iq = InlineQuery(self, query)
        return self._inline(iq)

    def _process_callback_query(self, query):
        chat = Chat.from_message(self, query["message"])
        cq = CallbackQuery(self, query)
        return self._callback(chat, cq)

    def _process_updates(self, updates):
        if not updates["ok"]:
            logger.error("getUpdates error: %s", updates.get("description"))
            return

        for update in updates["result"]:
            logger.debug("update %s", update)
            self._offset = max(self._offset, update["update_id"])
            coro = None

            if "message" in update:
                coro = self._process_message(update["message"])
            elif "inline_query" in update:
                coro = self._process_inline_query(update["inline_query"])
            elif "callback_query" in update:
                coro = self._process_callback_query(update["callback_query"])

            if coro:
                asyncio.async(coro)


class TgBot(Bot):
    def __init__(self, *args, **kwargs):
        logger.warning("TgBot is depricated, use Bot instead")
        super().__init__(*args, **kwargs)


class InlineQuery:
    """
    Incoming inline query
    See https://core.telegram.org/bots/api#inline-mode for details
    """

    def __init__(self, bot, src):
        self.bot = bot
        self.sender = Sender(src['from'])
        self.query_id = src['id']
        self.query = src['query']

    def answer(self, results, **options):
        return self.bot.api_call(
            "answerInlineQuery",
            inline_query_id=self.query_id,
            results=json.dumps(results),
            **options
        )


class TgInlineQuery(InlineQuery):
    def __init__(self, *args, **kwargs):
        logger.warning("TgInlineQuery is depricated, use InlineQuery instead")
        super().__init__(*args, **kwargs)


class CallbackQuery:
    def __init__(self, bot, src):
        self.bot = bot
        self.query_id = src['id']
        self.data = src['data']

    def answer(self):
        return self.bot.api_call(
            "answerCallbackQuery",
            callback_query_id=self.query_id
        )
