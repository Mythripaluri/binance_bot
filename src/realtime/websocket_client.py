import asyncio
import json
import websockets
from typing import Dict, List, Callable, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from ..utils.logger import get_logger

logger = get_logger()

@dataclass
class TickerData:
    symbol: str
    price: float
    price_change: float
    price_change_percent: float
    volume: float
    timestamp: datetime

@dataclass
class OrderBookLevel:
    price: float
    quantity: float

@dataclass
class OrderBookData:
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime

@dataclass
class TradeData:
    symbol: str
    price: float
    quantity: float
    side: str  # BUY or SELL
    timestamp: datetime

class BinanceWebSocketClient:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.base_url = "wss://fstream.binancefuture.com/ws/" if not testnet else "wss://stream.binancefuture.com/ws/"
        self.connections = {}
        self.callbacks = {
            'ticker': [],
            'orderbook': [],
            'trade': [],
            'kline': []
        }
        self.running_streams = set()
    
    def add_ticker_callback(self, callback: Callable[[TickerData], None]):
        """Add callback for ticker updates"""
        self.callbacks['ticker'].append(callback)
    
    def add_orderbook_callback(self, callback: Callable[[OrderBookData], None]):
        """Add callback for order book updates"""
        self.callbacks['orderbook'].append(callback)
    
    def add_trade_callback(self, callback: Callable[[TradeData], None]):
        """Add callback for trade updates"""
        self.callbacks['trade'].append(callback)
    
    async def start_ticker_stream(self, symbol: str):
        """Start real-time ticker stream for a symbol"""
        stream_name = f"{symbol.lower()}@ticker"
        
        if stream_name in self.running_streams:
            logger.warning(f"Ticker stream for {symbol} already running")
            return
        
        self.running_streams.add(stream_name)
        
        try:
            url = f"{self.base_url}{stream_name}"
            logger.info(f"Starting ticker stream for {symbol}: {url}")
            
            async with websockets.connect(url) as websocket:
                self.connections[stream_name] = websocket
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        ticker = TickerData(
                            symbol=data['s'],
                            price=float(data['c']),
                            price_change=float(data['P']),
                            price_change_percent=float(data['p']),
                            volume=float(data['v']),
                            timestamp=datetime.now()
                        )
                        
                        # Call all registered callbacks
                        for callback in self.callbacks['ticker']:
                            try:
                                callback(ticker)
                            except Exception as e:
                                logger.error(f"Error in ticker callback: {e}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding ticker message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing ticker data: {e}")
                        
        except Exception as e:
            logger.error(f"Error in ticker stream for {symbol}: {e}")
        finally:
            self.running_streams.discard(stream_name)
            if stream_name in self.connections:
                del self.connections[stream_name]
    
    async def start_orderbook_stream(self, symbol: str, levels: int = 5):
        """Start real-time order book stream"""
        stream_name = f"{symbol.lower()}@depth{levels}"
        
        if stream_name in self.running_streams:
            logger.warning(f"Order book stream for {symbol} already running")
            return
        
        self.running_streams.add(stream_name)
        
        try:
            url = f"{self.base_url}{stream_name}"
            logger.info(f"Starting order book stream for {symbol}: {url}")
            
            async with websockets.connect(url) as websocket:
                self.connections[stream_name] = websocket
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        bids = [OrderBookLevel(float(bid[0]), float(bid[1])) for bid in data['b']]
                        asks = [OrderBookLevel(float(ask[0]), float(ask[1])) for ask in data['a']]
                        
                        orderbook = OrderBookData(
                            symbol=data['s'],
                            bids=bids,
                            asks=asks,
                            timestamp=datetime.now()
                        )
                        
                        # Call all registered callbacks
                        for callback in self.callbacks['orderbook']:
                            try:
                                callback(orderbook)
                            except Exception as e:
                                logger.error(f"Error in orderbook callback: {e}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding orderbook message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing orderbook data: {e}")
                        
        except Exception as e:
            logger.error(f"Error in orderbook stream for {symbol}: {e}")
        finally:
            self.running_streams.discard(stream_name)
            if stream_name in self.connections:
                del self.connections[stream_name]
    
    async def start_trade_stream(self, symbol: str):
        """Start real-time trade stream"""
        stream_name = f"{symbol.lower()}@aggTrade"
        
        if stream_name in self.running_streams:
            logger.warning(f"Trade stream for {symbol} already running")
            return
        
        self.running_streams.add(stream_name)
        
        try:
            url = f"{self.base_url}{stream_name}"
            logger.info(f"Starting trade stream for {symbol}: {url}")
            
            async with websockets.connect(url) as websocket:
                self.connections[stream_name] = websocket
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        trade = TradeData(
                            symbol=data['s'],
                            price=float(data['p']),
                            quantity=float(data['q']),
                            side="SELL" if data['m'] else "BUY",  # m = true means buyer is market maker (sell)
                            timestamp=datetime.fromtimestamp(data['T'] / 1000)
                        )
                        
                        # Call all registered callbacks
                        for callback in self.callbacks['trade']:
                            try:
                                callback(trade)
                            except Exception as e:
                                logger.error(f"Error in trade callback: {e}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding trade message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing trade data: {e}")
                        
        except Exception as e:
            logger.error(f"Error in trade stream for {symbol}: {e}")
        finally:
            self.running_streams.discard(stream_name)
            if stream_name in self.connections:
                del self.connections[stream_name]
    
    async def start_multiple_streams(self, symbols: List[str], stream_types: List[str]):
        """Start multiple streams concurrently"""
        tasks = []
        
        for symbol in symbols:
            for stream_type in stream_types:
                if stream_type == "ticker":
                    tasks.append(asyncio.create_task(self.start_ticker_stream(symbol)))
                elif stream_type == "orderbook":
                    tasks.append(asyncio.create_task(self.start_orderbook_stream(symbol)))
                elif stream_type == "trade":
                    tasks.append(asyncio.create_task(self.start_trade_stream(symbol)))
        
        if tasks:
            logger.info(f"Starting {len(tasks)} WebSocket streams...")
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_stream(self, stream_name: str):
        """Stop a specific stream"""
        if stream_name in self.connections:
            await self.connections[stream_name].close()
            del self.connections[stream_name]
            self.running_streams.discard(stream_name)
            logger.info(f"Stopped stream: {stream_name}")
    
    async def stop_all_streams(self):
        """Stop all running streams"""
        for stream_name in list(self.connections.keys()):
            await self.stop_stream(stream_name)
        logger.info("All streams stopped")

class PriceMonitor:
    """Price monitoring with alerts and notifications"""
    
    def __init__(self):
        self.ws_client = BinanceWebSocketClient()
        self.price_alerts = {}  # symbol -> list of alerts
        self.current_prices = {}
        
        # Register callback for price updates
        self.ws_client.add_ticker_callback(self._handle_price_update)
    
    def add_price_alert(self, symbol: str, target_price: float, 
                       condition: str, callback: Optional[Callable] = None):
        """
        Add price alert
        
        Args:
            symbol: Trading symbol
            target_price: Price to alert at
            condition: 'above', 'below', 'crosses_up', 'crosses_down'
            callback: Optional callback function to call when alert triggers
        """
        if symbol not in self.price_alerts:
            self.price_alerts[symbol] = []
        
        alert = {
            'target_price': target_price,
            'condition': condition,
            'callback': callback,
            'triggered': False,
            'created_at': datetime.now()
        }
        
        self.price_alerts[symbol].append(alert)
        logger.info(f"Added price alert for {symbol}: {condition} {target_price}")
    
    def _handle_price_update(self, ticker_data: TickerData):
        """Handle incoming price updates and check alerts"""
        symbol = ticker_data.symbol
        current_price = ticker_data.price
        previous_price = self.current_prices.get(symbol)
        
        self.current_prices[symbol] = current_price
        
        # Check alerts for this symbol
        if symbol in self.price_alerts:
            for alert in self.price_alerts[symbol]:
                if alert['triggered']:
                    continue
                
                should_trigger = False
                condition = alert['condition']
                target = alert['target_price']
                
                if condition == 'above' and current_price > target:
                    should_trigger = True
                elif condition == 'below' and current_price < target:
                    should_trigger = True
                elif condition == 'crosses_up' and previous_price is not None:
                    if previous_price <= target < current_price:
                        should_trigger = True
                elif condition == 'crosses_down' and previous_price is not None:
                    if previous_price >= target > current_price:
                        should_trigger = True
                
                if should_trigger:
                    alert['triggered'] = True
                    self._trigger_alert(symbol, alert, current_price)
    
    def _trigger_alert(self, symbol: str, alert: Dict, current_price: float):
        """Trigger a price alert"""
        message = f"PRICE ALERT: {symbol} {alert['condition']} {alert['target_price']} (Current: {current_price})"
        logger.info(message)
        
        # Call custom callback if provided
        if alert['callback']:
            try:
                alert['callback'](symbol, current_price, alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def start_monitoring(self, symbols: List[str]):
        """Start monitoring prices for given symbols"""
        logger.info(f"Starting price monitoring for: {', '.join(symbols)}")
        await self.ws_client.start_multiple_streams(symbols, ["ticker"])
    
    async def stop_monitoring(self):
        """Stop price monitoring"""
        await self.ws_client.stop_all_streams()
        logger.info("Price monitoring stopped")
    
    def get_current_prices(self) -> Dict[str, float]:
        """Get current prices for all monitored symbols"""
        return self.current_prices.copy()
    
    def get_active_alerts(self) -> Dict[str, List[Dict]]:
        """Get all active (non-triggered) alerts"""
        active_alerts = {}
        
        for symbol, alerts in self.price_alerts.items():
            active = [alert for alert in alerts if not alert['triggered']]
            if active:
                active_alerts[symbol] = active
        
        return active_alerts

# Example usage functions
def create_sample_callbacks():
    """Create sample callbacks for demonstration"""
    
    def on_price_update(ticker: TickerData):
        logger.info(f"Price Update: {ticker.symbol} = ${ticker.price:.2f} ({ticker.price_change_percent:+.2f}%)")
    
    def on_orderbook_update(orderbook: OrderBookData):
        best_bid = orderbook.bids[0].price if orderbook.bids else 0
        best_ask = orderbook.asks[0].price if orderbook.asks else 0
        spread = best_ask - best_bid if best_bid and best_ask else 0
        logger.info(f"OrderBook: {orderbook.symbol} Bid: {best_bid} Ask: {best_ask} Spread: {spread:.2f}")
    
    def on_trade_update(trade: TradeData):
        logger.info(f"Trade: {trade.symbol} {trade.side} {trade.quantity} @ {trade.price}")
    
    def on_price_alert(symbol: str, price: float, alert: Dict):
        logger.info(f"🚨 ALERT TRIGGERED: {symbol} reached {price} (Target: {alert['target_price']})")
    
    return {
        'price': on_price_update,
        'orderbook': on_orderbook_update,
        'trade': on_trade_update,
        'alert': on_price_alert
    }

async def start_realtime_monitoring(symbols: List[str], stream_types: List[str] = None):
    """Start real-time monitoring with sample callbacks"""
    if stream_types is None:
        stream_types = ["ticker", "orderbook", "trade"]
    
    ws_client = BinanceWebSocketClient()
    callbacks = create_sample_callbacks()
    
    # Register callbacks
    ws_client.add_ticker_callback(callbacks['price'])
    ws_client.add_orderbook_callback(callbacks['orderbook'])
    ws_client.add_trade_callback(callbacks['trade'])
    
    try:
        await ws_client.start_multiple_streams(symbols, stream_types)
    except KeyboardInterrupt:
        logger.info("Stopping monitoring...")
        await ws_client.stop_all_streams()