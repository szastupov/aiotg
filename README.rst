aiotg
=====

.. image:: https://travis-ci.org/szastupov/aiotg.svg?branch=master
    :target: https://travis-ci.org/szastupov/aiotg

Asynchronous Python API for building Telegram bots, featuring:

- Easy and declarative API
- Hassle-free setup - no need for SSL certificates or static IP
- Built-in support for analytics via botan.io
- Automatic handling of Telegram API throttling or timeouts

Install it with pip:

.. code:: sh

    pip install aiotg

Then you can create a new bot in few lines:

.. code:: python

    from aiotg import Bot

    bot = Bot(api_token="...")

    @bot.command(r"/echo (.+)")
    def echo(chat, match):
        return chat.reply(match.group(1))

    bot.run()

Now run it with a proper API\_TOKEN and it should reply to /echo commands.

The example above looks like a normal synchronous code but it actually returns a coroutine.
If you want to make an external request (and that's what bots usually do) just use aiohttp and async/await syntax:

.. code:: python

    import aiohttp
    from aiotg import Bot

    bot = Bot(api_token="...")

    @bot.command("bitcoin")
    async def bitcoin(chat, match):
        url = "https://api.bitcoinaverage.com/ticker/global/USD/"
        async with aiohttp.get(url) as s:
            info = await s.json()
            await chat.send_text(info["24h_avg"])

    bot.run()

For a more complete example, take a look at
`WhatisBot <https://github.com/szastupov/whatisbot/blob/master/main.py>`__ or `Music Catalog Bot <https://github.com/szastupov/musicbot>`__.

Have a question? Ask it on project's `Telegram chat <https://telegram.me/joinchat/ABwEXjy3Tfmj2NAqEsQ1nw>`__.
