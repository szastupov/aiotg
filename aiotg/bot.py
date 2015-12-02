import re
import logging
import asyncio
import aiohttp
import json

from functools import partialmethod

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

class TgSender(dict):
    def __repr__(self):
        uname = " (%s)" % self["username"] if "username" in self else ""
        return self['first_name'] + uname

class TgChat:
    def __init__(self, bot, message):
        self.bot = bot
        self.message = message
        self.sender = TgSender(message['from'])
        chat = message['chat']
        self.id = chat['id']
        self.type = chat['type']

    def send_text(self, text, **kwargs):
        return self.bot.send_message(self.id, text, **kwargs)

    def reply(self, text, markup=None):
        return self.send_text(text,
            reply_to_message_id=self.message["message_id"],
            disable_web_page_preview='true',
            reply_markup=json.dumps(markup)
        )

    def _send_to_chat(self, method, **options):
        return self.bot.api_call(
            method,
            chat_id=self.id,
            **options
        )

    send_audio = partialmethod(_send_to_chat, "sendAudio")
    send_photo = partialmethod(_send_to_chat, "sendPhoto")
    send_video = partialmethod(_send_to_chat, "sendVideo")
    send_document = partialmethod(_send_to_chat, "sendDocument")
    send_sticker = partialmethod(_send_to_chat, "sendSticker")
    send_voice = partialmethod(_send_to_chat, "sendVoice")
    send_locaton = partialmethod(_send_to_chat, "sendLocation")

    def forward_message(self, from_chat_id, message_id):
        return self.bot.api_call(
            "forwardMessage",
            chat_id=self.id,
            from_chat_id=from_chat_id,
            message_id=message_id
        )

    def is_group(self):
        return self.type == "group"


class TgBot:

    """Telegram bot framework designed for asyncio"""

    def __init__(self, api_token, api_timeout=API_TIMEOUT, botan_token=None):
        """
        api_token - Telegram bot token, ask @BotFather for this
        api_timeout (optional) - Timeout for long polling
        """
        self.api_token = api_token
        self.api_timeout = api_timeout
        self.botan_token = botan_token
        self.commands = []
        self._running = True
        self._offset = 0

        self._default = lambda c, m: None

        def no_handle(mt):
            return lambda chat, msg: logger.debug("no handle for %s", mt)
        self._handlers = {mt: no_handle(mt) for mt in MESSAGE_TYPES}

    @asyncio.coroutine
    def api_call(self, method, **params):
        """Call Telegram API
        See https://core.telegram.org/bots/api for the reference
        """
        url = "{0}/bot{1}/{2}".format(API_URL, self.api_token, method)
        formdata = aiohttp.helpers.FormData({
            k: str(v) if isinstance(v, int) else v
            for k, v in params.items()
        })
        response = yield from aiohttp.post(url, data=formdata)

        if response.status == 200:
            return (yield from response.json())
        elif response.status in RETRY_CODES:
            logger.info("Server returned %d, retrying in %d sec.", response.status, RETRY_TIMEOUT)
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
        # res = yield from response.json()
        # if res["status"] != "accepted":
        #     logger.error("error submiting statistics %s: %s",
        #         res["status"], res.get("info", ""))

    def track(self, message, name="Message"):
        if self.botan_token:
            asyncio.async(self._track(message, name))

    def _process_message(self, message):
        chat = TgChat(self, message)

        for mt in MESSAGE_TYPES:
            if mt in message:
                self.track(message, mt)
                return self._handlers[mt](chat, message[mt])

        if "text" not in message:
            return

        text = message["text"].lower()

        for patterns, handler in self.commands:
            m = re.search(patterns, text)
            if m:
                self.track(message, handler.__name__)
                return handler(chat, m)

        # No match, run default if it's a 1to1 chat
        if not chat.is_group():
            self.track(message, "default")
            return self._default(chat, message)

    def stop(self):
        self._running = False

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
        while self._running:
            updates = yield from self.api_call(
                'getUpdates',
                offset=self._offset + 1,
                timeout=self.api_timeout
            )
            self._process_updates(updates)

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
