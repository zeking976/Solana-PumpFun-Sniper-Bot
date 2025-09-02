import aiohttp
import time
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TokenAccountOpts
from config import MIN_LIQUIDITY_USD, MAX_TOKEN_AGE_MINUTES, MAX_TOP_10_HOLDERS_PERCENT, PUMP_FUN_PROGRAM_ID

async def validate_token(token_address, client):
    """Validate a token based on specified filters."""
    try:
        # Check if token is in bonding phase
        if not await is_in_bonding_phase(token_address, client):
            print(f"Token {token_address} is not in bonding phase.")
            return False

        # Fetch token data from DexScreener
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}") as response:
                data = await response.json()
                pairs = data.get("pairs", [])
                if not pairs:
                    print(f"No trading pairs found for {token_address}.")
                    return False

                pair = pairs[0]
                liquidity_usd = pair.get("liquidity", {}).get("usd", 0)
                pair_created_at = pair.get("pairCreatedAt", 0)
                current_time = int(time.time() * 1000)
                age_minutes = (current_time - pair_created_at) / (1000 * 60)

                # Liquidity check
                if liquidity_usd < MIN_LIQUIDITY_USD:
                    print(f"Token {token_address} has low liquidity: ${liquidity_usd}")
                    return False

                # Token age check
                if age_minutes > MAX_TOKEN_AGE_MINUTES:
                    print(f"Token {token_address} is too old: {age_minutes} minutes")
                    return False

        # Check holder distribution
        if not await check_holder_distribution(token_address, client):
            print(f"Token {token_address} has concentrated holder distribution.")
            return False

        # Check for rug pull/honeypot risks using RugCheck
        if await is_rug_or_honeypot(token_address):
            print(f"Token {token_address} flagged as rug or honeypot.")
            return False

        # Check developer history
        if not await check_dev_history(token_address, client):
            print(f"Token {token_address} has no successful dev history.")
            return False

        # Check social sentiment and trending narrative
        if not await check_social_sentiment(token_address):
            print(f"Token {token_address} lacks trending narrative or social buzz.")
            return False

        return True

    except Exception as e:
        print(f"Error validating token {token_address}: {e}")
        return False

async def is_in_bonding_phase(token_address, client):
    """Check if token is in bonding phase by inspecting Pump.fun program accounts."""
    # Simplified check: Verify token is associated with Pump.fun bonding curve
    # In production, query the bonding curve account to confirm active status
    try:
        bonding_curve_account = await client.get_program_accounts(PUMP_FUN_PROGRAM_ID)
        # Placeholder logic: Assume bonding phase if token is newly created
        return True  # Replace with actual bonding curve check
    except Exception as e:
        print(f"Error checking bonding phase for {token_address}: {e}")
        return False

async def check_holder_distribution(token_address, client):
    """Check if top 10 holders own less than 50% of supply."""
    try:
        token_accounts = await client.get_token_accounts_by_owner(TokenAccountOpts(token_address))
        total_supply = await client.get_token_supply(token_address)
        total_supply_value = total_supply.value.ui_amount

        balances = [account.value.ui_amount for account in token_accounts.value]
        balances.sort(reverse=True)
        top_10_sum = sum(balances[:10]) if len(balances) >= 10 else sum(balances)
        top_10_percent = (top_10_sum / total_supply_value) * 100

        return top_10_percent <= MAX_TOP_10_HOLDERS_PERCENT
    except Exception as e:
        print(f"Error checking holder distribution for {token_address}: {e}")
        return False

async def is_rug_or_honeypot(token_address):
    """Check if token is a rug pull or honeypot using RugCheck API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report") as response:
                data = await response.json()
                risk_score = data.get("risk_score", 100)
                return risk_score > 20  # Adjust threshold based on testing
    except Exception as e:
        print(f"Error checking rug/honeypot for {token_address}: {e}")
        return False

async def check_dev_history(token_address, client):
    """Check if token's developer has a history of successful tokens."""
    # Placeholder: Query Solana blockchain for dev's previous tokens
    try:
        return True  # Replace with actual dev history check
    except Exception as e:
        print(f"Error checking dev history for {token_address}: {e}")
        return False

async def check_social_sentiment(token_address):
    """Check social media for trending narratives."""
    # Placeholder: Use Twitter/Discord APIs to check mentions and sentiment
    try:
        return True  # Replace with actual sentiment analysis
    except Exception as e:
        print(f"Error checking social sentiment for {token_address}: {e}")
        return False