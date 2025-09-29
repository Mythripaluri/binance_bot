import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from ..utils.logger import get_logger

logger = get_logger()

@dataclass
class Trade:
    id: Optional[int]
    symbol: str
    side: str
    quantity: float
    price: float
    commission: float
    timestamp: datetime
    order_id: str
    strategy: str = "manual"

@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float
    realized_pnl: float
    last_price: float

class TradeDatabase:
    def __init__(self, db_path: str = "bot_trades.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    commission REAL DEFAULT 0,
                    timestamp DATETIME NOT NULL,
                    order_id TEXT UNIQUE,
                    strategy TEXT DEFAULT 'manual'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    total_balance REAL,
                    unrealized_pnl REAL,
                    realized_pnl REAL,
                    positions_count INTEGER
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
                CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
            """)
            
        logger.info(f"Database initialized at {self.db_path}")
    
    def add_trade(self, trade: Trade) -> int:
        """Add a new trade to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO trades (symbol, side, quantity, price, commission, timestamp, order_id, strategy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (trade.symbol, trade.side, trade.quantity, trade.price, 
                  trade.commission, trade.timestamp, trade.order_id, trade.strategy))
            
            trade_id = cursor.lastrowid
            logger.info(f"Added trade {trade_id}: {trade.side} {trade.quantity} {trade.symbol} @ {trade.price}")
            return trade_id
    
    def get_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Trade]:
        """Get trades from database"""
        with sqlite3.connect(self.db_path) as conn:
            if symbol:
                cursor = conn.execute("""
                    SELECT * FROM trades WHERE symbol = ? 
                    ORDER BY timestamp DESC LIMIT ?
                """, (symbol, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
            
            trades = []
            for row in cursor.fetchall():
                trades.append(Trade(
                    id=row[0], symbol=row[1], side=row[2], quantity=row[3],
                    price=row[4], commission=row[5], timestamp=datetime.fromisoformat(row[6]),
                    order_id=row[7], strategy=row[8]
                ))
            
            return trades
    
    def get_position_summary(self, symbol: str) -> Dict:
        """Get position summary for a symbol"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) as net_quantity,
                    SUM(CASE WHEN side = 'BUY' THEN quantity * price ELSE -quantity * price END) as net_cost,
                    COUNT(*) as trade_count,
                    MIN(timestamp) as first_trade,
                    MAX(timestamp) as last_trade
                FROM trades WHERE symbol = ?
            """, (symbol,))
            
            result = cursor.fetchone()
            if result and result[0]:
                net_qty = result[0]
                net_cost = result[1]
                avg_price = abs(net_cost / net_qty) if net_qty != 0 else 0
                
                return {
                    "symbol": symbol,
                    "net_quantity": net_qty,
                    "avg_price": avg_price,
                    "total_cost": net_cost,
                    "trade_count": result[2],
                    "first_trade": result[3],
                    "last_trade": result[4]
                }
            
            return {"symbol": symbol, "net_quantity": 0, "avg_price": 0, 
                    "total_cost": 0, "trade_count": 0}
    
    def save_portfolio_snapshot(self, balance: float, unrealized_pnl: float, 
                               realized_pnl: float, positions_count: int):
        """Save portfolio snapshot for tracking"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO portfolio_snapshots 
                (timestamp, total_balance, unrealized_pnl, realized_pnl, positions_count)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now(), balance, unrealized_pnl, realized_pnl, positions_count))