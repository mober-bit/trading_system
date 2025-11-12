import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import backtrader as bt
from bot.trade_engine import TradeUtils

def generate_trade_signal(df, params=None):
    if params is None:
        params = dict(
            ema_fast=2,
            ema_slow=5,
            rsi_period=7,
            rsi_thresh=55,
            volume_window=5,
            volume_multiplier=1.1,
            atr_period=14,
            atr_range_factor=0.5
        )

    if len(df) < max(params['ema_slow'], params['rsi_period'], params['volume_window'], params['atr_period']):
        return None  # not enough data

    close = df['close']
    open_ = df['open']
    volume = df['volume']

    ema_fast = close.ewm(span=params['ema_fast']).mean().iloc[-1]
    ema_slow = close.ewm(span=params['ema_slow']).mean().iloc[-1]
    rsi = compute_rsi(close, period=params['rsi_period']).iloc[-1]
    avg_volume = volume.rolling(params['volume_window']).mean().iloc[-1]
    atr = TradeUtils.calculate_atr(df, period=params['atr_period'])

    breakout = close.iloc[-1] > close.iloc[-2]
    momentum = ema_fast > ema_slow and (ema_fast - ema_slow) > 0.05
    rsi_ok = rsi > params['rsi_thresh']
    volume_ok = volume.iloc[-1] > avg_volume * params['volume_multiplier']
    range_ok = abs(close.iloc[-1] - open_.iloc[-1]) > atr * params['atr_range_factor']

    if breakout and momentum and rsi_ok and volume_ok and range_ok:
        return 'BUY'
    else:
        return None

def compute_rsi(series, period=7):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))



def calculate_position_size(cash, atr, atr_multiplier, risk_pct):
    stop_distance = atr * atr_multiplier
    risk_amount = cash * risk_pct
    return int(risk_amount / stop_distance)
