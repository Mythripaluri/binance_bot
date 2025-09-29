import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from decimal import Decimal
import json
from ..utils.logger import get_logger
from ..binance_client import get_client

logger = get_logger()

@dataclass
class PaperOrder:
    id: Optional[int]
    symbol: str
    side: str  # BUY/SELL
    order_type: str  # MARKET/LIMIT/STOP/etc
    quantity: float
    price: Optional[float]  # None for market orders
    stop_price: Optional[float]  # For stop orders
    status: str  # PENDING/FILLED/CANCELLED/EXPIRED
    created_at: datetime
    filled_at: Optional[datetime]
    filled_price: Optional[float]
    commission: float

@dataclass
class PaperPosition:
    symbol: str
    quantity: float  # Positive for long, negative for short
    avg_entry_price: float
    unrealized_pnl: float
    realized_pnl: float

@dataclass
class PaperAccount:
    balance: float
    margin_balance: float
    unrealized_pnl: float
    realized_pnl: float
    positions: List[PaperPosition]

class PaperTradingEngine:
    """Simulated trading engine for paper trading"""
    
    def __init__(self, initial_balance: float = 10000.0, db_path: str = "paper_trading.db"):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.db_path = db_path
        self.client = get_client()  # For market data
        self.order_counter = 0
        
        self.init_database()
        
        # Load existing data
        self.orders = self._load_orders()
        self.positions = self._load_positions()
        
        logger.info(f"Paper trading engine initialized with ${initial_balance}")
    
    def init_database(self):
        """Initialize paper trading database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL,
                    stop_price REAL,
                    status TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    filled_at DATETIME,
                    filled_price REAL,
                    commission REAL DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_positions (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL NOT NULL,
                    avg_entry_price REAL NOT NULL,
                    realized_pnl REAL DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_account_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    balance REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    total_trades INTEGER NOT NULL
                )
            """)
    
    def _load_orders(self) -> List[PaperOrder]:
        """Load orders from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM paper_orders ORDER BY created_at DESC LIMIT 1000")
            orders = []
            
            for row in cursor.fetchall():
                orders.append(PaperOrder(
                    id=row[0], symbol=row[1], side=row[2], order_type=row[3],
                    quantity=row[4], price=row[5], stop_price=row[6], status=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                    filled_at=datetime.fromisoformat(row[9]) if row[9] else None,
                    filled_price=row[10], commission=row[11]
                ))
            
            return orders
    
    def _load_positions(self) -> Dict[str, PaperPosition]:
        """Load positions from database"""
        positions = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM paper_positions")
            
            for row in cursor.fetchall():
                symbol = row[0]
                positions[symbol] = PaperPosition(
                    symbol=symbol,
                    quantity=row[1],
                    avg_entry_price=row[2],
                    unrealized_pnl=0,  # Will be calculated
                    realized_pnl=row[3]
                )
        
        return positions
    
    def _save_order(self, order: PaperOrder) -> Optional[int]:
        """Save order to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO paper_orders 
                (symbol, side, order_type, quantity, price, stop_price, status, 
                 created_at, filled_at, filled_price, commission)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.symbol, order.side, order.order_type, order.quantity,
                order.price, order.stop_price, order.status, order.created_at,
                order.filled_at, order.filled_price, order.commission
            ))
            
            order_id = cursor.lastrowid
            order.id = order_id
            return order_id
    
    def _update_order(self, order: PaperOrder):
        """Update order in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE paper_orders 
                SET status = ?, filled_at = ?, filled_price = ?, commission = ?
                WHERE id = ?
            """, (order.status, order.filled_at, order.filled_price, order.commission, order.id))
    
    def _save_position(self, position: PaperPosition):
        """Save position to database"""
        with sqlite3.connect(self.db_path) as conn:     
            conn.execute("""
                INSERT OR REPLACE INTO paper_positions 
                (symbol, quantity, avg_entry_price, realized_pnl)
                VALUES (?, ?, ?, ?)
            """, (position.symbol, position.quantity, position.avg_entry_price, position.realized_pnl))
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        try:
            ticker = self.client.ticker_price(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return 0.0
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   quantity: float, price: Optional[float] = None, 
                   stop_price: Optional[float] = None) -> Dict:
        """Place a paper order"""
        try:
            # Create order
            order = PaperOrder(
                id=None,
                symbol=symbol.upper(),
                side=side.upper(),
                order_type=order_type.upper(),
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                status="PENDING",
                created_at=datetime.now(),
                filled_at=None,
                filled_price=None,
                commission=0.0
            )
            
            # Save to database
            order_id = self._save_order(order)
            self.orders.append(order)
            
            # Try to fill immediately if market order
            if order_type.upper() == "MARKET":
                self._try_fill_order(order)
            
            logger.info(f"Paper order placed: {order.side} {order.quantity} {order.symbol} @ {order.price or 'MARKET'}")
            
            return {
                "orderId": order_id,
                "symbol": order.symbol,
                "side": order.side,
                "type": order.order_type,
                "quantity": str(order.quantity),
                "price": str(order.price) if order.price else None,
                "status": order.status,
                "timeInForce": "GTC",
                "created_at": order.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error placing paper order: {e}")
            return {"error": str(e)}
    
    def _try_fill_order(self, order: PaperOrder) -> bool:
        """Try to fill a paper order"""
        try:
            current_price = self.get_current_price(order.symbol)
            
            if current_price <= 0:
                return False
            
            should_fill = False
            fill_price = current_price
            
            if order.order_type == "MARKET":
                should_fill = True
                # Add small slippage for realism
                slippage = 0.001  # 0.1%
                if order.side == "BUY":
                    fill_price = current_price * (1 + slippage)
                else:
                    fill_price = current_price * (1 - slippage)
            
            elif order.order_type == "LIMIT" and order.price is not None:
                if order.side == "BUY" and current_price <= order.price:
                    should_fill = True
                    fill_price = order.price
                elif order.side == "SELL" and current_price >= order.price:
                    should_fill = True
                    fill_price = order.price
            
            elif order.order_type == "STOP" and order.stop_price:
                if order.side == "BUY" and current_price >= order.stop_price:
                    should_fill = True
                    fill_price = current_price
                elif order.side == "SELL" and current_price <= order.stop_price:
                    should_fill = True
                    fill_price = current_price
            
            if should_fill and fill_price is not None:
                # Calculate commission (0.04% for Binance futures)
                commission = order.quantity * fill_price * 0.0004
                
                # Check if we have enough balance
                if order.side == "BUY":
                    required_balance = order.quantity * fill_price + commission
                    if self.current_balance < required_balance:
                        logger.warning(f"Insufficient balance for order {order.id}")
                        return False
                
                # Fill the order
                order.status = "FILLED"
                order.filled_at = datetime.now()
                order.filled_price = fill_price
                order.commission = commission
                
                # Update position
                self._update_position(order)
                
                # Update database
                self._update_order(order)
                
                logger.info(f"Paper order filled: {order.id} at {fill_price}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error filling order {order.id}: {e}")
            return False
    
    def _update_position(self, filled_order: PaperOrder):
        """Update position after order fill"""
        symbol = filled_order.symbol
        quantity = filled_order.quantity
        price = filled_order.filled_price
        side = filled_order.side
        
        if price is None:
            logger.error("Cannot update position with None price")
            return
        
        if side == "SELL":
            quantity = -quantity
        
        if symbol not in self.positions:
            # New position
            self.positions[symbol] = PaperPosition(
                symbol=symbol,
                quantity=quantity,
                avg_entry_price=price,
                unrealized_pnl=0,
                realized_pnl=0
            )
        else:
            # Update existing position
            pos = self.positions[symbol]
            old_quantity = pos.quantity
            
            if (old_quantity > 0 and quantity > 0) or (old_quantity < 0 and quantity < 0):
                # Adding to position
                total_cost = (abs(old_quantity) * pos.avg_entry_price) + (abs(quantity) * price)
                new_quantity = old_quantity + quantity
                
                if new_quantity != 0:
                    pos.avg_entry_price = total_cost / abs(new_quantity)
                pos.quantity = new_quantity
            else:
                # Reducing or reversing position
                if abs(quantity) >= abs(old_quantity):
                    # Closing and potentially reversing
                    realized_pnl = old_quantity * (price - pos.avg_entry_price)
                    pos.realized_pnl += realized_pnl
                    
                    remaining_qty = quantity + old_quantity  # old_quantity will be opposite sign
                    if remaining_qty != 0:
                        pos.quantity = remaining_qty
                        pos.avg_entry_price = price
                    else:
                        pos.quantity = 0
                else:
                    # Partially closing
                    closed_qty = -quantity  # Opposite of quantity being closed
                    realized_pnl = closed_qty * (price - pos.avg_entry_price)
                    pos.realized_pnl += realized_pnl
                    pos.quantity = old_quantity + quantity
        
        # Save updated position
        self._save_position(self.positions[symbol])
        
        # Update balance
        if filled_order.side == "BUY":
            self.current_balance -= (filled_order.quantity * price + filled_order.commission)
        else:
            self.current_balance += (filled_order.quantity * price - filled_order.commission)
    
    def cancel_order(self, order_id: int) -> Dict:
        """Cancel a pending order"""
        try:
            for order in self.orders:
                if order.id == order_id and order.status == "PENDING":
                    order.status = "CANCELLED"
                    self._update_order(order)
                    logger.info(f"Paper order cancelled: {order_id}")
                    return {"orderId": order_id, "status": "CANCELLED"}
            
            return {"error": "Order not found or not cancellable"}
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return {"error": str(e)}
    
    def get_account_info(self) -> PaperAccount:
        """Get paper account information"""
        try:
            # Update unrealized P&L for all positions
            total_unrealized_pnl = 0
            total_realized_pnl = 0
            
            for symbol, position in self.positions.items():
                if position.quantity != 0:
                    current_price = self.get_current_price(symbol)
                    position.unrealized_pnl = position.quantity * (current_price - position.avg_entry_price)
                    total_unrealized_pnl += position.unrealized_pnl
                
                total_realized_pnl += position.realized_pnl
            
            margin_balance = self.current_balance + total_unrealized_pnl
            
            return PaperAccount(
                balance=self.current_balance,
                margin_balance=margin_balance,
                unrealized_pnl=total_unrealized_pnl,
                realized_pnl=total_realized_pnl,
                positions=[pos for pos in self.positions.values() if pos.quantity != 0]
            )
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return PaperAccount(self.current_balance, self.current_balance, 0, 0, [])
    
    def get_orders(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get order history"""
        filtered_orders = self.orders
        
        if symbol:
            filtered_orders = [order for order in self.orders if order.symbol == symbol.upper()]
        
        # Sort by creation time, most recent first
        filtered_orders = sorted(filtered_orders, key=lambda x: x.created_at, reverse=True)[:limit]
        
        return [
            {
                "orderId": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "type": order.order_type,
                "quantity": str(order.quantity),
                "price": str(order.price) if order.price else None,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "filled_price": order.filled_price,
                "commission": order.commission
            }
            for order in filtered_orders
        ]
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        positions_data = []
        
        for symbol, position in self.positions.items():
            if position.quantity != 0:
                current_price = self.get_current_price(symbol)
                position.unrealized_pnl = position.quantity * (current_price - position.avg_entry_price)
                
                positions_data.append({
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "avg_entry_price": position.avg_entry_price,
                    "current_price": current_price,
                    "unrealized_pnl": position.unrealized_pnl,
                    "realized_pnl": position.realized_pnl,
                    "pnl_percentage": (position.unrealized_pnl / (abs(position.quantity) * position.avg_entry_price) * 100) if position.avg_entry_price > 0 else 0
                })
        
        return positions_data
    
    def check_pending_orders(self):
        """Check and potentially fill pending orders"""
        pending_orders = [order for order in self.orders if order.status == "PENDING"]
        
        filled_count = 0
        for order in pending_orders:
            if self._try_fill_order(order):
                filled_count += 1
        
        if filled_count > 0:
            logger.info(f"Filled {filled_count} pending paper orders")
    
    def reset_account(self, new_balance: Optional[float] = None):
        """Reset paper trading account"""
        if new_balance is None:
            new_balance = self.initial_balance
        
        # Clear database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM paper_orders")
            conn.execute("DELETE FROM paper_positions")
            conn.execute("DELETE FROM paper_account_history")
        
        # Reset state
        self.current_balance = new_balance
        self.orders = []
        self.positions = {}
        
        logger.info(f"Paper trading account reset with ${new_balance}")
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        account = self.get_account_info()
        
        total_pnl = account.realized_pnl + account.unrealized_pnl
        total_return_pct = (total_pnl / self.initial_balance) * 100
        
        # Count trades
        filled_orders = [order for order in self.orders if order.status == "FILLED"]
        total_trades = len(filled_orders)
        
        # Calculate win rate
        winning_trades = 0
        total_commission = 0
        
        for order in filled_orders:
            total_commission += order.commission
            
            # This is simplified - you'd need more sophisticated P&L tracking per trade
            if order.side == "SELL":  # Assuming selling is closing a position
                # Would need to match with corresponding buy order for accurate win/loss
                pass
        
        return {
            "initial_balance": self.initial_balance,
            "current_balance": account.balance,
            "margin_balance": account.margin_balance,
            "total_pnl": total_pnl,
            "realized_pnl": account.realized_pnl,
            "unrealized_pnl": account.unrealized_pnl,
            "total_return_percentage": total_return_pct,
            "total_trades": total_trades,
            "total_commission_paid": total_commission,
            "active_positions": len(account.positions),
            "win_rate": 0,  # Would need more complex calculation
            "max_drawdown": 0,  # Would need historical balance tracking
        }