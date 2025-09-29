"""
Example usage scripts for the Advanced Binance Trading Bot

This file demonstrates how to use the various features of the enhanced trading bot.
These examples should be run in a testnet environment for safety.
"""

import asyncio
import time
from datetime import datetime, timedelta

# Import all the new modules
from src.portfolio.tracker import PortfolioTracker
from src.risk.manager import RiskManager, RiskConfig
from src.analysis.indicators import TechnicalIndicators
from src.simulation.paper_trading import PaperTradingEngine
from src.realtime.websocket_client import PriceMonitor, BinanceWebSocketClient
from src.notifications.manager import notification_manager, notify_trade, configure_notifications
from src.binance_client import get_client
from src.utils.logger import get_logger

logger = get_logger()

def example_portfolio_tracking():
    """Example: Track trades and analyze portfolio performance"""
    print("🔍 Portfolio Tracking Example")
    print("=" * 40)
    
    # Initialize portfolio tracker
    tracker = PortfolioTracker()
    
    # Get portfolio summary
    summary = tracker.get_portfolio_summary()
    print(f"Total Balance: ${summary.get('total_wallet_balance', 0):.2f}")
    print(f"Unrealized P&L: ${summary.get('total_unrealized_pnl', 0):.2f}")
    print(f"Active Positions: {summary.get('positions_count', 0)}")
    
    # Get trade history
    history = tracker.get_trade_history(days=7)
    print(f"\n📈 Recent Trades: {len(history)}")
    for trade in history[:5]:  # Show last 5 trades
        print(f"  {trade['date']}: {trade['side']} {trade['quantity']} {trade['symbol']} @ ${trade['price']}")

def example_risk_management():
    """Example: Calculate optimal position sizes and assess risk"""
    print("\n⚖️ Risk Management Example")
    print("=" * 40)
    
    # Initialize risk manager with custom config
    config = RiskConfig(
        max_risk_per_trade=0.015,  # 1.5% max risk per trade
        max_position_size=0.20,    # 20% max position size
        stop_loss_percentage=0.04   # 4% stop loss
    )
    risk_manager = RiskManager(config)
    
    # Calculate position size for a trade
    symbol = "BTCUSDT"
    entry_price = 44000
    stop_loss = 43000
    
    result = risk_manager.calculate_position_size(symbol, entry_price, stop_loss)
    
    if 'error' not in result:
        print(f"Symbol: {result['symbol']}")
        print(f"Recommended Position Size: {result['position_size']:.4f}")
        print(f"Position Value: ${result['position_value']:.2f}")
        print(f"Risk Amount: ${result['risk_amount']:.2f}")
        print(f"Risk Percentage: {result['risk_percentage']:.2f}%")
        
        warnings = result.get('warnings', [])
        if warnings:
            print("⚠️ Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
    
    # Check overall portfolio risk
    risk_status = risk_manager.check_portfolio_risk()
    print(f"\n📊 Portfolio Risk Status: {risk_status.get('risk_status', 'UNKNOWN')}")
    print(f"Portfolio Risk: {risk_status.get('portfolio_risk_percentage', 0):.2f}%")

def example_technical_analysis():
    """Example: Generate trading signals and perform market analysis"""
    print("\n📈 Technical Analysis Example")
    print("=" * 40)
    
    # Initialize technical indicators
    indicators = TechnicalIndicators()
    
    # Generate signals for BTCUSDT
    symbol = "BTCUSDT"
    signals = indicators.generate_signals(symbol, "1h")
    
    print(f"Technical Signals for {symbol}:")
    for signal in signals:
        print(f"  {signal.indicator}: {signal.signal} (Strength: {signal.strength:.2f})")
    
    # Get detailed market analysis
    analysis = indicators.get_market_analysis(symbol, "4h")
    
    if 'error' not in analysis:
        print(f"\n📊 Market Analysis:")
        print(f"Current Price: ${analysis['current_price']:.2f}")
        print(f"Overall Sentiment: {analysis['overall_sentiment']}")
        
        # Show key indicators
        indicators_data = analysis.get('indicators', {})
        if 'rsi' in indicators_data:
            rsi = indicators_data['rsi']
            print(f"RSI: {rsi['value']:.2f} - {rsi['interpretation']}")
        
        if 'macd' in indicators_data:
            macd = indicators_data['macd']
            print(f"MACD: {macd['interpretation']}")

def example_paper_trading():
    """Example: Test strategies with paper trading"""
    print("\n🎯 Paper Trading Example")
    print("=" * 40)
    
    # Initialize paper trading engine
    engine = PaperTradingEngine(initial_balance=10000.0)
    
    # Place some paper trades
    symbol = "BTCUSDT"
    
    # Market buy order
    buy_order = engine.place_order(symbol, "BUY", "MARKET", 0.1)
    print(f"Paper Buy Order: {buy_order.get('orderId')}")
    
    # Limit sell order
    sell_order = engine.place_order(symbol, "SELL", "LIMIT", 0.05, 45000)
    print(f"Paper Sell Order: {sell_order.get('orderId')}")
    
    # Check account status
    account = engine.get_account_info()
    print(f"\n💰 Paper Account Status:")
    print(f"Balance: ${account.balance:.2f}")
    print(f"Unrealized P&L: ${account.unrealized_pnl:.2f}")
    
    # Show positions
    positions = engine.get_positions()
    if positions:
        print("📊 Paper Positions:")
        for pos in positions:
            print(f"  {pos['symbol']}: {pos['quantity']:.4f} @ ${pos['avg_entry_price']:.2f}")

async def example_realtime_monitoring():
    """Example: Monitor real-time price feeds"""
    print("\n📱 Real-time Monitoring Example")
    print("=" * 40)
    
    # Initialize price monitor
    monitor = PriceMonitor()
    
    # Add price alerts
    monitor.add_price_alert("BTCUSDT", 45000, "above", 
                           lambda symbol, price, alert: print(f"🚨 ALERT: {symbol} above $45,000! Current: ${price}"))
    
    monitor.add_price_alert("BTCUSDT", 43000, "below",
                           lambda symbol, price, alert: print(f"🚨 ALERT: {symbol} below $43,000! Current: ${price}"))
    
    print("Starting price monitoring for 30 seconds...")
    print("Setting alerts for BTCUSDT above $45,000 and below $43,000")
    
    try:
        # Monitor for 30 seconds
        await asyncio.wait_for(monitor.start_monitoring(["BTCUSDT"]), timeout=30)
    except asyncio.TimeoutError:
        print("Monitoring completed")
    except KeyboardInterrupt:
        print("Monitoring stopped by user")
    finally:
        await monitor.stop_monitoring()

def example_notifications():
    """Example: Configure and test notifications"""
    print("\n🔔 Notifications Example")
    print("=" * 40)
    
    # Configure notification channels
    configure_notifications(email=True, discord=True, console=True)
    
    # Send test notifications
    notify_trade("BTCUSDT", "BUY", 0.1, 44000, "test_order_123")
    
    # Send custom notification
    from src.notifications.manager import Notification, NotificationType
    
    custom_notification = Notification(
        type=NotificationType.PORTFOLIO_SUMMARY,
        title="Daily Portfolio Report",
        message="Here's your daily portfolio summary",
        data={
            "balance": 10000,
            "pnl": 250,
            "positions": 3,
            "performance": "📈 +2.5%"
        },
        timestamp=datetime.now(),
        priority="normal"
    )
    
    results = notification_manager.send_notification(custom_notification)
    print("Custom notification sent:")
    for channel, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {channel}: {status}")

def example_advanced_orders():
    """Example: Place advanced order types (TESTNET ONLY)"""
    print("\n🏛️ Advanced Orders Example (TESTNET)")
    print("=" * 40)
    
    # NOTE: These examples require testnet setup
    try:
        from src.advanced.advanced_orders import (
            place_iceberg_order, place_post_only_order, 
            IcebergOrder, PostOnlyOrder
        )
        
        # Example iceberg order (split large order into smaller pieces)
        iceberg_data = IcebergOrder(
            symbol="BTCUSDT",
            side="BUY",
            total_qty=1.0,
            visible_qty=0.1,
            price=43000
        )
        
        print("Iceberg Order Configuration:")
        print(f"  Total Quantity: {iceberg_data.total_qty}")
        print(f"  Visible Quantity: {iceberg_data.visible_qty}")
        print(f"  Price: ${iceberg_data.price}")
        print("  (This will be split into 10 orders of 0.1 each)")
        
        # Example post-only order (ensures maker fee)
        post_only_data = PostOnlyOrder(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            price=43500
        )
        
        print("\nPost-Only Order Configuration:")
        print(f"  Quantity: {post_only_data.qty}")
        print(f"  Price: ${post_only_data.price}")
        print("  (Will only execute if it doesn't immediately match)")
        
        print("\n⚠️ NOTE: Uncomment the actual order placement in testnet environment")
        # Uncomment these lines when testing in a safe environment:
        # iceberg_orders = place_iceberg_order(iceberg_data)
        # post_only_order = place_post_only_order(post_only_data)
        
    except Exception as e:
        print(f"Advanced orders example failed: {e}")
        print("Make sure you're connected to testnet for safe testing")

def example_strategy_development():
    """Example: Combine multiple features for strategy development"""
    print("\n🧠 Strategy Development Example")
    print("=" * 40)
    
    # This example shows how to combine various features for a simple strategy
    symbol = "BTCUSDT"
    
    # 1. Analyze market conditions
    indicators = TechnicalIndicators()
    signals = indicators.generate_signals(symbol, "1h")
    
    # 2. Check risk parameters
    risk_manager = RiskManager()
    current_price = 44000  # Would get from market data
    stop_loss = current_price * 0.98  # 2% stop loss
    
    position_calc = risk_manager.calculate_position_size(symbol, current_price, stop_loss)
    
    # 3. Simple strategy logic
    buy_signals = len([s for s in signals if s.signal == "BUY"])
    sell_signals = len([s for s in signals if s.signal == "SELL"])
    
    print("Strategy Analysis:")
    print(f"  Symbol: {symbol}")
    print(f"  Buy Signals: {buy_signals}")
    print(f"  Sell Signals: {sell_signals}")
    
    if 'error' not in position_calc:
        print(f"  Recommended Size: {position_calc['position_size']:.4f}")
        print(f"  Risk Amount: ${position_calc['risk_amount']:.2f}")
    
    # 4. Strategy decision
    if buy_signals > sell_signals and position_calc.get('is_valid', False):
        print("\n✅ Strategy Decision: BUY signal generated")
        print("   Conditions met for potential long position")
        
        # 5. Test with paper trading first
        engine = PaperTradingEngine()
        paper_order = engine.place_order(symbol, "BUY", "MARKET", position_calc['position_size'])
        print(f"   Paper trade executed: {paper_order.get('orderId')}")
        
    else:
        print("\n❌ Strategy Decision: No clear signal or risk too high")
        print("   Waiting for better opportunity")

def main():
    """Run all examples"""
    print("🤖 Advanced Binance Trading Bot - Feature Examples")
    print("=" * 60)
    print("⚠️  Make sure you're using TESTNET for safety!")
    print("=" * 60)
    
    try:
        # Run synchronous examples
        example_portfolio_tracking()
        example_risk_management()
        example_technical_analysis()
        example_paper_trading()
        example_notifications()
        example_advanced_orders()
        example_strategy_development()
        
        # Run asynchronous example
        print("\n" + "=" * 60)
        print("Running real-time monitoring example...")
        asyncio.run(example_realtime_monitoring())
        
        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("🚀 You're ready to build advanced trading strategies!")
        
    except Exception as e:
        logger.error(f"Example execution failed: {e}")
        print(f"\n❌ Error running examples: {e}")
        print("Make sure your .env file is configured correctly")

if __name__ == "__main__":
    main()