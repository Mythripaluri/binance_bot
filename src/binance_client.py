import os
from dotenv import load_dotenv
from binance.um_futures import UMFutures

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
USE_TESTNET = os.getenv("USE_TESTNET", "true").lower() == "true"

def get_client() -> UMFutures:
    base_url = "https://testnet.binancefuture.com" if USE_TESTNET else None
    return UMFutures(key=API_KEY, secret=API_SECRET, base_url=base_url)
