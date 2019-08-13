import os
import asyncio
from aiotg import Bot

bot = Bot(api_token="API_TOKEN")
channel = bot.channel(os.environ["CHANNEL"])
private = bot.private(os.environ["PRIVATE"])


async def greeter():
    await channel.send_text("Hello from channel!")
    await private.send_text("Why not say hello directly?")


loop = asyncio.get_event_loop()
loop.run_until_complete(greeter())
