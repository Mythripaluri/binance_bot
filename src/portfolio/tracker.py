from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
from ..binance_client import get_client
from ..utils.logger import get_logger
from .database import TradeDatabase, Position, Trade

logger = get_logger()

class PortfolioTracker:
    def __init__(self):
        self.db = TradeDatabase()
        self.client = get_client()
    
    def record_trade_from_order(self, order_response: Dict, strategy: str = "manual"):
        """Record a trade from Binance order response"""
        try:
            # Extract trade information from order response
            symbol = order_response.get('symbol', '')
            side = order_response.get('side', '')
            
            if not symbol or not side:
                logger.error("Missing symbol or side in order response")
                return None
            
            # Handle different order response formats
            if 'fills' in order_response:
                # Market order with fills
                total_qty = 0
                total_cost = 0
                total_commission = 0
                
                for fill in order_response['fills']:
                    qty = float(fill['qty'])
                    price = float(fill['price'])
                    commission = float(fill['commission'])
                    
                    total_qty += qty
                    total_cost += qty * price
                    total_commission += commission
                
                avg_price = total_cost / total_qty if total_qty > 0 else 0
                
                trade = Trade(
                    id=None,
                    symbol=symbol,
                    side=side,
                    quantity=total_qty,
                    price=avg_price,
                    commission=total_commission,
                    timestamp=datetime.now(),
                    order_id=str(order_response.get('orderId', '')),
                    strategy=strategy
                )
            else:
                # Limit order or other types
                trade = Trade(
                    id=None,
                    symbol=symbol,
                    side=side,
                    quantity=float(order_response.get('origQty', 0)),
                    price=float(order_response.get('price', 0)),
                    commission=0,  # Will be updated when filled
                    timestamp=datetime.now(),
                    order_id=str(order_response.get('orderId', '')),
                    strategy=strategy
                )
            
            trade_id = self.db.add_trade(trade)
            logger.info(f"Recorded trade {trade_id} for {symbol}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            return None
    
    def get_current_positions(self) -> List[Position]:
        """Get current positions with live P&L calculation"""
        try:
            # Get account positions from Binance
            account_info = self.client.account()
            positions = []
            
            for position in account_info.get('positions', []):
                symbol = position['symbol']
                position_amt = float(position['positionAmt'])
                
                if abs(position_amt) > 0:  # Only include non-zero positions
                    entry_price = float(position['entryPrice'])
                    mark_price = float(position['markPrice'])
                    unrealized_pnl = float(position['unRealizedProfit'])
                    
                    # Get realized P&L from database
                    db_position = self.db.get_position_summary(symbol)
                    
                    pos = Position(
                        symbol=symbol,
                        quantity=position_amt,
                        avg_price=entry_price,
                        unrealized_pnl=unrealized_pnl,
                        realized_pnl=0,  # Calculate from trades if needed
                        last_price=mark_price
                    )
                    positions.append(pos)
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        try:
            account = self.client.account()
            positions = self.get_current_positions()
            
            total_wallet_balance = float(account.get('totalWalletBalance', 0))
            total_unrealized_pnl = float(account.get('totalUnrealizedProfit', 0))
            total_margin_balance = float(account.get('totalMarginBalance', 0))
            available_balance = float(account.get('availableBalance', 0))
            
            # Calculate realized P&L from recent trades
            recent_trades = self.db.get_trades(limit=1000)
            total_fees = sum(trade.commission for trade in recent_trades)
            
            portfolio = {
                "timestamp": datetime.now(),
                "total_wallet_balance": total_wallet_balance,
                "available_balance": available_balance,
                "total_margin_balance": total_margin_balance,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_fees_paid": total_fees,
                "positions_count": len(positions),
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "quantity": pos.quantity,
                        "avg_price": pos.avg_price,
                        "current_price": pos.last_price,
                        "unrealized_pnl": pos.unrealized_pnl,
                        "pnl_percentage": (pos.unrealized_pnl / (abs(pos.quantity) * pos.avg_price) * 100) if pos.avg_price > 0 else 0
                    }
                    for pos in positions
                ],
                "performance": {
                    "total_pnl": total_unrealized_pnl,
                    "pnl_percentage": (total_unrealized_pnl / total_wallet_balance * 100) if total_wallet_balance > 0 else 0,
                    "largest_position": max(positions, key=lambda x: abs(x.quantity * x.avg_price)) if positions else None
                }
            }
            
            # Save snapshot to database
            self.db.save_portfolio_snapshot(
                total_wallet_balance, 
                total_unrealized_pnl, 
                0,  # realized P&L calculation
                len(positions)
            )
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {}
    
    def get_trade_history(self, symbol: Optional[str] = None, days: int = 30) -> List[Dict]:
        """Get formatted trade history"""
        trades = self.db.get_trades(symbol=symbol, limit=1000)
        
        formatted_trades = []
        for trade in trades:
            # Skip trades older than specified days
            if (datetime.now() - trade.timestamp).days > days:
                continue
                
            formatted_trades.append({
                "date": trade.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "value": trade.quantity * trade.price,
                "commission": trade.commission,
                "strategy": trade.strategy,
                "order_id": trade.order_id
            })
        
        return formatted_trades
    
    def calculate_daily_pnl(self, days: int = 7) -> List[Dict]:
        """Calculate daily P&L for the last N days"""
        # This would require more sophisticated tracking
        # For now, return a placeholder structure
        daily_pnl = []
        
        try:
            # Get portfolio snapshots from database - implement when needed
            pass  # Implement daily P&L calculation from portfolio_snapshots table
                
        except Exception as e:
            logger.error(f"Error calculating daily P&L: {e}")
        
        return daily_pnl