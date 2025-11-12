import logging
import os
from pathlib import Path

log_file = Path(__file__).parent.parent / "data files" / "trades.log"
os.makedirs(log_file.parent, exist_ok=True)

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_trade(symbol, side, quantity, price):
    message = f"Trade: {side} {quantity} shares of {symbol} at {price}"
    print(message)  # Also print to console for immediate feedback
    logging.info(message)
