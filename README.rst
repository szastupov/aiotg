aiotg
=====

Asynchronous Python API for building Telegram bots

This module is under heavy development, so the API is not stable yet,
but you are encouraged to play with it and report any issues and suggestions.

Install it with pip:

.. code:: sh

    pip install git+https://github.com/szastupov/aiotg.git@setup

Then you can create a new bot in few lines:

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
