from ..utils.logger import get_logger
from ..validators import GridParams
from ..binance_client import get_client
from ..orders.shared import ensure_symbol_precision, ensure_price_precision, ensure_position_mode

logger = get_logger()

def run_grid(params: GridParams):
    client = get_client()
    ensure_position_mode(client)

    symbol = params.symbol.upper()
    lower, upper, levels = params.lower, params.upper, params.levels
    qty = ensure_symbol_precision(client, symbol, params.qty)

    step = (upper - lower) / levels
    orders = []
    for i in range(levels):
        buy_price = ensure_price_precision(client, symbol, lower + i * step)
        sell_price = ensure_price_precision(client, symbol, buy_price + step)

        buy = client.new_order(symbol=symbol, side="BUY", type="LIMIT",
                               timeInForce="GTC", price=str(buy_price), quantity=str(qty))
        sell = client.new_order(symbol=symbol, side="SELL", type="LIMIT",
                                timeInForce="GTC", price=str(sell_price), quantity=str(qty))
        orders.append({"buy": buy, "sell": sell})
    return orders
