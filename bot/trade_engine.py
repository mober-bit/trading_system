from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder, util
import time
import logging
from datetime import datetime
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bot.logger import log_trade
import pandas as pd
import sqlite3
import yfinance as yf

class TradeUtils:
    def __init__(self, commission_per_share=0.005, min_commission=1.0, cooldown_seconds=60):
        self.ib = IB()
        self.total_commission = 0.0
        self.last_trade_time = None
        self.cooldown_seconds = cooldown_seconds
        self.commission_per_share = commission_per_share
        self.min_commission = min_commission
        

    def calculate_commission(self, size):
        commission = max(size * self.commission_per_share, self.min_commission)
        self.total_commission += commission
        return commission
    

    def fetch_recent_ohlcv(bot, symbol='AAPL', duration='2 D', bar_size='5 mins'):
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            bot.ib.qualifyContracts(contract)

            bars = bot.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )

            df = util.df(bars)
            df = df[['high', 'low', 'close']]  # Keep only needed columns
            print(f"📊 Fetched {len(df)} bars for {symbol}")
            return df
        except Exception as e:
            print(f"❌ Failed to fetch OHLCV data: {e}")
            return None
        
    @staticmethod
    def calculate_atr( df, period=14):
        if df is None or df.empty:
           print("⚠️ Empty DataFrame")
           return None
        try:
            high = df['high']
            low = df['low']
            close = df['close']

            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()

            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            latest_atr = atr.iloc[-1]
            print(f"📊 ATR({period}) = {latest_atr:.2f}")
            return latest_atr
        except Exception as e:
              print(f"⚠️ ATR calculation error: {e}")
              return None

    @staticmethod
    def fetch_price_yf(symbol):
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.fast_info.get("last_price")

            # Fallback to latest close if fast_info fails
            if price is None or pd.isna(price):
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                    print(f"📉 Fallback to last close: {price}")
                else:
                    raise ValueError("No historical data available")

            return price

        except Exception as e:
            print(f"⚠️ yfinance price fetch failed for {symbol}: {e}")
            return None

    def update_trade_time(self):
            self.last_trade_time = datetime.now()

    def is_cooldown_active(self):
        now = datetime.now()
        if self.last_trade_time and (now - self.last_trade_time).total_seconds() < self.cooldown_seconds:
            return True
        return False

    

    def calculate_position_size(self, capital, risk_pct, stop_distance):
        risk_amount = capital * risk_pct
        return max(int(risk_amount / stop_distance), 1)
    
    def init_trade_db(db_path='data files/trades.db'):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                quantity INTEGER,
                entry_price REAL,
                stop_price REAL,
                take_profit_price REAL,
                commission REAL,
                atr REAL

            )
        ''')
        conn.commit()
        conn.close()

    def log_trade_to_db(symbol, side, quantity, entry_price, stop_price, take_profit_price, commission, atr, db_path='data files/trades.db'):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (timestamp, symbol, side, quantity, entry_price, stop_price, take_profit_price, commission, atr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
            datetime.now().isoformat(),
            symbol,
            side,
            quantity,
            entry_price,
            stop_price,
            take_profit_price,
            commission,
            atr
        ))
        conn.commit()
        conn.close()
        print(f"📝 Trade logged to DB: {symbol} {side} {quantity} @ {entry_price}")    
    
class TradeEngine:
    def __init__(self, host='127.0.0.1', port=7497, clientId=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.clientId = clientId
        self.connect()
        self.utils = TradeUtils(self.ib)
        
        


    def connect(self):
        try:
            self.ib.connect(self.host, self.port, self.clientId)
            print("✅ Connected to IBKR")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to IBKR: {e}")
            print("Make sure TWS or IB Gateway is running and API is enabled")
            return False

    


    def get_live_price(self, symbol):
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            ticker = self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(1)  # allow time for data
            price = ticker.marketPrice()
            print(f"📈 Live price for {symbol}: {price}")
            return price
        except Exception as e:
            print(f"❌ Failed to get live price: {e}")
            return None



    def place_order(self, symbol, action, quantity, limit_price=None):
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            order = MarketOrder(action, quantity) if limit_price is None else LimitOrder(action, quantity, limit_price)
            trade = self.ib.placeOrder(contract, order)

            self.ib.sleep(1)  
            status= trade.orderStatus.status
            filled = trade.orderStatus.filled
            remaining = trade.orderStatus.remaining

            commission = self.utils.calculate_commission(quantity)
            self.utils.update_trade_time()
            print(f"📦 Order placed: {action} {quantity} {symbol}")
            print(f"📦 Order status: {status}, Filled: {filled}, Remaining: {remaining}")
            print(f"💸 Estimated commission: {commission:.2f}, Total: {self.utils.total_commission:.2f}")



            return trade
        except Exception as e:
            print(f"❌ Failed to place order: {e}")
            return None

    def place_stop_order(self, symbol, action, quantity, limit_price=None):
        if self.utils.is_cooldown_active():
            print("⏳ Cooldown active, skipping trade")
            return None

        try:
            contract = Stock(symbol, 'SMART', 'USD')
            order = MarketOrder(action, quantity) if limit_price is None else LimitOrder(action, quantity, limit_price)
            trade = self.ib.placeOrder(contract, order)
            print(f"📦 Order placed: {action} {quantity} {symbol} @ {stop_price}")
            print(f"💸 Estimated commission: {commission:.2f}, Total: {self.utils.total_commission:.2f}")
            log_trade(symbol, action, quantity, f"Stop @ {stop_price}")
            return trade

        except Exception as e:
            print(f"❌ Failed to place stop order: {e}")
            return None
    def place_bracket_order(self, symbol, action, quantity, entry_price, stop_price, take_profit_price):
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)

            # Parent order: entry
            parent = LimitOrder(action, quantity, entry_price)
            parent.transmit = False

            # Stop-loss order
            opposite_action = 'SELL' if action == 'BUY' else 'BUY'
            stop = StopOrder(opposite_action, quantity, stop_price)
            stop.parentId = parent.orderId
            stop.transmit = False

            # Take-profit order
            take_profit = LimitOrder(opposite_action, quantity, take_profit_price)
            take_profit.parentId = parent.orderId
            take_profit.transmit = True

            # Place all orders
            self.ib.placeOrder(contract, parent)
            self.ib.placeOrder(contract, stop)
            self.ib.placeOrder(contract, take_profit)

            # Log and cooldown
            commission = self.utils.calculate_commission(quantity)
            self.utils.update_trade_time()
            log_trade(symbol, action, quantity, f"Entry @ {entry_price}, TP @ {take_profit_price}, SL @ {stop_price}")
            self.utils.log_trade_to_db(
            symbol, action, quantity,
            entry_price, stop_price, take_profit_price,
            commission, 0)  # atr not defined, using 0
            print(f"🎯 Bracket order placed: {action} {quantity} {symbol} @ {entry_price} → TP: {take_profit_price}, SL: {stop_price}")
            print(f"💸 Estimated commission: {commission:.2f}, Total: {self.utils.total_commission:.2f}")
            return parent
        except Exception as e:
            print(f"❌ Failed to place bracket order: {e}")
            return None
    
    def disconnect(self):
        try:
            self.ib.disconnect()
            print("❌ Disconnected from IBKR")
        except Exception as e:
            print(f"❌ Error disconnecting.................: {e}")

