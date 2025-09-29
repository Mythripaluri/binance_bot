import click
import asyncio
from tabulate import tabulate
from .utils.logger import get_logger
from .binance_client import get_client
from .validators import OrderBase, LimitOrder, StopLimitOrder, OCOOrder, TWAPParams, GridParams
from .orders.market_orders import place_market_order
from .orders.limit_orders import place_limit_order
from .orders.stop_limit import place_stop_limit
from .advanced.oco import place_oco
from .advanced.twap import run_twap
from .advanced.grid import run_grid

# New imports for enhanced features
from .portfolio.tracker import PortfolioTracker
from .risk.manager import RiskManager, RiskConfig
from .analysis.indicators import TechnicalIndicators
from .advanced.advanced_orders import (
    place_iceberg_order, place_post_only_order, place_reduce_only_order,
    place_trailing_stop_order, IcebergOrder, PostOnlyOrder, ReduceOnlyOrder
)
from .simulation.paper_trading import PaperTradingEngine
from .realtime.websocket_client import PriceMonitor, start_realtime_monitoring
from .notifications.manager import notification_manager, notify_trade, notify_alert

logger = get_logger()

@click.group()
def cli():
    """Binance USDT-M Futures CLI Bot"""
    pass

# --- Account Info Commands ---
@cli.command()
def account():
    """Check account information (balances, margin, etc.)"""
    client = get_client()
    try:
        resp = client.account()
        click.echo(resp)
    except Exception as e:
        logger.error(f"Failed to fetch account info: {e}")
        click.echo("Error fetching account info")

@cli.command()
@click.argument("symbol")
def orders(symbol):
    """Check open orders for a symbol"""
    client = get_client()
    try:
        resp = client.get_orders(symbol=symbol.upper())
        click.echo(tabulate(resp, headers="keys"))
    except Exception as e:
        logger.error(f"Failed to fetch orders for {symbol}: {e}")
        click.echo(f"Error fetching orders for {symbol}")

@cli.command()
@click.argument("symbol")
def positions(symbol):
    """Check positions for a symbol"""
    client = get_client()
    try:
        resp = client.get_position_risk(symbol=symbol.upper())
        click.echo(tabulate(resp, headers="keys"))
    except Exception as e:
        logger.error(f"Failed to fetch positions for {symbol}: {e}")
        click.echo(f"Error fetching positions for {symbol}")

# --- Market Commands ---
@cli.command()
def ping():
    """Ping the exchange and print server time"""
    client = get_client()
    try:
        pong = client.ping()
        server_time = client.time()
        click.echo(f"Ping: {pong}, Server Time: {server_time}")
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        click.echo("Error pinging server")

@cli.command()
@click.argument("symbol")
def price(symbol):
    """Get latest price for a symbol"""
    client = get_client()
    try:
        r = client.ticker_price(symbol=symbol.upper())
        click.echo(r)
    except Exception as e:
        logger.error(f"Failed to fetch price for {symbol}: {e}")
        click.echo(f"Error fetching price for {symbol}")

# --- Orders Group ---
@cli.group()
def order():
    """Place basic and advanced orders"""
    pass

@order.command("market")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--track/--no-track", default=True, help="Track in portfolio")
def order_market(symbol, side, qty, track):
    try:
        data = OrderBase(symbol=symbol.upper(), side=side.upper(), qty=qty)
        resp = place_market_order(data)
        click.echo(resp)
        
        # Track the order in portfolio if successful
        if track and resp and 'orderId' in resp:
            try:
                tracker = PortfolioTracker()
                tracker.record_trade_from_order(resp, "manual")
                
                # Send notification
                if 'fills' in resp and resp['fills']:
                    fill = resp['fills'][0]
                    notify_trade(symbol.upper(), side.upper(), qty, 
                               float(fill['price']), str(resp['orderId']))
                               
            except Exception as e:
                logger.warning(f"Portfolio tracking failed: {e}")
                
    except Exception as e:
        logger.error(f"Market order failed: {e}")
        click.echo("Error placing market order")

@order.command("limit")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--price", required=True, type=float)
@click.option("--tif", default="GTC", show_default=True)
@click.option("--track/--no-track", default=True, help="Track in portfolio")
def order_limit(symbol, side, qty, price, tif, track):
    try:
        data = LimitOrder(symbol=symbol.upper(), side=side.upper(), qty=qty, price=price)
        resp = place_limit_order(data, tif=tif)
        click.echo(resp)
        
        # Track the order in portfolio if successful
        if track and resp and 'orderId' in resp:
            try:
                tracker = PortfolioTracker()
                tracker.record_trade_from_order(resp, "manual")
            except Exception as e:
                logger.warning(f"Portfolio tracking failed: {e}")
                
    except Exception as e:
        logger.error(f"Limit order failed: {e}")
        click.echo("Error placing limit order")

@order.command("stop-limit")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--stop", required=True, type=float)
@click.option("--price", required=True, type=float)
@click.option("--tif", default="GTC", show_default=True)
def order_stop_limit(symbol, side, qty, stop, price, tif):
    try:
        data = StopLimitOrder(symbol=symbol.upper(), side=side.upper(), qty=qty, stop=stop, price=price)
        resp = place_stop_limit(data, tif=tif)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Stop-limit order failed: {e}")
        click.echo("Error placing stop-limit order")

@order.command("oco")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--tp", required=True, type=float)
@click.option("--sl", required=True, type=float)
def order_oco(symbol, side, qty, tp, sl):
    try:
        data = OCOOrder(symbol=symbol.upper(), side=side.upper(), qty=qty, tp=tp, sl=sl)
        resp = place_oco(data)
        click.echo(resp)
    except Exception as e:
        logger.error(f"OCO order failed: {e}")
        click.echo("Error placing OCO order")

@order.command("iceberg")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--total-qty", required=True, type=float)
@click.option("--visible-qty", required=True, type=float)
@click.option("--price", required=True, type=float)
def order_iceberg(symbol, side, total_qty, visible_qty, price):
    """Place an iceberg order"""
    try:
        data = IcebergOrder(symbol=symbol.upper(), side=side.upper(), 
                           total_qty=total_qty, visible_qty=visible_qty, price=price)
        resp = place_iceberg_order(data)
        click.echo(f"Iceberg order placed: {len(resp)} slices")
        for i, order in enumerate(resp):
            click.echo(f"Slice {i+1}: {order.get('orderId')}")
    except Exception as e:
        logger.error(f"Iceberg order failed: {e}")
        click.echo("Error placing iceberg order")

@order.command("post-only")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--price", required=True, type=float)
def order_post_only(symbol, side, qty, price):
    """Place a post-only order"""
    try:
        data = PostOnlyOrder(symbol=symbol.upper(), side=side.upper(), qty=qty, price=price)
        resp = place_post_only_order(data)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Post-only order failed: {e}")
        click.echo("Error placing post-only order")

@order.command("reduce-only")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--price", type=float, help="Price for limit order (omit for market)")
def order_reduce_only(symbol, side, qty, price):
    """Place a reduce-only order"""
    try:
        data = ReduceOnlyOrder(symbol=symbol.upper(), side=side.upper(), qty=qty, price=price)
        resp = place_reduce_only_order(data)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Reduce-only order failed: {e}")
        click.echo("Error placing reduce-only order")

@order.command("trailing-stop")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--callback-rate", required=True, type=float, help="Callback rate in percentage")
def order_trailing_stop(symbol, side, qty, callback_rate):
    """Place a trailing stop order"""
    try:
        resp = place_trailing_stop_order(symbol.upper(), side.upper(), qty, callback_rate)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Trailing stop order failed: {e}")
        click.echo("Error placing trailing stop order")

# --- Strategies Group ---
@cli.group()
def strat():
    """Run strategies (TWAP, Grid)"""
    pass

@strat.command("twap")
@click.option("--symbol", required=True)
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
@click.option("--qty", required=True, type=float)
@click.option("--slices", required=True, type=int)
@click.option("--duration", required=True, type=int, help="seconds")
def strat_twap(symbol, side, qty, slices, duration):
    try:
        params = TWAPParams(symbol=symbol.upper(), side=side.upper(), qty=qty, slices=slices, duration=duration)
        resp = run_twap(params)
        click.echo(tabulate([{ "slice": i+1, "result": r } for i, r in enumerate(resp)], headers="keys"))
    except Exception as e:
        logger.error(f"TWAP strategy failed: {e}")
        click.echo("Error running TWAP strategy")

@strat.command("grid")
@click.option("--symbol", required=True)
@click.option("--qty", required=True, type=float)
@click.option("--lower", required=True, type=float)
@click.option("--upper", required=True, type=float)
@click.option("--levels", required=True, type=int)
def strat_grid(symbol, qty, lower, upper, levels):
    try:
        params = GridParams(symbol=symbol.upper(), qty=qty, lower=lower, upper=upper, levels=levels)
        resp = run_grid(params)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Grid strategy failed: {e}")
        click.echo("Error running Grid strategy")

# --- Portfolio Management Group ---
@cli.group()
def portfolio():
    """Portfolio tracking and management"""
    pass

@portfolio.command("summary")
def portfolio_summary():
    """Get comprehensive portfolio summary"""
    try:
        tracker = PortfolioTracker()
        summary = tracker.get_portfolio_summary()
        
        click.echo("\n📊 PORTFOLIO SUMMARY")
        click.echo("=" * 50)
        click.echo(f"Total Balance: ${summary.get('total_wallet_balance', 0):.2f}")
        click.echo(f"Available Balance: ${summary.get('available_balance', 0):.2f}")
        click.echo(f"Unrealized P&L: ${summary.get('total_unrealized_pnl', 0):.2f}")
        click.echo(f"Active Positions: {summary.get('positions_count', 0)}")
        
        if summary.get('positions'):
            click.echo("\n📈 POSITIONS:")
            positions_table = []
            for pos in summary['positions']:
                positions_table.append({
                    'Symbol': pos['symbol'],
                    'Quantity': f"{pos['quantity']:.4f}",
                    'Avg Price': f"${pos['avg_price']:.2f}",
                    'Current Price': f"${pos['current_price']:.2f}",
                    'PnL': f"${pos['unrealized_pnl']:.2f}",
                    'PnL %': f"{pos['pnl_percentage']:.2f}%"
                })
            click.echo(tabulate(positions_table, headers="keys"))
            
    except Exception as e:
        logger.error(f"Portfolio summary failed: {e}")
        click.echo("Error getting portfolio summary")

@portfolio.command("history")
@click.option("--symbol", help="Filter by symbol")
@click.option("--days", default=7, help="Number of days to look back")
def portfolio_history(symbol, days):
    """Get trade history"""
    try:
        tracker = PortfolioTracker()
        history = tracker.get_trade_history(symbol, days)
        
        if history:
            click.echo(f"\n📋 TRADE HISTORY ({days} days)")
            click.echo("=" * 60)
            click.echo(tabulate(history, headers="keys"))
        else:
            click.echo("No trades found for the specified period")
            
    except Exception as e:
        logger.error(f"Portfolio history failed: {e}")
        click.echo("Error getting trade history")

# --- Risk Management Group ---
@cli.group()
def risk():
    """Risk management tools"""
    pass

@risk.command("check")
def risk_check():
    """Check current portfolio risk"""
    try:
        risk_manager = RiskManager()
        risk_status = risk_manager.check_portfolio_risk()
        
        click.echo("\n⚠️  RISK ASSESSMENT")
        click.echo("=" * 40)
        click.echo(f"Total Balance: ${risk_status.get('total_balance', 0):.2f}")
        click.echo(f"Portfolio Risk: {risk_status.get('portfolio_risk_percentage', 0):.2f}%")
        click.echo(f"Portfolio Exposure: {risk_status.get('portfolio_exposure', 0):.2f}%")
        click.echo(f"Open Positions: {risk_status.get('open_positions_count', 0)}")
        click.echo(f"Risk Status: {risk_status.get('risk_status', 'UNKNOWN')}")
        
        recommendations = risk_status.get('recommendations', [])
        if recommendations:
            click.echo("\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                click.echo(f"  • {rec}")
                
    except Exception as e:
        logger.error(f"Risk check failed: {e}")
        click.echo("Error checking portfolio risk")

@risk.command("calculate-size")
@click.option("--symbol", required=True)
@click.option("--entry-price", required=True, type=float)
@click.option("--stop-loss", required=True, type=float)
@click.option("--risk-amount", type=float, help="Custom risk amount (optional)")
def risk_calculate_size(symbol, entry_price, stop_loss, risk_amount):
    """Calculate optimal position size based on risk"""
    try:
        risk_manager = RiskManager()
        result = risk_manager.calculate_position_size(symbol, entry_price, stop_loss, risk_amount)
        
        if 'error' in result:
            click.echo(f"Error: {result['error']}")
            return
        
        click.echo("\n📐 POSITION SIZE CALCULATION")
        click.echo("=" * 45)
        click.echo(f"Symbol: {result['symbol']}")
        click.echo(f"Entry Price: ${result['entry_price']:.2f}")
        click.echo(f"Stop Loss: ${result['stop_loss_price']:.2f}")
        click.echo(f"Take Profit: ${result['take_profit_price']:.2f}")
        click.echo(f"\n💰 RECOMMENDED SIZE:")
        click.echo(f"Position Size: {result['position_size']:.4f}")
        click.echo(f"Position Value: ${result['position_value']:.2f}")
        click.echo(f"Risk Amount: ${result['risk_amount']:.2f}")
        click.echo(f"Risk %: {result['risk_percentage']:.2f}%")
        click.echo(f"Position %: {result['position_percentage']:.2f}%")
        
        warnings = result.get('warnings', [])
        if warnings:
            click.echo("\n⚠️  WARNINGS:")
            for warning in warnings:
                click.echo(f"  • {warning}")
                
    except Exception as e:
        logger.error(f"Position size calculation failed: {e}")
        click.echo("Error calculating position size")

# --- Technical Analysis Group ---
@cli.group()
def analysis():
    """Technical analysis tools"""
    pass

@analysis.command("signals")
@click.option("--symbol", required=True)
@click.option("--interval", default="1h", help="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)")
def analysis_signals(symbol, interval):
    """Get technical analysis signals"""
    try:
        indicators = TechnicalIndicators()
        signals = indicators.generate_signals(symbol.upper(), interval)
        
        if signals:
            click.echo(f"\n📈 TECHNICAL SIGNALS - {symbol.upper()} ({interval})")
            click.echo("=" * 55)
            
            signals_table = []
            for signal in signals:
                signals_table.append({
                    'Indicator': signal.indicator,
                    'Signal': signal.signal,
                    'Value': f"{signal.value:.4f}",
                    'Strength': f"{signal.strength:.2f}",
                    'Time': signal.timestamp
                })
            
            click.echo(tabulate(signals_table, headers="keys"))
            
            # Overall sentiment
            buy_signals = len([s for s in signals if s.signal == "BUY"])
            sell_signals = len([s for s in signals if s.signal == "SELL"])
            
            if buy_signals > sell_signals:
                sentiment = "🟢 BULLISH"
            elif sell_signals > buy_signals:
                sentiment = "🔴 BEARISH"
            else:
                sentiment = "🟡 NEUTRAL"
            
            click.echo(f"\nOverall Sentiment: {sentiment}")
        else:
            click.echo("No signals generated")
            
    except Exception as e:
        logger.error(f"Technical analysis failed: {e}")
        click.echo("Error generating technical signals")

@analysis.command("detailed")
@click.option("--symbol", required=True)
@click.option("--interval", default="1h")
def analysis_detailed(symbol, interval):
    """Get detailed market analysis"""
    try:
        indicators = TechnicalIndicators()
        analysis = indicators.get_market_analysis(symbol.upper(), interval)
        
        if 'error' in analysis:
            click.echo(f"Error: {analysis['error']}")
            return
        
        click.echo(f"\n📊 DETAILED ANALYSIS - {analysis['symbol']} ({interval})")
        click.echo("=" * 60)
        click.echo(f"Current Price: ${analysis['current_price']:.2f}")
        click.echo(f"Overall Sentiment: {analysis['overall_sentiment']} ({analysis['sentiment_strength']:.2f})")
        
        # Indicators
        indicators_data = analysis.get('indicators', {})
        
        click.echo("\n📈 INDICATORS:")
        if 'rsi' in indicators_data:
            rsi = indicators_data['rsi']
            click.echo(f"RSI: {rsi['value']:.2f} - {rsi['interpretation']}")
        
        if 'macd' in indicators_data:
            macd = indicators_data['macd']
            click.echo(f"MACD: {macd['interpretation']} (Histogram: {macd['histogram']:.4f})")
        
        if 'bollinger_bands' in indicators_data:
            bb = indicators_data['bollinger_bands']
            click.echo(f"Bollinger Bands: {bb['position']}")
        
        if 'moving_averages' in indicators_data:
            ma = indicators_data['moving_averages']
            click.echo(f"Moving Averages: {ma['trend']}")
        
        # Support/Resistance
        sr = analysis.get('support_resistance', {})
        if sr:
            click.echo(f"\n📊 LEVELS:")
            click.echo(f"Support: ${sr.get('support', 0):.2f}")
            click.echo(f"Resistance: ${sr.get('resistance', 0):.2f}")
            
    except Exception as e:
        logger.error(f"Detailed analysis failed: {e}")
        click.echo("Error performing detailed analysis")

# --- Paper Trading Group ---
@cli.group()
def paper():
    """Paper trading simulation"""
    pass

@paper.command("init")
@click.option("--balance", default=10000.0, help="Initial balance for paper trading")
def paper_init(balance):
    """Initialize paper trading account"""
    try:
        engine = PaperTradingEngine(initial_balance=balance)
        engine.reset_account(balance)
        click.echo(f"Paper trading account initialized with ${balance}")
    except Exception as e:
        logger.error(f"Paper trading init failed: {e}")
        click.echo("Error initializing paper trading")

@paper.command("buy")
@click.option("--symbol", required=True)
@click.option("--qty", required=True, type=float)
@click.option("--price", type=float, help="Price for limit order (omit for market)")
def paper_buy(symbol, qty, price):
    """Place paper buy order"""
    try:
        engine = PaperTradingEngine()
        order_type = "LIMIT" if price else "MARKET"
        resp = engine.place_order(symbol.upper(), "BUY", order_type, qty, price)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Paper buy failed: {e}")
        click.echo("Error placing paper buy order")

@paper.command("sell")
@click.option("--symbol", required=True)
@click.option("--qty", required=True, type=float)
@click.option("--price", type=float, help="Price for limit order (omit for market)")
def paper_sell(symbol, qty, price):
    """Place paper sell order"""
    try:
        engine = PaperTradingEngine()
        order_type = "LIMIT" if price else "MARKET"
        resp = engine.place_order(symbol.upper(), "SELL", order_type, qty, price)
        click.echo(resp)
    except Exception as e:
        logger.error(f"Paper sell failed: {e}")
        click.echo("Error placing paper sell order")

@paper.command("status")
def paper_status():
    """Get paper trading account status"""
    try:
        engine = PaperTradingEngine()
        account = engine.get_account_info()
        positions = engine.get_positions()
        stats = engine.get_performance_stats()
        
        click.echo("\n💰 PAPER TRADING ACCOUNT")
        click.echo("=" * 40)
        click.echo(f"Balance: ${account.balance:.2f}")
        click.echo(f"Margin Balance: ${account.margin_balance:.2f}")
        click.echo(f"Unrealized P&L: ${account.unrealized_pnl:.2f}")
        click.echo(f"Realized P&L: ${account.realized_pnl:.2f}")
        click.echo(f"Total Return: {stats['total_return_percentage']:.2f}%")
        
        if positions:
            click.echo("\n📊 POSITIONS:")
            click.echo(tabulate(positions, headers="keys"))
        
    except Exception as e:
        logger.error(f"Paper status failed: {e}")
        click.echo("Error getting paper trading status")

# --- Real-time Monitoring Group ---
@cli.group()
def monitor():
    """Real-time market monitoring"""
    pass

@monitor.command("price")
@click.option("--symbols", required=True, help="Comma-separated list of symbols")
@click.option("--duration", default=60, help="Duration in seconds")
def monitor_price(symbols, duration):
    """Monitor real-time prices"""
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        click.echo(f"Starting real-time price monitoring for {', '.join(symbol_list)}...")
        click.echo(f"Monitoring for {duration} seconds. Press Ctrl+C to stop.")
        
        async def run_monitoring():
            await start_realtime_monitoring(symbol_list, ["ticker"])
        
        # Run for specified duration
        try:
            asyncio.run(asyncio.wait_for(run_monitoring(), timeout=duration))
        except asyncio.TimeoutError:
            click.echo("Monitoring completed")
            
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped by user")
    except Exception as e:
        logger.error(f"Price monitoring failed: {e}")
        click.echo("Error starting price monitoring")

@monitor.command("alerts")
@click.option("--symbol", required=True)
@click.option("--target", required=True, type=float, help="Target price")
@click.option("--condition", required=True, type=click.Choice(["above", "below", "crosses_up", "crosses_down"]))
def monitor_alerts(symbol, target, condition):
    """Set up price alerts"""
    try:
        monitor = PriceMonitor()
        
        def alert_callback(symbol, price, alert):
            notify_alert(symbol, price, alert['target_price'], condition)
            click.echo(f"🚨 ALERT: {symbol} {condition} ${target} (Current: ${price})")
        
        monitor.add_price_alert(symbol.upper(), target, condition, alert_callback)
        
        click.echo(f"Price alert set: {symbol.upper()} {condition} ${target}")
        click.echo("Starting monitoring... Press Ctrl+C to stop.")
        
        async def run_alert_monitoring():
            await monitor.start_monitoring([symbol.upper()])
        
        asyncio.run(run_alert_monitoring())
        
    except KeyboardInterrupt:
        click.echo("\nAlert monitoring stopped")
    except Exception as e:
        logger.error(f"Alert monitoring failed: {e}")
        click.echo("Error setting up price alerts")

# --- Notifications Group ---
@cli.group()
def notify():
    """Notification management"""
    pass

@notify.command("config")
@click.option("--email/--no-email", default=True)
@click.option("--discord/--no-discord", default=True)
@click.option("--console/--no-console", default=True)
def notify_config(email, discord, console):
    """Configure notification channels"""
    try:
        from .notifications.manager import configure_notifications
        configure_notifications(email, discord, console)
        
        click.echo("Notification channels configured:")
        click.echo(f"  Email: {'✓' if email else '✗'}")
        click.echo(f"  Discord: {'✓' if discord else '✗'}")
        click.echo(f"  Console: {'✓' if console else '✗'}")
        
    except Exception as e:
        logger.error(f"Notification config failed: {e}")
        click.echo("Error configuring notifications")

@notify.command("test")
def notify_test():
    """Send test notification"""
    try:
        from .notifications.manager import notification_manager, Notification, NotificationType
        from datetime import datetime
        
        test_notification = Notification(
            type=NotificationType.PORTFOLIO_SUMMARY,
            title="Test Notification",
            message="This is a test notification from your trading bot.",
            data={"test": True, "timestamp": datetime.now().isoformat()},
            timestamp=datetime.now(),
            priority="normal"
        )
        
        results = notification_manager.send_notification(test_notification)
        
        click.echo("Test notification sent:")
        for channel, success in results.items():
            status = "✓" if success else "✗"
            click.echo(f"  {channel}: {status}")
            
    except Exception as e:
        logger.error(f"Test notification failed: {e}")
        click.echo("Error sending test notification")

if __name__ == "__main__":
    cli()











# import click
# from tabulate import tabulate
# from .utils.logger import get_logger
# from .binance_client import get_client
# from .validators import OrderBase, LimitOrder, StopLimitOrder, OCOOrder, TWAPParams, GridParams
# from .orders.market_orders import place_market_order
# from .orders.limit_orders import place_limit_order
# from .orders.stop_limit import place_stop_limit
# from .advanced.oco import place_oco
# from .advanced.twap import run_twap
# from .advanced.grid import run_grid

# logger = get_logger()

# # --- Account Info Commands ---

# @cli.command()
# def account():
#     """Check account information (balances, margin, etc.)"""
#     client = get_client()
#     resp = client.account()
#     print(resp)


# @cli.command()
# @click.argument("symbol")
# def orders(symbol):
#     """Check open orders for a symbol"""
#     client = get_client()
#     resp = client.get_orders(symbol=symbol)
#     print(resp)


# @cli.command()
# @click.argument("symbol")
# def positions(symbol):
#     """Check positions for a symbol"""
#     client = get_client()
#     resp = client.get_position_risk(symbol=symbol)
#     print(resp)


# @click.group()
# def cli():
#     "Binance USDT-M Futures CLI Bot"
#     pass

# @cli.command()
# def ping():
#     "Ping the exchange and print server time"
#     c = get_client()
#     r = c.ping()
#     t = c.time()
#     click.echo(f"Ping: {r}, Server Time: {t}")

# @cli.command()
# @click.argument("symbol")
# def price(symbol):
#     "Get latest price for a symbol"
#     c = get_client()
#     r = c.ticker_price(symbol=symbol.upper())
#     click.echo(r)

# @cli.group()
# def order():
#     "Place basic and advanced orders"
#     pass

# @order.command("market")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# def order_market(symbol, side, qty):
#     data = OrderBase(symbol=symbol, side=side.upper(), qty=qty)
#     resp = place_market_order(data)
#     click.echo(resp)

# @order.command("limit")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# @click.option("--price", required=True, type=float)
# @click.option("--tif", default="GTC", show_default=True)
# def order_limit(symbol, side, qty, price, tif):
#     data = LimitOrder(symbol=symbol, side=side.upper(), qty=qty, price=price)
#     resp = place_limit_order(data, tif=tif)
#     click.echo(resp)

# @order.command("stop-limit")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# @click.option("--stop", required=True, type=float)
# @click.option("--price", required=True, type=float)
# @click.option("--tif", default="GTC", show_default=True)
# def order_stop_limit(symbol, side, qty, stop, price, tif):
#     data = StopLimitOrder(symbol=symbol, side=side.upper(), qty=qty, stop=stop, price=price)
#     resp = place_stop_limit(data, tif=tif)
#     click.echo(resp)

# @order.command("oco")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# @click.option("--tp", required=True, type=float)
# @click.option("--sl", required=True, type=float)
# def order_oco(symbol, side, qty, tp, sl):
#     data = OCOOrder(symbol=symbol, side=side.upper(), qty=qty, tp=tp, sl=sl)
#     resp = place_oco(data)
#     click.echo(resp)

# @cli.group()
# def strat():
#     "Run strategies (TWAP, Grid)"
#     pass

# @strat.command("twap")
# @click.option("--symbol", required=True)
# @click.option("--side", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False))
# @click.option("--qty", required=True, type=float)
# @click.option("--slices", required=True, type=int)
# @click.option("--duration", required=True, type=int, help="seconds")
# def strat_twap(symbol, side, qty, slices, duration):
#     params = TWAPParams(symbol=symbol, side=side.upper(), qty=qty, slices=slices, duration=duration)
#     resp = run_twap(params)
#     click.echo(tabulate([{ "slice": i+1, "result": r } for i, r in enumerate(resp)], headers="keys"))

# @strat.command("grid")
# @click.option("--symbol", required=True)
# @click.option("--qty", required=True, type=float)
# @click.option("--lower", required=True, type=float)
# @click.option("--upper", required=True, type=float)
# @click.option("--levels", required=True, type=int)
# def strat_grid(symbol, qty, lower, upper, levels):
#     params = GridParams(symbol=symbol, qty=qty, lower=lower, upper=upper, levels=levels)
#     resp = run_grid(params)
#     click.echo(resp)

# if __name__ == "__main__":
#     cli()
