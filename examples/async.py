from aiotg import Bot, Chat

bot = Bot(api_token="API_TOKEN")


@bot.command(r"bitcoin")
async def bitcoin(chat: Chat, match):
    url = "https://api.bitcoinaverage.com/ticker/global/USD/"
    async with bot.session.get(url) as s:
        info = await s.json()
        await chat.send_text(info["24h_avg"])


if __name__ == "__main__":
    bot.run(debug=True)
