import os
import re
import logging
import asyncio
from urllib.parse import urlparse

import aiohttp
from aiohttp import web
import json

from functools import partialmethod
from . chat import Chat, Sender

__author__ = "Stepan Zastupov"
__copyright__ = "Copyright 2015-2017 Stepan Zastupov"
__license__ = "MIT"

API_URL = "https://api.telegram.org"
API_TIMEOUT = 60
RETRY_TIMEOUT = 30
RETRY_CODES = [429, 500, 502, 503, 504]
BOTAN_URL = "https://api.botan.io/track"

MESSAGE_TYPES = [
    "location", "photo", "document", "audio", "voice", "sticker", "contact",
    "venue", "video", "game", "contact", "delete_chat_photo", "new_chat_photo",
    "delete_chat_photo", "new_chat_member", "left_chat_member",
    "new_chat_title"
]

logger = logging.getLogger("aiotg")


class Bot:
    """Telegram bot framework designed for asyncio

    :param str api_token: Telegram bot token, ask @BotFather for this
    :param int api_timeout: Timeout for long polling
    :param str botan_token: Token for http://botan.io
    :param str name: Bot name
    """

    _running = False
    _offset = 0

    def __init__(self, api_token, api_timeout=API_TIMEOUT,
                 botan_token=None, name=None):
        self.api_token = api_token
        self.api_timeout = api_timeout
        self.botan_token = botan_token
        self.name = name
        self.webhook_url = None
        self._session = None

        def no_handle(mt):
            return lambda chat, msg: logger.debug("no handle for %s", mt)

        self._handlers = {mt: no_handle(mt) for mt in MESSAGE_TYPES}
        self._commands = []
        self._default = lambda c, m: None
        self._inline = lambda iq: None
        self._callback = lambda c, cq: None

    async def loop(self):
        """
        Return bot's main loop as coroutine. Use with asyncio.

        :Example:

        >>> loop = asyncio.get_event_loop()
        >>> loop.run_until_complete(bot.loop())

        or

        >>> loop = asyncio.get_event_loop()
        >>> loop.create_task(bot.loop())
        """
        self._running = True
        while self._running:
            updates = await self.api_call(
                'getUpdates',
                offset=self._offset + 1,
                timeout=self.api_timeout
            )
            self._process_updates(updates)

    def run(self):
        """
        Convenience method for running bots in getUpdates mode

        :Example:

        >>> if __name__ == '__main__':
        >>>     bot.run()

        """
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.loop())
        except KeyboardInterrupt:
            self.stop()

    def run_webhook(self, webhook_url, **options):
        """
        Convenience method for running bots in webhook mode

        :Example:

        >>> if __name__ == '__main__':
        >>>     bot.run_webhook(webhook_url="https://yourserver.com/webhooktoken")

        Additional documentation on https://core.telegram.org/bots/api#setwebhook
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.set_webhook(webhook_url, **options))
        if webhook_url:
            url = urlparse(webhook_url)
            app = self.create_webhook_app(url.path, loop)
            host = os.environ.get('HOST', '0.0.0.0')
            port = int(os.environ.get('PORT', 0)) or url.port
            web.run_app(app, host=host, port=port)

    def stop_webhook(self):
        """
        Use to switch from Webhook to getUpdates mode
        """
        self.run_webhook(webhook_url="")

    def add_command(self, regexp, fn):
        """
        Manually register regexp based command
        """
        self._commands.append((regexp, fn))

    def command(self, regexp):
        """
        Register a new command

        :param str regexp: Regular expression matching the command to register

        :Example:

        >>> @bot.command(r"/echo (.+)")
        >>> def echo(chat, match):
        >>>     return chat.reply(match.group(1))
        """
        def decorator(fn):
            self.add_command(regexp, fn)
            return fn
        return decorator

    def default(self, callback):
        """
        Set callback for default command that is called on unrecognized
        commands for 1-to-1 chats

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

    def channel(self, channel_name):
        """
        Construct a Chat object used to post to channel

        :param str channel_name: Channel name
        """
        return Chat(self, channel_name, "channel")

    def private(self, user_id):
        """
        Construct a Chat object used to post direct messages

        :param str user_id: User id
        """
        return Chat(self, user_id, "private")

    def group(self, group_id):
        """
        Construct a Chat object used to post group messages

        :param str group_id: Group chat id
        """
        return Chat(self, group_id, "group")

    async def api_call(self, method, **params):
        """
        Call Telegram API.

        See https://core.telegram.org/bots/api for reference.

        :param str method: Telegram API method
        :param params: Arguments for the method call
        """
        url = "{0}/bot{1}/{2}".format(API_URL, self.api_token, method)
        logger.debug("api_call %s, %s", method, params)

        response = await self.session.post(url, data=params)

        if response.status == 200:
            return await response.json()
        elif response.status in RETRY_CODES:
            logger.info("Server returned %d, retrying in %d sec.",
                        response.status, RETRY_TIMEOUT)
            await response.release()
            await asyncio.sleep(RETRY_TIMEOUT)
            return await self.api_call(method, **params)
        else:
            if response.headers['content-type'] == 'application/json':
                err_msg = (await response.json())["description"]
            else:
                err_msg = await response.read()
            logger.error(err_msg)
            raise RuntimeError(err_msg)

    async def get_me(self):
        """
        Returns basic information about the bot
        (see https://core.telegram.org/bots/api#getme)
        """
        json_result = await self.api_call("getMe")
        return json_result["result"]

    async def leave_chat(self, chat_id):
        """
        Use this method for your bot to leave a group, supergroup or channel.
        Returns True on success.

        :param int chat_id: Unique identifier for the target chat \
            or username of the target supergroup or channel \
            (in the format @channelusername)
        """
        json_result = await self.api_call("leaveChat", chat_id=chat_id)
        return json_result["result"]

    def send_message(self, chat_id, text, **options):
        """
        Send a text message to chat

        :param int chat_id: ID of the chat to send the message to
        :param str text: Text to send
        :param options: Additional sendMessage options
            (see https://core.telegram.org/bots/api#sendmessage)
        """
        return self.api_call("sendMessage", chat_id=chat_id, text=text, **options)

    def edit_message_text(self, chat_id, message_id, text, **options):
        """
        Edit a text message in a chat

        :param int chat_id: ID of the chat the message to edit is in
        :param int message_id: ID of the message to edit
        :param str text: Text to edit the message to
        :param options: Additional API options
        """
        return self.api_call(
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            **options
        )

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup, **options):
        """
        Edit a reply markup of message in a chat

        :param int chat_id: ID of the chat the message to edit is in
        :param int message_id: ID of the message to edit
        :param str reply_markup: New inline keyboard markup for the message
        :param options: Additional API options
        """
        return self.api_call(
            "editMessageReplyMarkup",
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
            **options
        )

    async def get_file(self, file_id):
        """
        Get basic information about a file and prepare it for downloading.

        :param int file_id: File identifier to get information about
        :return: File object (see https://core.telegram.org/bots/api#file)
        """
        json = await self.api_call("getFile", file_id=file_id)
        return json["result"]

    def download_file(self, file_path, range=None):
        """
        Download a file from Telegram servers
        """
        headers = {"range": range} if range else None
        url = "{0}/file/bot{1}/{2}".format(API_URL, self.api_token, file_path)
        return self.session.get(url, headers=headers)

    _get_user_profile_photos = partialmethod(api_call, "getUserProfilePhotos")

    def get_user_profile_photos(self, user_id, **options):
        """
        Get a list of profile pictures for a user

        :param int user_id: Unique identifier of the target user
        :param options: Additional getUserProfilePhotos options (see
            https://core.telegram.org/bots/api#getuserprofilephotos)
        """
        return self._get_user_profile_photos(
            user_id=str(user_id),
            **options
        )

    def track(self, message, name="Message"):
        """
        Track message using http://botan.io
        Set botan_token to make it work
        """
        if self.botan_token:
            asyncio.ensure_future(self._track(message, name))

    def stop(self):
        self._running = False

    async def webhook_handle(self, request):
        """
        aiohttp.web handle for processing web hooks

        :Example:

        >>> from aiohttp import web
        >>> app = web.Application()
        >>> app.router.add_route('/webhook')
        """
        update = await request.json()
        self._process_update(update)
        return web.Response()

    def create_webhook_app(self, path, loop=None):
        """
        Shorthand for creating aiohttp.web.Application with registered webhook hanlde
        """
        app = web.Application(loop=loop)
        app.router.add_route('POST', path, self.webhook_handle)
        return app

    def set_webhook(self, webhook_url, **options):
        """
        Register you webhook url for Telegram service.
        """
        return self.api_call(
            'setWebhook',
            url=webhook_url,
            **options
        )

    @property
    def session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    def __del__(self):
        try:
            if self._session:
                self._session.close()
        except:
            # 😶
            pass

    async def _track(self, message, name):
        response = await self.session.post(
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
        await response.release()

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
            self._process_update(update)

    def _process_update(self, update):
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
            asyncio.ensure_future(coro)


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

    def answer(self, **options):
        return self.bot.api_call(
            "answerCallbackQuery",
            callback_query_id=self.query_id,
            **options
        )
