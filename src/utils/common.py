from decimal import Decimal

def round_step(value: float, step: float) -> float:
    d = Decimal(str(value))
    s = Decimal(str(step))
    return float((d // s) * s)

def side_to_binance(side: str) -> str:
    s = side.upper()
    if s not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    return s
