import re

from aiotg.bot import Bot, API_TIMEOUT, MESSAGE_TYPES, logger, InlineQuery, \
    CallbackQuery
from aiotg.chat import Chat


class ExtendedBot(Bot):

    def __init__(self, api_token, api_timeout=API_TIMEOUT,
                 botan_token=None, name=None):
        """This is modifierd copy/paste from original Bot.__init__ it's fully
        overloads the parent method, however uses it in the same time.

        Telegram bot framework designed for asyncio
        :param str api_token: Telegram bot token, ask @BotFather for this
        :param int api_timeout: Timeout for long polling
        :param str botan_token: Token for http://botan.io
        :param str name: Bot name
        """

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
        self._callbacks = []
        self._inlines = []
        self._default = lambda chat, message: None
        self._default_callback = lambda chat, cq: None
        self._default_inline = lambda iq: None

    def _process_callback_query(self, query):
        chat = Chat.from_message(self, query["message"])
        cq = CallbackQuery(self, query)
        for patterns, handler in self._callbacks:
            match = re.search(patterns, cq.data, re.I)
            if match:
                return handler(chat, cq, match)

        if not chat.is_group():
            return self._default_callback(chat, cq)

    def add_callback(self, regexp, fn):
        """
        Manually register regexp based callback
        """
        self._callbacks.append((regexp, fn))

    def default_callback(self, callback):
        """
        Set default callback for unhandled callback queries
        :Example:
        >>> @bot.default_callback
        >>> def echo(chat, cq):
        >>>     return cq.answer()
        """
        self._default_callback = callback
        return callback

    def callback(self, regexp):

        """
        Register a new callback
        :param str regexp: Regular expression matching callback_data to
               register
        :Example:
        >>> @bot.callback(r"buttonclick-(.+)")
        >>> def echo(chat, cq, match):
        >>>     return chat.reply(match.group(1))
        """
        def decorator(fn):
            self.add_callback(regexp, fn)
            return fn
        return decorator

    def add_inline(self, regexp, fn):
        self._inlines.append((regexp, fn))

    def inline(self, regexp):
        """
        Register a new inline callback
        :param str regexp: Regular expression matching callback_data to
               register
        :Example:
        >>> @bot.inline(r"myinline-(.+)")
        >>> def echo(chat, iq, match):
        >>>     return iq.answer([
        >>>         {"type": "text", "title": "test", "id", "0"}
        >>>     ])
        """
        def decorator(fn):
            self.add_inline(regexp, fn)
            return fn
        return decorator

    def _process_inline_query(self, query):
        iq = InlineQuery(self, query)

        for patterns, handler in self._inlines:
            match = re.search(patterns, query['query'], re.I)
            if match:
                return handler(iq, match)

        return self._default_inline(iq)

    def default_inline(self, inline_callback):
        """
        Set default callback for unhandled inline queries
        :Example:
        >>> @bot.default_inline
        >>> def echo(iq):
        >>>     return iq.answer([
        >>>         {"type": "text", "title": "test", "id", "0"}
        >>>     ])
        """
        self._default_inline = inline_callback
        return inline_callback
