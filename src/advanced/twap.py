import time
from ..utils.logger import get_logger
from ..validators import TWAPParams
from ..binance_client import get_client
from ..orders.shared import ensure_symbol_precision, ensure_position_mode
from ..utils.common import side_to_binance

logger = get_logger()

def run_twap(params: TWAPParams):
    client = get_client()
    ensure_position_mode(client)

    symbol, side = params.symbol.upper(), side_to_binance(params.side)
    slices, duration = params.slices, params.duration
    slice_qty = params.qty / slices
    interval = max(1, duration // slices)

    results = []
    for i in range(slices):
        qty = ensure_symbol_precision(client, symbol, slice_qty)
        resp = client.new_order(symbol=symbol, side=side, type="MARKET", quantity=str(qty))
        results.append(resp)
        if i < slices - 1:
            time.sleep(interval)
    return results
