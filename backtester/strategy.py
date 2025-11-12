import pandas as pd
import backtrader as bt
from datetime import timedelta


import backtrader as bt

class MomentumBreakoutScalper(bt.Strategy):
    params = dict(
        ema_fast=2,
        ema_slow=5,
        rsi_period=7,
        rsi_thresh=50,
        volume_window=5,
        volume_multiplier=0.9,
        stop_loss_pct=0.002,  # 0.2%
        take_profit_pct=0.004 ,# 0.4%
        atr_period=14,
        atr_multiplier=2.5,
        cooldown_minutes=30,
        risk_per_trade=0.01
    )

    def __init__(self):
        print("Initializing MomentumBreakoutScalper Strategy")
        self.ema_fast = bt.ind.EMA(self.data.close, period=self.p.ema_fast)
        self.ema_slow = bt.ind.EMA(self.data.close, period=self.p.ema_slow)
        self.rsi = bt.ind.RSI(self.data.close, period=self.p.rsi_period)
        self.avg_volume = bt.ind.ATR(self.data, period=self.p.atr_period)
        self.order = None
        self.entry_price = None
        self.last_pnl = 0
        self.total_pnl = 0
        self.total_commission = 0
        self.last_trade_time = None
        self.atr = bt.ind.ATR(self.data, period=self.p.atr_period)

    def next(self):
        now = self.data.datetime.datetime(0)
        if self.last_pnl < 0 and self.last_trade_time:
            if (now - self.last_trade_time).total_seconds() <self.p.cooldown_minutes * 60:
                return  # skip entry after a loss

        if self.order:
            return  # wait for pending order
        
        # cooldown check
        if self.last_trade_time and (now - self.last_trade_time).total_seconds() < self.p.cooldown_minutes * 60:
            return  # in cooldown period

        breakout = self.data.close[0] > self.data.close[-1]
        momentum = self.ema_fast[0] > self.ema_slow[0] and (self.ema_fast[0] - self.ema_slow[0]) > 0.05
        rsi_ok = self.rsi[0] > 55
        volume_ok = self.data.volume[0] > self.avg_volume[0] * 1.1
        price_range = abs(self.data.close[0] - self.data.open[0])
        range_ok = price_range > self.atr[0] * 0.5
        
        #dynamic position sizing
        cash = self.broker.get_cash()
        risk_amount = cash * self.p.risk_per_trade
        stop_distance = self.atr[0] * self.p.atr_multiplier
        size = int(risk_amount / stop_distance)

           # entry logic
        if not self.position and (breakout and momentum and rsi_ok and volume_ok and range_ok):
            self.order = self.buy(size=size)
            self.entry_price = self.data.close[0]
            self.last_trade_time = now
            print(f"TIGHT BUY at {now} - {self.entry_price:.2f}")


        # exit logic
        elif self.position:
            stop_loss = self.entry_price - self.atr[0] * self.p.atr_multiplier
            take_profit = self.entry_price + self.atr[0] * self.p.atr_multiplier

            if self.data.close[0] < self.entry_price * 0.998 or self.data.close[0] > self.entry_price * 1.002:
                self.close()
                pnl = (self.data.close[0] - self.entry_price) * self.position.size
                self.total_pnl += pnl
                commission = self.broker.getcommissioninfo(self.data)._getcommission(self.position.size, self.data.close[0], True)
                self.total_commission += commission
                print(f"Total Commission Paid: {self.total_commission:.2f}")
                print(f"Trade PnL: {pnl:.2f}")
                print(f"Cumulative PnL: {self.total_pnl:.2f}")


                print(f"EXIT at {self.data.datetime.datetime(0)} - {self.data.close[0]:.2f}")

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None        