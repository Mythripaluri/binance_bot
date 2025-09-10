from ..utils.logger import get_logger

logger = get_logger()

def _get_exchange_filters(client, symbol: str):
    info = client.exchange_info()
    for s in info["symbols"]:
        if s["symbol"] == symbol:
            return s["filters"]
    raise ValueError(f"Symbol {symbol} not found")

def ensure_symbol_precision(client, symbol: str, qty: float) -> float:
    filters = _get_exchange_filters(client, symbol)
    for f in filters:
        if f["filterType"] == "LOT_SIZE":
            step = float(f["stepSize"])
            min_qty = float(f["minQty"])
            qty = max(min_qty, (qty // step) * step)
            return float(f"{qty:.10f}".rstrip("0").rstrip("."))
    return qty

def ensure_price_precision(client, symbol: str, price: float) -> float:
    filters = _get_exchange_filters(client, symbol)
    for f in filters:
        if f["filterType"] == "PRICE_FILTER":
            tick = float(f["tickSize"])
            min_price = float(f["minPrice"])
            price = max(min_price, (price // tick) * tick)
            return float(f"{price:.10f}".rstrip("0").rstrip("."))
    return price

def ensure_position_mode(client):
    mode = client.get_position_mode()
    logger.info(f"Account position mode: {mode}")
