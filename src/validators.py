from pydantic import BaseModel, Field, field_validator
from typing import Literal

class OrderBase(BaseModel):
    symbol: str = Field(..., description="Symbol, e.g., BTCUSDT")
    side: Literal["BUY", "SELL"]
    qty: float = Field(..., gt=0)

class LimitOrder(OrderBase):
    price: float = Field(..., gt=0)

class StopLimitOrder(OrderBase):
    price: float = Field(..., gt=0)
    stop: float = Field(..., gt=0)

class OCOOrder(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: float = Field(..., gt=0)
    tp: float = Field(..., gt=0)
    sl: float = Field(..., gt=0)

class TWAPParams(OrderBase):
    slices: int = Field(..., gt=0)
    duration: int = Field(..., gt=0)

class GridParams(BaseModel):
    symbol: str
    qty: float = Field(..., gt=0)
    lower: float = Field(..., gt=0)
    upper: float = Field(..., gt=0)
    levels: int = Field(..., gt=1)

    @field_validator("upper")
    @classmethod
    def upper_gt_lower(cls, v, info):
        if "lower" in info.data and v <= info.data["lower"]:
            raise ValueError("upper must be > lower")
        return v
