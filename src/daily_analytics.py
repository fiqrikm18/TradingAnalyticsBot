import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import os
import requests
import json
import time
from datetime import datetime
import consts

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = consts.DISCORD_WEBHOOK_Daily
STOCK_LIST_FILE = consts.STOCK_LIST_FILE


def load_tickers(filename):
    if not os.path.exists(filename):
        return []
    try:
        if filename.endswith('.xlsx'):
            df = pd.read_excel(filename)
        else:
            df = pd.read_csv(filename)
        df.columns = df.columns.str.strip()

        valid_boards = ['Main', 'Development', 'Ekonomi Baru']
        if 'Listing Board' in df.columns:
            df = df[df['Listing Board'].isin(valid_boards)]

        # Create a Dictionary for {Code: Name} mapping
        return {str(row['Code'])+".JK": str(row['Company Name']) for _, row in df.iterrows()}
    except:
        return {}


def get_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1y", interval="1d")
        if df.empty or len(df) < 50:
            return None
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Basic Indicators
        df.ta.sma(length=200, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)

        # Volume MA
        df['VOL_SMA_20'] = df['Volume'].rolling(window=20).mean()

        return df
    except:
        return None


def analyze_market_health(ticker_dict):
    print(f"📊 Analyzing Market Health ({len(ticker_dict)} stocks)...")

    stats = {
        'total': 0,
        'uptrend': 0,    # Above SMA200
        'downtrend': 0,  # Below SMA200
        'oversold': 0,   # RSI < 30
        'overbought': 0,  # RSI > 70
        'vol_spike': [],  # List of tickers with 3x Volume
        'squeeze': [],   # Bollinger Band Squeeze
        'watchlist': []  # Near EMA50 Support
    }

    processed = 0
    for ticker, name in ticker_dict.items():
        print(f"   Scanning {ticker}...", end="\r")
        df = get_data(ticker)
        if df is None:
            continue

        curr = df.iloc[-1]
        close = curr['Close']
        sma200 = curr.get('SMA_200', 0)
        ema50 = curr.get('EMA_50', 0)
        rsi = curr.get('RSI_14', 50)
        vol = curr['Volume']
        vol_ma = curr.get('VOL_SMA_20', 0)

        # Bandwidth for Squeeze
        bbu = curr.get('BBU_20_2.0', 0)
        bbl = curr.get('BBL_20_2.0', 0)
        bandwidth = (bbu - bbl) / sma200 if sma200 > 0 else 0

        # 1. Trend Stats
        stats['total'] += 1
        if close > sma200:
            stats['uptrend'] += 1
        else:
            stats['downtrend'] += 1

        # 2. RSI Extremes
        if rsi < 30:
            stats['oversold'] += 1
        elif rsi > 70:
            stats['overbought'] += 1

        # 3. Volume Spikes (> 3x Average)
        if vol_ma > 0 and (vol / vol_ma) > 3.0:
            ratio = vol / vol_ma
            stats['vol_spike'].append((ticker, ratio))

        # 4. Volatility Squeeze (Bandwidth < 5%)
        if bandwidth < 0.05 and bandwidth > 0:
            stats['squeeze'].append(ticker)

        # 5. "On Radar" (Pullback near EMA50 in Uptrend)
        # Price is above SMA200, but dropped near EMA50 (within 2%)
        if close > sma200 and abs(close - ema50)/close < 0.02:
            stats['watchlist'].append(ticker)

        processed += 1

    print("\n✅ Analysis Complete.")
    return stats


def send_daily_brief(stats):
    if stats['total'] == 0:
        return

    # Calculate Market Breadth
    bullish_pct = (stats['uptrend'] / stats['total']) * 100
    bearish_pct = (stats['downtrend'] / stats['total']) * 100
    sentiment = "🐂 BULLISH" if bullish_pct > 50 else "🐻 BEARISH"
    color = 65280 if bullish_pct > 50 else 16711680

    # Format Lists
    top_vol = sorted(stats['vol_spike'], key=lambda x: x[1], reverse=True)[:5]
    vol_str = "\n".join(
        [f"**{t[0]}** (`{t[1]:.1f}x`)" for t in top_vol]) if top_vol else "None"

    squeeze_str = ", ".join(
        stats['squeeze'][:8]) if stats['squeeze'] else "None"
    watch_str = ", ".join(stats['watchlist'][:8]
                          ) if stats['watchlist'] else "None"

    embed = {
        "username": "Market Chief",
        "embeds": [{
            "title": f"📅 Daily Market Brief | {datetime.now().strftime('%d %b %Y')}",
            "description": f"**Market Sentiment:** {sentiment}\nAnalyzing **{stats['total']}** liquid stocks.",
            "color": color,
            "fields": [
                {
                    "name": "📊 Market Breadth",
                    "value": f"📈 **Uptrend:** `{bullish_pct:.1f}%`\n📉 **Downtrend:** `{bearish_pct:.1f}%`\n🧊 **Oversold:** `{stats['oversold']}` stocks",
                    "inline": True
                },
                {
                    "name": "📢 Volume Anomalies (Institutions?)",
                    "value": vol_str,
                    "inline": True
                },
                {
                    "name": "💥 Volatility Squeeze (Ready to Move)",
                    "value": f"*{squeeze_str}*",
                    "inline": False
                },
                {
                    "name": "👀 Watchlist (Near EMA50 Support)",
                    "value": f"**{watch_str}**",
                    "inline": False
                }
            ],
            "footer": {"text": "Generated by Alpha Quant Analytics"}
        }]
    }

    requests.post(DISCORD_WEBHOOK_URL, data={
                  "payload_json": json.dumps(embed)})


if __name__ == "__main__":
    print("🌅 Starting Daily Analytics...")
    tickers = load_tickers(STOCK_LIST_FILE)
    if tickers:
        data_stats = analyze_market_health(tickers)
        send_daily_brief(data_stats)
    else:
        print("❌ Ticker load failed.")
