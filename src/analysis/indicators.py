import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from ..binance_client import get_client
from ..utils.logger import get_logger

logger = get_logger()

@dataclass
class IndicatorSignal:
    indicator: str
    signal: str  # BUY, SELL, NEUTRAL
    value: float
    strength: float  # 0-1, how strong the signal is
    timestamp: str

class TechnicalIndicators:
    def __init__(self):
        self.client = get_client()
    
    def get_kline_data(self, symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
        """Get candlestick data from Binance"""
        try:
            klines = self.client.klines(symbol=symbol, interval=interval, limit=limit)
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert to appropriate data types
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df[numeric_columns]
            
        except Exception as e:
            logger.error(f"Error getting kline data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period).mean()
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = self.calculate_sma(prices, period)
        std = prices.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def generate_signals(self, symbol: str, interval: str = "1h", lookback: int = 100) -> List[IndicatorSignal]:
        """Generate trading signals from multiple indicators"""
        try:
            df = self.get_kline_data(symbol, interval, lookback)
            
            if df.empty:
                return []
            
            signals = []
            current_price = df['close'].iloc[-1]
            
            # RSI Signal
            rsi = self.calculate_rsi(df['close'])
            current_rsi = rsi.iloc[-1]
            
            if current_rsi < 30:
                signals.append(IndicatorSignal(
                    indicator="RSI",
                    signal="BUY",
                    value=current_rsi,
                    strength=min((30 - current_rsi) / 30, 1.0),
                    timestamp=df.index[-1].isoformat()
                ))
            elif current_rsi > 70:
                signals.append(IndicatorSignal(
                    indicator="RSI",
                    signal="SELL",
                    value=current_rsi,
                    strength=min((current_rsi - 70) / 30, 1.0),
                    timestamp=df.index[-1].isoformat()
                ))
            else:
                signals.append(IndicatorSignal(
                    indicator="RSI",
                    signal="NEUTRAL",
                    value=current_rsi,
                    strength=0.0,
                    timestamp=df.index[-1].isoformat()
                ))
            
            # MACD Signal
            macd_data = self.calculate_macd(df['close'])
            current_macd = macd_data['macd'].iloc[-1]
            current_signal = macd_data['signal'].iloc[-1]
            current_histogram = macd_data['histogram'].iloc[-1]
            
            if current_macd > current_signal and current_histogram > 0:
                signals.append(IndicatorSignal(
                    indicator="MACD",
                    signal="BUY",
                    value=current_histogram,
                    strength=min(abs(current_histogram) / (current_price * 0.01), 1.0),
                    timestamp=df.index[-1].isoformat()
                ))
            elif current_macd < current_signal and current_histogram < 0:
                signals.append(IndicatorSignal(
                    indicator="MACD",
                    signal="SELL",
                    value=current_histogram,
                    strength=min(abs(current_histogram) / (current_price * 0.01), 1.0),
                    timestamp=df.index[-1].isoformat()
                ))
            else:
                signals.append(IndicatorSignal(
                    indicator="MACD",
                    signal="NEUTRAL",
                    value=current_histogram,
                    strength=0.0,
                    timestamp=df.index[-1].isoformat()
                ))
            
            # Moving Average Signal
            sma_20 = self.calculate_sma(df['close'], 20)
            sma_50 = self.calculate_sma(df['close'], 50)
            
            current_sma_20 = sma_20.iloc[-1]
            current_sma_50 = sma_50.iloc[-1]
            
            if current_price > current_sma_20 > current_sma_50:
                signals.append(IndicatorSignal(
                    indicator="MA_CROSS",
                    signal="BUY",
                    value=current_price - current_sma_20,
                    strength=min((current_price - current_sma_20) / (current_price * 0.02), 1.0),
                    timestamp=df.index[-1].isoformat()
                ))
            elif current_price < current_sma_20 < current_sma_50:
                signals.append(IndicatorSignal(
                    indicator="MA_CROSS",
                    signal="SELL",
                    value=current_sma_20 - current_price,
                    strength=min((current_sma_20 - current_price) / (current_price * 0.02), 1.0),
                    timestamp=df.index[-1].isoformat()
                ))
            else:
                signals.append(IndicatorSignal(
                    indicator="MA_CROSS",
                    signal="NEUTRAL",
                    value=0,
                    strength=0.0,
                    timestamp=df.index[-1].isoformat()
                ))
            
            # Bollinger Bands Signal
            bb = self.calculate_bollinger_bands(df['close'])
            current_upper = bb['upper'].iloc[-1]
            current_lower = bb['lower'].iloc[-1]
            current_middle = bb['middle'].iloc[-1]
            
            if current_price <= current_lower:
                signals.append(IndicatorSignal(
                    indicator="BOLLINGER",
                    signal="BUY",
                    value=current_lower - current_price,
                    strength=min((current_lower - current_price) / (current_price * 0.02), 1.0),
                    timestamp=df.index[-1].isoformat()
                ))
            elif current_price >= current_upper:
                signals.append(IndicatorSignal(
                    indicator="BOLLINGER",
                    signal="SELL",
                    value=current_price - current_upper,
                    strength=min((current_price - current_upper) / (current_price * 0.02), 1.0),
                    timestamp=df.index[-1].isoformat()
                ))
            else:
                signals.append(IndicatorSignal(
                    indicator="BOLLINGER",
                    signal="NEUTRAL",
                    value=0,
                    strength=0.0,
                    timestamp=df.index[-1].isoformat()
                ))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return []
    
    def get_market_analysis(self, symbol: str, interval: str = "1h") -> Dict:
        """Get comprehensive market analysis"""
        try:
            df = self.get_kline_data(symbol, interval, 200)
            
            if df.empty:
                return {"error": "No data available"}
            
            current_price = df['close'].iloc[-1]
            
            # Calculate all indicators
            rsi = self.calculate_rsi(df['close'])
            macd_data = self.calculate_macd(df['close'])
            bb = self.calculate_bollinger_bands(df['close'])
            stoch = self.calculate_stochastic(df['high'], df['low'], df['close'])
            atr = self.calculate_atr(df['high'], df['low'], df['close'])
            
            sma_20 = self.calculate_sma(df['close'], 20)
            sma_50 = self.calculate_sma(df['close'], 50)
            sma_200 = self.calculate_sma(df['close'], 200)
            
            # Generate overall sentiment
            signals = self.generate_signals(symbol, interval)
            buy_signals = len([s for s in signals if s.signal == "BUY"])
            sell_signals = len([s for s in signals if s.signal == "SELL"])
            
            if buy_signals > sell_signals:
                overall_sentiment = "BULLISH"
                sentiment_strength = buy_signals / len(signals)
            elif sell_signals > buy_signals:
                overall_sentiment = "BEARISH"
                sentiment_strength = sell_signals / len(signals)
            else:
                overall_sentiment = "NEUTRAL"
                sentiment_strength = 0.5
            
            analysis = {
                "symbol": symbol,
                "current_price": current_price,
                "timestamp": df.index[-1].isoformat(),
                "overall_sentiment": overall_sentiment,
                "sentiment_strength": sentiment_strength,
                "indicators": {
                    "rsi": {
                        "value": rsi.iloc[-1],
                        "interpretation": self._interpret_rsi(rsi.iloc[-1])
                    },
                    "macd": {
                        "macd": macd_data['macd'].iloc[-1],
                        "signal": macd_data['signal'].iloc[-1],
                        "histogram": macd_data['histogram'].iloc[-1],
                        "interpretation": self._interpret_macd(macd_data['macd'].iloc[-1], macd_data['signal'].iloc[-1])
                    },
                    "bollinger_bands": {
                        "upper": bb['upper'].iloc[-1],
                        "middle": bb['middle'].iloc[-1],
                        "lower": bb['lower'].iloc[-1],
                        "position": self._interpret_bb_position(current_price, bb['upper'].iloc[-1], bb['lower'].iloc[-1])
                    },
                    "moving_averages": {
                        "sma_20": sma_20.iloc[-1],
                        "sma_50": sma_50.iloc[-1],
                        "sma_200": sma_200.iloc[-1],
                        "trend": self._interpret_ma_trend(current_price, sma_20.iloc[-1], sma_50.iloc[-1], sma_200.iloc[-1])
                    },
                    "atr": {
                        "value": atr.iloc[-1],
                        "volatility": self._interpret_atr(atr.iloc[-1], current_price)
                    }
                },
                "signals": [
                    {
                        "indicator": s.indicator,
                        "signal": s.signal,
                        "strength": s.strength,
                        "value": s.value
                    }
                    for s in signals
                ],
                "support_resistance": self._find_support_resistance(df)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in market analysis for {symbol}: {e}")
            return {"error": str(e)}
    
    def _interpret_rsi(self, rsi_value: float) -> str:
        """Interpret RSI value"""
        if rsi_value < 30:
            return "Oversold - Potential buying opportunity"
        elif rsi_value > 70:
            return "Overbought - Potential selling opportunity"
        else:
            return "Neutral - No clear signal"
    
    def _interpret_macd(self, macd: float, signal: float) -> str:
        """Interpret MACD signal"""
        if macd > signal:
            return "Bullish momentum"
        elif macd < signal:
            return "Bearish momentum"
        else:
            return "Neutral momentum"
    
    def _interpret_bb_position(self, price: float, upper: float, lower: float) -> str:
        """Interpret Bollinger Bands position"""
        if price >= upper:
            return "Above upper band - Overbought"
        elif price <= lower:
            return "Below lower band - Oversold"
        else:
            return "Within bands - Normal range"
    
    def _interpret_ma_trend(self, price: float, sma20: float, sma50: float, sma200: float) -> str:
        """Interpret moving average trend"""
        if price > sma20 > sma50 > sma200:
            return "Strong uptrend"
        elif price > sma20 > sma50:
            return "Uptrend"
        elif price < sma20 < sma50 < sma200:
            return "Strong downtrend"
        elif price < sma20 < sma50:
            return "Downtrend"
        else:
            return "Sideways/Mixed"
    
    def _interpret_atr(self, atr: float, price: float) -> str:
        """Interpret ATR for volatility"""
        atr_percentage = (atr / price) * 100
        
        if atr_percentage > 3:
            return "High volatility"
        elif atr_percentage > 1.5:
            return "Moderate volatility"
        else:
            return "Low volatility"
    
    def _find_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict:
        """Find basic support and resistance levels"""
        try:
            # Simple implementation using recent highs and lows
            recent_data = df.tail(50)
            
            resistance = recent_data['high'].rolling(window=window).max().iloc[-1]
            support = recent_data['low'].rolling(window=window).min().iloc[-1]
            
            return {
                "resistance": resistance,
                "support": support
            }
        except:
            return {"resistance": 0, "support": 0}