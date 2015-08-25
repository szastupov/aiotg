aiotg
=====

Asynchronous Python API for building Telegram bots

This module is under heavy development, so it's not on PyPI yet. The
current recommended way to use it is as GIT submodule:

.. code:: sh

    git submodule add https://github.com/szastupov/aiotg.git
    pip install -r ./aiotg/requirements.txt

You can create a new bot in a few lines:

.. code:: python

    import os
    from aiotg import TgBot

    bot = TgBot(os.environ["API_TOKEN"])

    @bot.command(r"/echo (.+)")
    def echo(message, match):
        return message.reply(match.group(1))

    if __name__ == '__main__':
        bot.run()

Run it with a proper API\_TOKEN and it should reply to /echo commands.

For a more complete example, take a look at
`WhatisBot <https://github.com/szastupov/whatisbot/blob/master/main.py>`__.
