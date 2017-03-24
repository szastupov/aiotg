import os
import aiohttp
from aiotg import Bot

bot = Bot(os.environ["API_TOKEN"])


@bot.command(r"bitcoin")
async def bitcoin(chat, match):
    url = "https://api.bitcoinaverage.com/ticker/global/USD/"
    async with aiohttp.get(url) as s:
        info = await s.json()
        await chat.send_text(info["24h_avg"])

if __name__ == '__main__':
    bot.run(debug=True)
