import logging
import pandas as pd
import yfinance as yf
from config.settings import LOOKBACK_DAYS


def load_tickers(file_path):
    """Loads ticker symbols from an Excel file."""
    try:
        df = pd.read_excel(file_path)
        tickers = []
        for t in df['Code'].astype(str):
            t = t.strip().upper()
            if not t:
                continue
            if not t.endswith('.JK'):
                t = f"{t}.JK"
            tickers.append(t)
        return tickers
    except Exception as e:
        print(f"❌ Error loading tickers: {e}")
        return []


def get_market_data(ticker, period="6mo"):
    """Fetches historical market data including OBV."""
    try:
        stock = yf.Ticker(ticker)
        # Fetch requested period
        history = stock.history(period=period)

        if len(history) < LOOKBACK_DAYS:
            return None

        # Clean data
        df = history[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

        # Calculate OBV (On-Balance Volume)
        df['OBV'] = (
            (df['Close'] > df['Close'].shift(1)).astype(int) * df['Volume'] +
            (df['Close'] < df['Close'].shift(1)).astype(int) * -df['Volume']
        ).cumsum()

        # Calculate SMA (20-day)
        df['SMA20'] = df['Close'].rolling(window=20).mean()

        df.dropna(inplace=True)
        return df

    except Exception as e:
        logging.error(f"Error fetching data for {ticker}: {e}")
        return None


def get_fundamentals(ticker):
    """Fetches basic fundamental data."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "mcap": f"{info.get('marketCap', 0)/1e9:,.0f} B",
            "per": info.get('trailingPE', 0),
            "pbv": info.get('priceToBook', 0),
            "roe": info.get('returnOnEquity', 0)
        }
    except:
        return {"mcap": "N/A", "per": 0, "pbv": 0, "roe": 0}
