from .shared import ensure_symbol_precision, ensure_price_precision, ensure_position_mode
from ..utils.logger import get_logger
from ..validators import LimitOrder
from ..binance_client import get_client
from ..utils.common import side_to_binance

logger = get_logger()

def place_limit_order(data: LimitOrder, tif: str = "GTC"):
    client = get_client()
    ensure_position_mode(client)
    symbol, side = data.symbol.upper(), side_to_binance(data.side)
    qty = ensure_symbol_precision(client, symbol, data.qty)
    price = ensure_price_precision(client, symbol, data.price)

    logger.info(f"Placing LIMIT {side} {symbol} qty={qty} price={price}")
    resp = client.new_order(symbol=symbol, side=side, type="LIMIT",
                            timeInForce=tif, price=str(price), quantity=str(qty))
    logger.info(f"Response: {resp}")
    return resp
