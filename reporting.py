import aiohttp
from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID
from trading import TradingBot

async def send_report(bot: TradingBot, chat_id):
    """Send a report of buys and PnL via Telegram to admin only."""
    if str(chat_id) != ADMIN_USER_ID:
        return  # Only send reports to admin

    message = "30-Day Trading Report\n\n"
    message += "Buys Completed:\n"

    total_pnl = 0
    for record in bot.buy_records:
        token_address = record["token_address"]
        buy_amount = record["amount"]
        tx_id = record["tx_id"]

        # Fetch current token price
        current_price = await fetch_token_price(token_address)
        buy_price = buy_amount  # Simplify: Assume buy price in SOL
        pnl = (current_price - buy_price) if current_price else 0

        message += f"Token: {token_address}\n"
        message += f"Buy Amount: {buy_amount} SOL\n"
        message += f"Tx ID: {tx_id}\n"
        message += f"PnL: {pnl:.4f} SOL\n\n"
        total_pnl += pnl

    message += f"Total PnL: {total_pnl:.4f} SOL\n"

    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                print("Report sent successfully.")
            else:
                print(f"Failed to send report: {await response.text()}")

async def fetch_token_price(token_address):
    """Fetch current token price from DexScreener."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}") as response:
                data = await response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    return float(pairs[0].get("priceUsd", 0))
                return None
    except Exception as e:
        print(f"Error fetching price for {token_address}: {e}")
        return None