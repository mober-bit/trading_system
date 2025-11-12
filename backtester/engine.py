import pandas as pd
import matplotlib.pyplot as plt
import os
from pathlib import Path
from datetime import datetime
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import backtrader as bt
from backtester.csv_loader import load_csv
from backtester.strategy import MomentumBreakoutScalper

class IBKRCommission(bt.CommInfoBase):
    params = (
        ('commission', 0.005),  # $0.005 per share
        ('min_commission', 1.0),  # $1 minimum per order
    )

    def _getcommission(self, size, price, pseudoexec):
        cost = abs(size) * self.p.commission
        return max(cost, self.p.min_commission)


def backtest( ):
    symbol = input("Enter stock symbol for backtest: ")
    df=load_csv(Path("data files") / "data" / f"{symbol}_intraday.csv")
    data = bt.feeds.PandasData(dataname=df, datetime='date', open='open', high='high', low='low', close='close', volume='volume')
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(MomentumBreakoutScalper)
    cerebro.broker.setcash(1000.0)
    cerebro.broker.addcommissioninfo(IBKRCommission())
    cerebro.run()
    cerebro.plot()
    return [], pd.DataFrame()  # Placeholder for trades and performance DataFrame



backtest()