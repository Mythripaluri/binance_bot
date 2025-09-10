from .shared import ensure_symbol_precision, ensure_price_precision, ensure_position_mode
from ..utils.logger import get_logger
from ..validators import StopLimitOrder
from ..binance_client import get_client
from ..utils.common import side_to_binance

logger = get_logger()

def place_stop_limit(data: StopLimitOrder, tif: str = "GTC"):
    client = get_client()
    ensure_position_mode(client)
    symbol, side = data.symbol.upper(), side_to_binance(data.side)
    qty = ensure_symbol_precision(client, symbol, data.qty)
    price = ensure_price_precision(client, symbol, data.price)
    stop = ensure_price_precision(client, symbol, data.stop)

    logger.info(f"Placing STOP_LIMIT {side} {symbol} qty={qty} stop={stop} price={price}")
    resp = client.new_order(symbol=symbol, side=side, type="STOP",
                            timeInForce=tif, price=str(price), stopPrice=str(stop), quantity=str(qty))
    logger.info(f"Response: {resp}")
    return resp
