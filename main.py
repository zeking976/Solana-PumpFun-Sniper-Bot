import asyncio
import aiohttp
from trading import TradingBot
from reporting import send_report
from utils import monitor_new_tokens, telegram_webhook
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ADMIN_USER_ID

async def main():
    bot = TradingBot()
    chat_id = TELEGRAM_CHAT_ID

    async def handle_new_token(token_address, chat_id=chat_id, platform="pumpfun"):
        if await bot.check_cycle():
            print("New 30-day cycle started.")
            bot.buy_records = []
            await send_report(bot, chat_id)
        if bot.buys_completed < bot.NUM_BUYS:
            if await bot.buy_token(token_address, ADMIN_USER_ID, platform):
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": f"✅ Admin bought token {token_address} on {platform.capitalize()}!",
                        "parse_mode": "Markdown"
                    }
                    async with session.post(url, json=payload) as response:
                        if response.status != 200:
                            print(f"Failed to send buy confirmation: {await response.text()}")
        await send_token_notification(token_address, chat_id, platform)

    asyncio.create_task(telegram_webhook())
    await monitor_new_tokens(handle_new_token, chat_id)

if __name__ == "__main__":
    asyncio.run(main())