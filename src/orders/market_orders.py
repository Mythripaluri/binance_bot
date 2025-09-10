from .shared import ensure_symbol_precision, ensure_position_mode
from ..utils.logger import get_logger
from ..validators import OrderBase
from ..binance_client import get_client
from ..utils.common import side_to_binance

logger = get_logger()

def place_market_order(data: OrderBase):
    client = get_client()
    ensure_position_mode(client)
    symbol, qty, side = data.symbol.upper(), data.qty, side_to_binance(data.side)
    qty = ensure_symbol_precision(client, symbol, qty)

    logger.info(f"Placing MARKET {side} {symbol} qty={qty}")
    resp = client.new_order(symbol=symbol, side=side, type="MARKET", quantity=str(qty))
    logger.info(f"Response: {resp}")
    return resp
