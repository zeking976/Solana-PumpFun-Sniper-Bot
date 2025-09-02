import time
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solders.keypair import Keypair
from jupiter_python_sdk.jupiter import Jupiter
from config import PRIVATE_KEY, RPC_ENDPOINT, BUY_AMOUNT, TRANSACTION_FEE, NUM_BUYS, ADMIN_USER_ID
from filters import validate_token

class TradingBot:
    def __init__(self):
        self.client = AsyncClient(RPC_ENDPOINT)
        self.keypair = Keypair.from_base58_string(PRIVATE_KEY)
        self.jupiter = Jupiter(rpc_endpoint=RPC_ENDPOINT, private_key=PRIVATE_KEY)
        self.buys_completed = 0
        self.buy_records = []
        self.last_cycle_time = time.time()

    async def buy_token(self, token_address, user_id=None, platform="pumpfun"):
        """Execute a buy transaction for a token on Pump.fun or Raydium."""
        if user_id and str(user_id) != ADMIN_USER_ID:
            print("Only admin can buy tokens.")
            return False

        if self.buys_completed >= NUM_BUYS:
            print("Reached maximum buys for this cycle.")
            return False

        if not await validate_token(token_address, self.client, platform):
            print(f"Token {token_address} failed validation on {platform}.")
            return False

        try:
            # Calculate total cost
            total_cost = BUY_AMOUNT + TRANSACTION_FEE

            # Check wallet balance
            balance = await self.client.get_balance(self.keypair.pubkey())
            if balance.value / 1e9 < total_cost:
                print("Insufficient balance for buy.")
                return False

            # Execute swap via Jupiter for Raydium or Pump.fun
            swap_result = await self.jupiter.swap(
                input_mint="So11111111111111111111111111111111111111112",  # SOL
                output_mint=token_address,
                amount=int(BUY_AMOUNT * 1e9),  # SOL to lamports
                slippage_bps=100  # 1% slippage
            )

            # Sign and send transaction
            tx = Transaction().add(swap_result["transaction"])
            tx_resp = await self.client.send_transaction(tx, self.keypair)
            print(f"Buy executed for {token_address} on {platform}: {tx_resp.value}")

            # Record buy details
            self.buy_records.append({
                "token_address": token_address,
                "platform": platform,
                "amount": BUY_AMOUNT,
                "timestamp": time.time(),
                "tx_id": tx_resp.value
            })
            self.buys_completed += 1

            return True

        except Exception as e:
            print(f"Error executing buy for {token_address} on {platform}: {e}")
            return False

    async def check_cycle(self):
        """Check if 30 days have passed to reset buy cycle."""
        current_time = time.time()
        if (current_time - self.last_cycle_time) >= 30 * 24 * 60 * 60:
            self.buys_completed = 0
            self.last_cycle_time = current_time
            return True
        return False