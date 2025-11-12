# main.py
import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backtester.csv_loader import load_csv

from data.vantage_loader import ingest_data

def main():
    symbol = input("Enter stock symbol: ")
    # Define a consistent base path for data files
    data_base_path = Path("data files") / "data"

    ingest_data(symbol)
    # 1. Load data
    df = load_csv(data_base_path / f"{symbol}_intraday.csv")

   
    
    


if __name__ == "__main__":
    main()
