import pandas as pd
import numpy as np
import time
import yfinance as  yf
from pathlib import Path
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from trade_engine import TradeEngine
from bot.signals import generate_trade_signal
from logger import log_trade
from bot.trade_engine import TradeUtils, TradeEngine
from data.vantage_loader import ingest_data, live_data
from dotenv import load_dotenv


import time
from datetime import datetime, time as dtime

ticker=[
    "SNN", "AKAM", "GMED", "PLUG", "NVDA", "BBAI", "PFE", "ACHR", "TTOO", "AMC",
    "CVNA", "SOFI", "GME", "LCID", "RIVN", "FUBO", "MULN", "NKLA", "WBD", "SNAP",
    "TSM", "AAL", "DAL", "UBER", "LYFT", "COIN", "MARA", "RIOT", "BB", "XPEV",
    "NIO", "PLTR", "DKNG", "AFRM", "CHPT", "ENPH", "SPWR", "QS", "BYND", "SPCE",
    "TDOC", "ZM", "SHOP", "FSLY", "UPST", "AI", "U", "RBLX", "DKNG", "MSTR"
      ]


def is_market_open():
    now = datetime.now().time()
    return dtime(9, 30) <= now <= dtime(16, 0)  # US market hours (ET)


def run_bot_all_day(bot, utils,live):
    live.live_data_websocket()
    print("🚀 Starting trading loop...")
    load_dotenv()
    token = os.getenv("fintoken")


    print("🔌 IB connected:", bot.ib.isConnected())

    while True:
        
        #if not is_market_open():
            #print("⏳ Market closed. Sleeping...")
            #time.sleep(10)
            #continue

        if utils.is_cooldown_active():
            print("🕒 Cooldown active, skipping this cycle")
            time.sleep(10)
            continue

        

       
        for symbol in ticker:
            try:
                print(f"📊 Processing {symbol}...")
                
                
                df = utils.fetch_recent_ohlcv(bot, symbol)  # You'll need to implement this
                print("🔌 IB connected:", bot.ib.isConnected())

                if df is None or df.empty:
                    print(f"⚠️ No OHLCV data for {symbol}, using yfinance fallback")
                    df = ingest_data(symbol)
                    if df is None or df.empty:
                        print(f"⚠️ Failed to fetch data for {symbol}, skipping")
                        continue
                    

                atr = utils.calculate_atr(df)
                if atr is None or atr <= 0:
                    print(f"⚠️ Invalid ATR for {symbol}, skipping")
                    continue
                
                if atr < 0.05:
                    print(f"⚠️ ATR too low for {symbol} ({atr:.2f}), skipping")
                    continue

                #entry_price= TradeUtils.fetch_price_yf(symbol) 
                #print(f"🔔 Fetched live price {symbol}: {entry_price}") 
                 

                entry_price = live.get_live_price(symbol)
                if entry_price is None:
                    print(f"⚠️ Could not get live price for {symbol}, skipping")
                    continue
                print(f"🔔 Fetched live price {symbol}: {entry_price}")
                
                    
                    

                stop_price = entry_price - atr
                take_profit_price = entry_price + 2 * atr
                stop_distance = entry_price - stop_price

                size = utils.calculate_position_size(capital=10000, risk_pct=0.01, stop_distance=atr)

                signal = generate_trade_signal(df)

                if signal == 'BUY':
                    size = utils.calculate_position_size(capital=10000, risk_pct=0.01, stop_distance=0.50)
                    bot.place_order(symbol, signal, size)  # pass as separate arguments
                else:
                    continue
            
                entry_price = bot.get_live_price(symbol)    
                if entry_price:
                    bot.place_bracket_order(symbol, signal, size, entry_price, stop_price, take_profit_price)

                #Wait before next ticker
                time.sleep(5)  # Small delay between tickers
                
            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")
                continue

        #Wait before next cycle
        time.sleep(60)  # adjust frequency as needed

   

def safe_place_order(self, symbol, action, quantity, limit_price=None, retries=3):
    for attempt in range(retries):
        trade = self.place_order(symbol, action, quantity, limit_price)
        if trade and trade.orderStatus.status in ['Filled', 'Submitted']:
            return trade
        print(f"🔁 Retry {attempt + 1} failed. Retrying...")
        self.ib.sleep(2)
    print("❌ All retries failed.")
    return None

def cancel_if_stale(self, trade, timeout=30):
    start = datetime.now()
    while (datetime.now() - start).seconds < timeout:
        if trade.orderStatus.status == 'Filled':
            return
        self.ib.sleep(1)
    self.ib.cancelOrder(trade.order)
    print("🧹 Stale order cancelled after timeout")




if __name__ == "__main__":

    
    utils = TradeUtils()
    bot = TradeEngine()
    live= live_data()
    
    #retry=  safe_place_order(symbol, action, quantity, limit_price)
    run_bot_all_day(bot, utils, live)