from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from ..binance_client import get_client
from ..utils.logger import get_logger

logger = get_logger()

@dataclass
class RiskConfig:
    max_risk_per_trade: float = 0.02  # 2% max risk per trade
    max_portfolio_risk: float = 0.10  # 10% max total portfolio risk
    max_position_size: float = 0.25   # 25% max position size of portfolio
    stop_loss_percentage: float = 0.05  # 5% stop loss
    take_profit_ratio: float = 2.0    # 2:1 reward to risk ratio
    max_daily_loss: float = 0.05      # 5% max daily loss
    max_open_positions: int = 10      # Max number of open positions

class RiskManager:
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self.client = get_client()
    
    def get_account_balance(self) -> float:
        """Get current account balance"""
        try:
            account = self.client.account()
            return float(account.get('totalWalletBalance', 0))
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return 0.0
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              stop_loss_price: float, risk_amount: Optional[float] = None) -> Dict:
        """
        Calculate optimal position size based on risk management rules
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            risk_amount: Custom risk amount (if None, uses config percentage)
        
        Returns:
            Dict with position size, risk metrics, and recommendations
        """
        try:
            account_balance = self.get_account_balance()
            
            if account_balance <= 0:
                return {"error": "Invalid account balance"}
            
            # Calculate risk per trade
            if risk_amount is None:
                risk_amount = account_balance * self.config.max_risk_per_trade
            
            # Calculate risk per share/unit
            price_difference = abs(entry_price - stop_loss_price)
            risk_per_unit = price_difference
            
            if risk_per_unit <= 0:
                return {"error": "Invalid stop loss price"}
            
            # Base position size calculation
            base_position_size = risk_amount / risk_per_unit
            
            # Apply maximum position size constraint
            max_position_value = account_balance * self.config.max_position_size
            max_position_size = max_position_value / entry_price
            
            # Take the smaller of the two
            optimal_position_size = min(base_position_size, max_position_size)
            
            # Get symbol precision and adjust
            precision_adjusted_size = self._adjust_for_symbol_precision(symbol, optimal_position_size)
            
            position_value = precision_adjusted_size * entry_price
            actual_risk = precision_adjusted_size * risk_per_unit
            risk_percentage = (actual_risk / account_balance) * 100
            position_percentage = (position_value / account_balance) * 100
            
            return {
                "symbol": symbol,
                "position_size": precision_adjusted_size,
                "position_value": position_value,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": self._calculate_take_profit(entry_price, stop_loss_price),
                "risk_amount": actual_risk,
                "risk_percentage": risk_percentage,
                "position_percentage": position_percentage,
                "account_balance": account_balance,
                "is_valid": self._validate_position(risk_percentage, position_percentage),
                "warnings": self._generate_warnings(risk_percentage, position_percentage)
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {"error": str(e)}
    
    def _adjust_for_symbol_precision(self, symbol: str, quantity: float) -> float:
        """Adjust quantity for symbol precision requirements"""
        try:
            exchange_info = self.client.exchange_info()
            
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    for filter_info in symbol_info['filters']:
                        if filter_info['filterType'] == 'LOT_SIZE':
                            step_size = float(filter_info['stepSize'])
                            min_qty = float(filter_info['minQty'])
                            
                            # Adjust to step size
                            adjusted_qty = (quantity // step_size) * step_size
                            
                            # Ensure minimum quantity
                            adjusted_qty = max(adjusted_qty, min_qty)
                            
                            # Round to appropriate decimal places
                            decimal_places = len(str(step_size).split('.')[-1]) if '.' in str(step_size) else 0
                            return round(adjusted_qty, decimal_places)
            
            return quantity
            
        except Exception as e:
            logger.error(f"Error adjusting precision for {symbol}: {e}")
            return quantity
    
    def _calculate_take_profit(self, entry_price: float, stop_loss_price: float) -> float:
        """Calculate take profit price based on reward-to-risk ratio"""
        risk = abs(entry_price - stop_loss_price)
        reward = risk * self.config.take_profit_ratio
        
        if entry_price > stop_loss_price:  # Long position
            return entry_price + reward
        else:  # Short position
            return entry_price - reward
    
    def _validate_position(self, risk_percentage: float, position_percentage: float) -> bool:
        """Validate if position meets risk management criteria"""
        if risk_percentage > self.config.max_risk_per_trade * 100:
            return False
        if position_percentage > self.config.max_position_size * 100:
            return False
        return True
    
    def _generate_warnings(self, risk_percentage: float, position_percentage: float) -> list:
        """Generate risk warnings"""
        warnings = []
        
        if risk_percentage > self.config.max_risk_per_trade * 100:
            warnings.append(f"Risk percentage ({risk_percentage:.2f}%) exceeds maximum allowed ({self.config.max_risk_per_trade * 100}%)")
        
        if position_percentage > self.config.max_position_size * 100:
            warnings.append(f"Position size ({position_percentage:.2f}%) exceeds maximum allowed ({self.config.max_position_size * 100}%)")
        
        if risk_percentage > 5.0:
            warnings.append("High risk trade - consider reducing position size")
        
        if position_percentage > 20.0:
            warnings.append("Large position size - ensure adequate diversification")
        
        return warnings
    
    def check_portfolio_risk(self) -> Dict:
        """Check current portfolio risk metrics"""
        try:
            account = self.client.account()
            positions = account.get('positions', [])
            
            total_unrealized_pnl = float(account.get('totalUnrealizedProfit', 0))
            total_wallet_balance = float(account.get('totalWalletBalance', 0))
            
            open_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
            total_position_value = sum(abs(float(pos['positionAmt']) * float(pos['entryPrice'])) for pos in open_positions)
            
            portfolio_risk_percentage = abs(total_unrealized_pnl / total_wallet_balance * 100) if total_wallet_balance > 0 else 0
            portfolio_exposure = (total_position_value / total_wallet_balance * 100) if total_wallet_balance > 0 else 0
            
            risk_status = {
                "total_balance": total_wallet_balance,
                "unrealized_pnl": total_unrealized_pnl,
                "portfolio_risk_percentage": portfolio_risk_percentage,
                "portfolio_exposure": portfolio_exposure,
                "open_positions_count": len(open_positions),
                "max_positions_allowed": self.config.max_open_positions,
                "risk_status": self._assess_risk_level(portfolio_risk_percentage, portfolio_exposure, len(open_positions)),
                "recommendations": self._generate_risk_recommendations(portfolio_risk_percentage, portfolio_exposure, len(open_positions))
            }
            
            return risk_status
            
        except Exception as e:
            logger.error(f"Error checking portfolio risk: {e}")
            return {"error": str(e)}
    
    def _assess_risk_level(self, risk_pct: float, exposure_pct: float, position_count: int) -> str:
        """Assess overall portfolio risk level"""
        if risk_pct > self.config.max_portfolio_risk * 100 or exposure_pct > 80 or position_count > self.config.max_open_positions:
            return "HIGH"
        elif risk_pct > self.config.max_portfolio_risk * 50 or exposure_pct > 60 or position_count > self.config.max_open_positions * 0.8:
            return "MODERATE"
        else:
            return "LOW"
    
    def _generate_risk_recommendations(self, risk_pct: float, exposure_pct: float, position_count: int) -> list:
        """Generate risk management recommendations"""
        recommendations = []
        
        if risk_pct > self.config.max_portfolio_risk * 100:
            recommendations.append("Portfolio risk is too high - consider closing some positions")
        
        if exposure_pct > 80:
            recommendations.append("Portfolio exposure is high - avoid new large positions")
        
        if position_count > self.config.max_open_positions:
            recommendations.append(f"Too many open positions ({position_count}) - consider consolidating")
        
        if risk_pct < 2:
            recommendations.append("Low risk utilization - consider increasing position sizes if opportunities exist")
        
        return recommendations
    
    def should_allow_trade(self, symbol: str, side: str, quantity: float, price: float) -> Tuple[bool, str]:
        """
        Check if a trade should be allowed based on risk management rules
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        try:
            portfolio_risk = self.check_portfolio_risk()
            
            # Check if portfolio risk is too high
            if portfolio_risk.get('risk_status') == 'HIGH':
                return False, "Portfolio risk is too high for new trades"
            
            # Check position count
            if portfolio_risk.get('open_positions_count', 0) >= self.config.max_open_positions:
                return False, f"Maximum number of positions ({self.config.max_open_positions}) reached"
            
            # Check daily loss limit (would need daily P&L tracking)
            # This is a placeholder for daily loss check
            
            trade_value = quantity * price
            account_balance = portfolio_risk.get('total_balance', 0)
            
            if account_balance > 0:
                trade_percentage = (trade_value / account_balance) * 100
                if trade_percentage > self.config.max_position_size * 100:
                    return False, f"Trade size ({trade_percentage:.1f}%) exceeds maximum position size"
            
            return True, "Trade allowed"
            
        except Exception as e:
            logger.error(f"Error checking trade allowance: {e}")
            return False, f"Error in risk check: {str(e)}"