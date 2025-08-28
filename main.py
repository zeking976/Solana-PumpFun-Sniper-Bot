import asyncio
from trading import TradingBot
from reporting import send_report
from utils import monitor_new_tokens

async def main():
    bot = TradingBot()
    chat_id = "your_telegram_chat_id"  # Replace with your Telegram chat ID

    async def handle_new_token(token_address):
        if await bot.check_cycle():
            print("New 30-day cycle started.")
            bot.buy_records = []  # Reset records for new cycle
            await send_report(bot, chat_id)  # Send report for previous cycle

        if bot.buys_completed < bot.NUM_BUYS:
            await bot.buy_token(token_address)

    # Start monitoring for new tokens
    await monitor_new_tokens(handle_new_token)

if __name__ == "__main__":
    asyncio.run(main())