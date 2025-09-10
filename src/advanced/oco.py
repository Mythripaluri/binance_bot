from ..utils.logger import get_logger
from ..validators import OCOOrder
from ..binance_client import get_client
from ..orders.shared import ensure_symbol_precision, ensure_price_precision, ensure_position_mode
from ..utils.common import side_to_binance

logger = get_logger()

def place_oco(data: OCOOrder):
    client = get_client()
    ensure_position_mode(client)

    symbol, side = data.symbol.upper(), side_to_binance(data.side)
    qty = ensure_symbol_precision(client, symbol, data.qty)
    tp = ensure_price_precision(client, symbol, data.tp)
    sl = ensure_price_precision(client, symbol, data.sl)

    logger.info(f"Placing OCO {side} {symbol} qty={qty} tp={tp} sl={sl}")
    tp_order = client.new_order(symbol=symbol, side=side, type="TAKE_PROFIT",
                                timeInForce="GTC", price=str(tp), stopPrice=str(tp), quantity=str(qty))
    sl_order = client.new_order(symbol=symbol, side=side, type="STOP_MARKET",
                                stopPrice=str(sl), closePosition=False, quantity=str(qty))

    return {"tp": tp_order, "sl": sl_order}
