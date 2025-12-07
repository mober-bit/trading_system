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
from prediction_model.model import predict_next_price

import time
from datetime import datetime, time as dtime





tickers=[]
pct_changes=[]
def spike_filter():
    
    mo=pd.read_csv(Path("prediction_model/price_predictions.csv"))
    item=0
    for stock,predicted in zip(mo['Stock'],mo['Predicted_Price']):
        item+=1
        print(f"Analyzing ticker {item} : {stock}")
        try:
            of=yf.download(stock, period="3d", interval="1d")
            last_close=of['Close'].iloc[-1].item()
            pct_change=((predicted- last_close)/last_close)*100
            print(f"Pct Change={pct_change}%")
            pct_changes.append({'Stock': stock, 'Pct_Change': pct_change})
            if of.empty:
                print(f"Warning: No data found for {stock}. Skipping.")
                continue
        except Exception as e:
            print(f"Error fetching data for {stock}: {e}")

        Pct_Change=pd.DataFrame(pct_changes,columns=['Stock','Pct_Change'])
        pct_sorted=Pct_Change.sort_values(by='Pct_Change',ascending=False)
        pct_sorted.to_csv(Path("prediction_model/price_directions_sorted.csv"),index=False)    
   
def final_filter():
    cf=pd.read_csv(Path("prediction_model/price_directions_sorted.csv"))
    tickers.extend(cf['Stock'].head(49).to_list())
    
    
def is_market_open():
    now = datetime.now().time()
    return dtime(9, 30) <= now <= dtime(16, 0)  # US market hours (ET)


def run_bot_all_day(bot, utils,live):
    predict_next_price()  # takes about 30 minutes to run through all tickers
    spike_filter() # takes also about 30 minutes to run through all tickers
    final_filter()  
    live.live_data_websocket()
    print("🚀 Starting trading loop...")
    load_dotenv()
    token = os.getenv("fintoken")


    print("🔌 IB connected:", bot.ib.isConnected())

    while True:
        
        if not is_market_open():
            print("⏳ Market closed. Sleeping...")
            time.sleep(10)
            continue

        if utils.is_cooldown_active():
            print("🕒 Cooldown active, skipping this cycle")
            time.sleep(10)
            continue

        

       
        for symbol in tickers:
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
                
                    print(f"⚠️ ATR too low for {symbol} ({atr:.2f}), skipping")
                    continue

                 

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
                print(f"📈 Signal for {symbol}: {signal}")


                if signal == 'BUY':
                    size = utils.calculate_position_size(capital=10000, risk_pct=0.01, stop_distance=0.50)
                    entry_price = bot.get_live_price(symbol) 
                    bot.place_bracket_order(symbol, signal, size, entry_price, stop_price, take_profit_price)
    
                
            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")
                continue

       



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