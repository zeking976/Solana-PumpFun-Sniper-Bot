import asyncio
import aiohttp
import time
import json
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ADMIN_USER_ID, RPC_ENDPOINT, PUMP_FUN_PROGRAM_ID
from filters import validate_token

async def monitor_new_tokens(callback, chat_id=TELEGRAM_CHAT_ID):
    """Monitor new tokens on Pump.fun via WebSocket and notify via Telegram."""
    async with AsyncClient(RPC_ENDPOINT) as client:
        # Subscribe to Pump.fun program logs
        program_id = Pubkey.from_string(PUMP_FUN_PROGRAM_ID)
        async for response in client.logs_subscribe(
            program_id=program_id,
            commitment=Confirmed
        ):
            # Parse logs for new token creation
            for log in response.value.logs:
                if "initialize" in log.lower():  # Detect token creation
                    token_address = await extract_token_address(log)
                    if token_address and await validate_token(token_address, client):
                        await callback(token_address, chat_id)

async def extract_token_address(log):
    """Extract token mint address from Pump.fun logs (placeholder)."""
    # Placeholder: Parse logs or fetch from Pump.fun API
    # In production, extract mint from transaction signature or API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.pump.fun/tokens/latest") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("mint_address", None)
    except Exception as e:
        print(f"Error extracting token address: {e}")
    return None

async def fetch_token_info(token_address):
    """Fetch token info from DexScreener or Pump.fun."""
    try:
        async with aiohttp.ClientSession() as session:
            # Try DexScreener
            async with session.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}") as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        pair = pairs[0]
                        return {
                            "name": pair["baseToken"]["name"],
                            "symbol": pair["baseToken"]["symbol"],
                            "contract_address": token_address,
                            "price": float(pair.get("priceUsd", 0.0001)),
                            "market_cap": float(pair.get("marketCap", 1000000)),
                            "volume": float(pair.get("volume", {}).get("h24", 50000)),
                            "liquidity": float(pair.get("liquidity", {}).get("usd", 200000)),
                            "chain": "Solana",
                            "listed_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(pair.get("pairCreatedAt", time.time() * 1000) / 1000)),
                            "image_url": pair.get("info", {}).get("imageUrl", None),
                            "dex_paid": pair.get("dexPaid", False)
                        }
            # Fallback to Pump.fun API (placeholder)
            async with session.get(f"https://api.pump.fun/tokens/{token_address}") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "name": data.get("name", "Unknown Token"),
                        "symbol": data.get("symbol", "UNKNOWN"),
                        "contract_address": token_address,
                        "price": float(data.get("price", 0.0001)),
                        "market_cap": float(data.get("market_cap", 1000000)),
                        "volume": float(data.get("volume", 50000)),
                        "liquidity": float(data.get("liquidity", 200000)),
                        "chain": "Solana",
                        "listed_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                        "image_url": data.get("image_url", None),
                        "dex_paid": data.get("dex_paid", False)
                    }
    except Exception as e:
        print(f"Error fetching token info for {token_address}: {e}")
    return {
        "name": "Sample Token",
        "symbol": "SMP",
        "contract_address": token_address,
        "price": 0.0001,
        "market_cap": 1000000,
        "volume": 50000,
        "liquidity": 200000,
        "chain": "Solana",
        "listed_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "image_url": None,
        "dex_paid": False
    }

async def is_dex_paid(token_address):
    """Check if token has completed Pump.fun bonding curve and listed on DEX."""
    try:
        async with AsyncClient(RPC_ENDPOINT) as client:
            # Check bonding curve account status
            program_id = Pubkey.from_string(PUMP_FUN_PROGRAM_ID)
            # Placeholder: Query bonding curve account
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.pump.fun/tokens/{token_address}/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("dex_paid", False)
    except Exception as e:
        print(f"Error checking DEX payment for {token_address}: {e}")
    return False

async def format_token_info(token_info):
    """Format token info for Telegram message."""
    return (
        f"Token: {token_info['name']} ({token_info['symbol']})\n"
        f"Contract Address: `{token_info['contract_address']}`\n"
        f"Price: ${token_info['price']:.8f}\n"
        f"Market Cap: ${token_info['market_cap']:,.2f}\n"
        f"Volume: ${token_info['volume']:,.2f}\n"
        f"Liquidity: ${token_info['liquidity']:,.2f}\n"
        f"Chain: {token_info['chain']}\n"
        f"Listed: {token_info['listed_time']}"
    )

async def send_token_notification(token_address, chat_id):
    """Send Telegram notification for a new token."""
    async with aiohttp.ClientSession() as session:
        token_info = await fetch_token_info(token_address)
        text = await format_token_info(token_info)
        ca_text = f"CA📃: `{token_info['contract_address']}`"
        report_text = f"{text}\n\n{ca_text}\n\nOther users can send /start to get reports of new tokens and other functions!"

        # Check DEX payment status
        if await is_dex_paid(token_address):
            market_cap = token_info["market_cap"]
            report_text += f"\n\n✅ DEX Paid! Market Cap: ${market_cap:,.2f}"

        # Inline buttons for multiplier reports
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "5x Report", "callback_data": f"report_5x_{token_address}"},
                    {"text": "10x Report", "callback_data": f"report_10x_{token_address}"},
                    {"text": "15x Report", "callback_data": f"report_15x_{token_address}"}
                ],
                [
                    {"text": "20x Report", "callback_data": f"report_20x_{token_address}"},
                    {"text": "30x Report", "callback_data": f"report_30x_{token_address}"},
                    {"text": "50x Report", "callback_data": f"report_50x_{token_address}"}
                ]
            ]
        }

        # Send initial token post
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                message_data = await response.json()
                message_id = message_data["result"]["message_id"]

                # Send report as reply with image (if available)
                report_payload = {
                    "chat_id": chat_id,
                    "text": report_text,
                    "parse_mode": "Markdown",
                    "reply_to_message_id": message_id,
                    "reply_markup": json.dumps(reply_markup)
                }
                if token_info["image_url"]:
                    photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                    photo_payload = {
                        "chat_id": chat_id,
                        "photo": token_info["image_url"],
                        "caption": report_text,
                        "parse_mode": "Markdown",
                        "reply_to_message_id": message_id,
                        "reply_markup": json.dumps(reply_markup)
                    }
                    async with session.post(photo_url, json=photo_payload) as photo_response:
                        if photo_response.status == 200:
                            return
                async with session.post(url, json=report_payload) as report_response:
                    if report_response.status == 200:
                        return
            print(f"Failed to send notification: {await response.text()}")

async def handle_callback_query(query, chat_id):
    """Handle inline button callbacks for multiplier reports."""
    async with aiohttp.ClientSession() as session:
        data = query["data"]
        multiplier = data.split("_")[1]
        token_address = data.split("_")[2]

        token_info = await fetch_token_info(token_address)
        current_price = token_info["price"]
        target_price = current_price * float(multiplier.replace("x", ""))

        report_text = (
            f"{multiplier} Report for {token_info['name']} ({token_info['symbol']}):\n"
            f"Current Price: ${current_price:.8f}\n"
            f"Target {multiplier} Price: ${target_price:.8f}\n"
            f"Contract Address: `{token_info['contract_address']}`\n"
            f"Other users can send /start to get reports of new tokens and other functions!"
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": report_text,
            "parse_mode": "Markdown"
        }
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                print(f"Failed to send callback response: {await response.text()}")

async def handle_start_command(chat_id):
    """Handle /start command."""
    async with aiohttp.ClientSession() as session:
        message = (
            "Welcome to the Solana PumpFun Sniper Bot! 🚀\n"
            "Receive reports of new tokens and access various functions.\n"
            f"{'As the admin, you can also buy tokens through the bot.' if str(chat_id) == str(ADMIN_USER_ID) else 'Note: Token purchasing is available only to the admin.'}"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                print(f"Failed to send start message: {await response.text()}")

async def telegram_webhook():
    """Handle Telegram webhook updates."""
    async with aiohttp.ClientSession() as session:
        # Set webhook (optional)
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
            payload = {"url": webhook_url}
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to set webhook: {await response.text()}")

        # Polling for updates
        offset = None
        while True:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 30}
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    updates = await response.json()
                    for update in updates.get("result", []):
                        offset = update["update_id"] + 1
                        if "message" in update and update["message"].get("text") == "/start":
                            chat_id = update["message"]["chat"]["id"]
                            await handle_start_command(chat_id)
                        elif "callback_query" in update:
                            chat_id = update["callback_query"]["message"]["chat"]["id"]
                            await handle_callback_query(update["callback_query"], chat_id)
            await asyncio.sleep(1)