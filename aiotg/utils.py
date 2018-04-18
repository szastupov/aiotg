"""Utils functions.

"""

from functools import wraps
from inspect import getmembers, ismodule


def get_handlers(package):
    """Helper to split in module the handlers.

    Example:

    package
    | __init__.py
    >>> from . import file # call explicitly others are ignored

    | file.py
    >>> from aiotg.utils import handler
    >>> def other(): # does not have the decorator then it is ignored
    ...     pass
    >>> @handler(r'/game', action='command')
    ... def game(chat, match):
    ...     chat.sent_text('hello world')

    main.py
    >>> import package
    >>> from aiotg import Bot
    >>> from aiotg.utils import get_handlers
    >>> bot = Bot(api_token='...')
    >>> for handler in get_handlers(package):
    ...     handler(bot)
    >>> bot.run()

    """
    functions = []
    members = getmembers(package)

    for _, module in filter(lambda x: ismodule(x[1]), members):
        for _, function in getmembers(module):
            if hasattr(function, 'handler'):
                functions.append(function)

    return functions


def handler(regex, action='command'):
    """Decorator handler.

    """
    def _wrap(function):
        @wraps(function)
        def _handler(bot):
            return getattr(bot, 'add_' + action)(regex, function)

        _handler.handler = True
        return _handler

    return _wrap
