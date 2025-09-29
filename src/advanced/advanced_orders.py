from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from ..utils.logger import get_logger
from ..binance_client import get_client
from ..orders.shared import ensure_symbol_precision, ensure_price_precision, ensure_position_mode
from ..utils.common import side_to_binance

logger = get_logger()

class IcebergOrder(BaseModel):
    symbol: str = Field(..., description="Symbol, e.g., BTCUSDT")
    side: str = Field(..., pattern="^(BUY|SELL)$")
    total_qty: float = Field(..., gt=0)
    visible_qty: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    
    def model_post_init(self, __context):
        if self.visible_qty > self.total_qty:
            raise ValueError("Visible quantity cannot exceed total quantity")

class PostOnlyOrder(BaseModel):
    symbol: str = Field(..., description="Symbol, e.g., BTCUSDT")
    side: str = Field(..., pattern="^(BUY|SELL)$")
    qty: float = Field(..., gt=0)
    price: float = Field(..., gt=0)

class ReduceOnlyOrder(BaseModel):
    symbol: str = Field(..., description="Symbol, e.g., BTCUSDT")
    side: str = Field(..., pattern="^(BUY|SELL)$")
    qty: float = Field(..., gt=0)
    price: Optional[float] = None  # None for market orders

def place_iceberg_order(data: IcebergOrder, time_in_force: str = "GTC") -> List[Dict]:
    """
    Place an iceberg order by breaking it into smaller visible chunks
    """
    client = get_client()
    ensure_position_mode(client)
    
    symbol = data.symbol.upper()
    side = side_to_binance(data.side)
    total_qty = ensure_symbol_precision(client, symbol, data.total_qty)
    visible_qty = ensure_symbol_precision(client, symbol, data.visible_qty)
    price = ensure_price_precision(client, symbol, data.price)
    
    logger.info(f"Placing ICEBERG order: {side} {symbol} total={total_qty}, visible={visible_qty}, price={price}")
    
    orders = []
    remaining_qty = total_qty
    
    try:
        while remaining_qty > 0:
            current_qty = min(remaining_qty, visible_qty)
            current_qty = ensure_symbol_precision(client, symbol, current_qty)
            
            logger.info(f"Placing iceberg slice: {current_qty} of {remaining_qty} remaining")
            
            order = client.new_order(
                symbol=symbol,
                side=side,
                type="LIMIT",
                timeInForce=time_in_force,
                quantity=str(current_qty),
                price=str(price)
            )
            
            orders.append(order)
            remaining_qty -= current_qty
            
            # In a real implementation, you'd wait for the order to fill
            # before placing the next slice. This is a simplified version.
            logger.info(f"Iceberg slice placed: {order.get('orderId')}")
        
        logger.info(f"Iceberg order completed: {len(orders)} slices placed")
        return orders
        
    except Exception as e:
        logger.error(f"Error placing iceberg order: {e}")
        # Cancel any placed orders if there's an error
        for order in orders:
            try:
                client.cancel_order(symbol=symbol, orderId=order.get('orderId'))
                logger.info(f"Cancelled order {order.get('orderId')} due to error")
            except:
                pass
        raise e

def place_post_only_order(data: PostOnlyOrder) -> Dict:
    """
    Place a post-only order that will only be placed if it doesn't immediately match
    """
    client = get_client()
    ensure_position_mode(client)
    
    symbol = data.symbol.upper()
    side = side_to_binance(data.side)
    qty = ensure_symbol_precision(client, symbol, data.qty)
    price = ensure_price_precision(client, symbol, data.price)
    
    logger.info(f"Placing POST-ONLY {side} {symbol} qty={qty} price={price}")
    
    try:
        # Check current market price to ensure the order is post-only
        ticker = client.ticker_price(symbol=symbol)
        current_price = float(ticker['price'])
        
        # For buy orders, price must be below current market price
        # For sell orders, price must be above current market price
        if side == "BUY" and price >= current_price:
            raise ValueError(f"Post-only BUY order price ({price}) must be below market price ({current_price})")
        elif side == "SELL" and price <= current_price:
            raise ValueError(f"Post-only SELL order price ({price}) must be above market price ({current_price})")
        
        order = client.new_order(
            symbol=symbol,
            side=side,
            type="LIMIT",
            timeInForce="GTX",  # Good Till Crossing - will be rejected if it would immediately match
            quantity=str(qty),
            price=str(price)
        )
        
        logger.info(f"Post-only order placed: {order.get('orderId')}")
        return order
        
    except Exception as e:
        logger.error(f"Error placing post-only order: {e}")
        raise e

def place_reduce_only_order(data: ReduceOnlyOrder) -> Dict:
    """
    Place a reduce-only order that can only reduce an existing position
    """
    client = get_client()
    ensure_position_mode(client)
    
    symbol = data.symbol.upper()
    side = side_to_binance(data.side)
    qty = ensure_symbol_precision(client, symbol, data.qty)
    
    logger.info(f"Placing REDUCE-ONLY {side} {symbol} qty={qty}")
    
    try:
        # Check current position
        positions = client.get_position_risk(symbol=symbol)
        current_position = None
        
        for pos in positions:
            if pos['symbol'] == symbol:
                current_position = float(pos['positionAmt'])
                break
        
        if current_position is None or current_position == 0:
            raise ValueError(f"No open position found for {symbol}")
        
        # Ensure the order would reduce the position
        if current_position > 0 and side == "BUY":
            raise ValueError("Cannot place BUY reduce-only order when position is LONG")
        elif current_position < 0 and side == "SELL":
            raise ValueError("Cannot place SELL reduce-only order when position is SHORT")
        
        # Ensure quantity doesn't exceed position size
        max_reduce_qty = abs(current_position)
        if qty > max_reduce_qty:
            logger.warning(f"Reduce quantity {qty} exceeds position size {max_reduce_qty}, adjusting...")
            qty = ensure_symbol_precision(client, symbol, max_reduce_qty)
        
        if data.price is None:
            # Market reduce-only order
            order = client.new_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=str(qty),
                reduceOnly=True
            )
        else:
            # Limit reduce-only order
            price = ensure_price_precision(client, symbol, data.price)
            order = client.new_order(
                symbol=symbol,
                side=side,
                type="LIMIT",
                timeInForce="GTC",
                quantity=str(qty),
                price=str(price),
                reduceOnly=True
            )
        
        logger.info(f"Reduce-only order placed: {order.get('orderId')}")
        return order
        
    except Exception as e:
        logger.error(f"Error placing reduce-only order: {e}")
        raise e

def place_trailing_stop_order(symbol: str, side: str, qty: float, callback_rate: float) -> Dict:
    """
    Place a trailing stop order
    """
    client = get_client()
    ensure_position_mode(client)
    
    symbol = symbol.upper()
    side = side_to_binance(side)
    qty = ensure_symbol_precision(client, symbol, qty)
    
    logger.info(f"Placing TRAILING-STOP {side} {symbol} qty={qty} callback_rate={callback_rate}%")
    
    try:
        order = client.new_order(
            symbol=symbol,
            side=side,
            type="TRAILING_STOP_MARKET",
            quantity=str(qty),
            callbackRate=str(callback_rate),  # Percentage
            reduceOnly=True  # Trailing stops are typically used to close positions
        )
        
        logger.info(f"Trailing stop order placed: {order.get('orderId')}")
        return order
        
    except Exception as e:
        logger.error(f"Error placing trailing stop order: {e}")
        raise e

def get_advanced_order_status(symbol: str, order_id: str) -> Dict:
    """
    Get detailed status of an advanced order
    """
    client = get_client()
    
    try:
        order = client.get_order(symbol=symbol.upper(), orderId=order_id)
        
        # Add interpretation of order status
        status_info = {
            "order_id": order.get('orderId'),
            "symbol": order.get('symbol'),
            "side": order.get('side'),
            "type": order.get('type'),
            "status": order.get('status'),
            "original_qty": order.get('origQty'),
            "executed_qty": order.get('executedQty'),
            "remaining_qty": float(order.get('origQty', 0)) - float(order.get('executedQty', 0)),
            "price": order.get('price'),
            "stop_price": order.get('stopPrice'),
            "time_in_force": order.get('timeInForce'),
            "reduce_only": order.get('reduceOnly'),
            "close_position": order.get('closePosition'),
            "created_time": order.get('time'),
            "updated_time": order.get('updateTime')
        }
        
        # Add human-readable status
        if order.get('status') == 'NEW':
            status_info['status_description'] = "Order is active and waiting to be filled"
        elif order.get('status') == 'PARTIALLY_FILLED':
            status_info['status_description'] = "Order is partially filled"
        elif order.get('status') == 'FILLED':
            status_info['status_description'] = "Order is completely filled"
        elif order.get('status') == 'CANCELED':
            status_info['status_description'] = "Order was cancelled"
        elif order.get('status') == 'REJECTED':
            status_info['status_description'] = "Order was rejected"
        elif order.get('status') == 'EXPIRED':
            status_info['status_description'] = "Order has expired"
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting order status for {symbol}:{order_id}: {e}")
        return {"error": str(e)}

def cancel_advanced_order(symbol: str, order_id: str) -> Dict:
    """
    Cancel an advanced order
    """
    client = get_client()
    
    try:
        result = client.cancel_order(symbol=symbol.upper(), orderId=order_id)
        logger.info(f"Cancelled order {order_id} for {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Error cancelling order {order_id} for {symbol}: {e}")
        raise e