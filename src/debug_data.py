from services import market_data
import pandas as pd

ticker = "BBCA.JK"
print(f"Fetching {ticker}...")
df = market_data.get_market_data(ticker)

if df is None:
    print("DF IS NONE")
else:
    print(f"Shape: {df.shape}")
    print(df.tail())
    print(df.head())
