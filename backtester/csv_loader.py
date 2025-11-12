import pandas as pd
from pathlib import Path

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=['date'])
    df.columns=[c.lower() for c in df.columns]
    rename_map = { 'timestamp': 'date', 'datetime': 'date',
        'open_price': 'open', 'high_price': 'high',
        'low_price': 'low', 'close_price': 'close'}
    df = df.rename(columns=rename_map)
    df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
    df= df.dropna().sort_values('date').reset_index(drop=True)  
    return df