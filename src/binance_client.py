import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
USE_TESTNET = os.getenv("USE_TESTNET", "true").lower() == "true"

def get_client() -> Client:
    return Client(API_KEY, API_SECRET, testnet=USE_TESTNET)
