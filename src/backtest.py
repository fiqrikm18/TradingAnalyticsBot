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
FILE_FILENAME = consts.STOCK_LIST_FILE
DISCORD_WEBHOOK_URL = consts.DISCORD_WEBHOOK_Backtest

INITIAL_CAPITAL = consts.CAPITAL_IDR
RISK_PCT = consts.RISK_PCT


def load_tickers(filename):
    print(f"📂 Loading tickers from {filename}...")
    if not os.path.exists(filename):
        print(f"❌ Error: File '{filename}' not found.")
        return []

    try:
        if filename.endswith('.xlsx'):
            df = pd.read_excel(filename)
        else:
            df = pd.read_csv(filename)
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"❌ Read Error: {e}")
        return []

    valid_boards = ['Main', 'Development', 'Ekonomi Baru']
    if 'Listing Board' in df.columns:
        df_clean = df[df['Listing Board'].isin(valid_boards)]
    else:
        df_clean = df

    if 'Code' not in df_clean.columns:
        return []
    return [str(code) + ".JK" for code in df_clean['Code'].tolist()]


def get_data(ticker):
    try:
        df = yf.Ticker(ticker).history(
            period="3y", interval="1d", auto_adjust=True)
        if df.empty or len(df) < 200:
            return None
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        df.ta.stochrsi(length=14, rsi_length=14, k=3, d=3, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.adx(length=14, append=True)
        return df
    except:
        return None


def run_simulation(df):
    capital = INITIAL_CAPITAL
    trades = []
    active_trade = None
    peak_capital = capital
    max_drawdown = 0

    for i in range(200, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]

        if capital > peak_capital:
            peak_capital = capital
        dd = (peak_capital - capital) / peak_capital
        if dd > max_drawdown:
            max_drawdown = dd

        if active_trade:
            if curr['Low'] <= active_trade['sl']:
                pnl = (active_trade['sl'] - active_trade['entry']
                       ) * active_trade['shares']
                capital += pnl
                trades.append({'Result': 'LOSS', 'PnL': pnl})
                active_trade = None
            elif curr['High'] >= active_trade['tp']:
                pnl = (active_trade['tp'] - active_trade['entry']
                       ) * active_trade['shares']
                capital += pnl
                trades.append({'Result': 'WIN', 'PnL': pnl})
                active_trade = None
            continue

        past_window = df.iloc[i-120:i]
        if past_window.empty:
            continue
        high = past_window['High'].max()
        low = past_window['Low'].min()
        diff = high - low
        if diff == 0:
            continue

        fib = {'0.0': high, '0.5': high - 0.5 * diff, '0.618': high -
               0.618 * diff, '0.786': high - 0.786 * diff}

        k_curr = curr.get('STOCHRSIk_14_14_3_3', 0)
        d_curr = curr.get('STOCHRSId_14_14_3_3', 0)
        k_prev = prev.get('STOCHRSIk_14_14_3_3', 0)
        d_prev = prev.get('STOCHRSId_14_14_3_3', 0)
        sma200 = curr.get('SMA_200', 0)
        ema50 = curr.get('EMA_50', 0)
        close = curr['Close']

        trigger_stoch = (k_curr > d_curr) and (
            k_prev < d_prev) and (k_curr < 50)
        is_uptrend = (close > sma200) or (close > ema50)
        in_zone = (close >= fib['0.618'] *
                   0.85) and (close <= fib['0.5'] * 1.15)

        if trigger_stoch and is_uptrend and in_zone:
            entry_price = close
            sl = fib['0.786']
            tp = fib['0.0']

            risk = entry_price - sl
            if risk <= 0:
                continue

            risk_amt = capital * RISK_PCT
            shares = int(risk_amt / risk)
            if shares * entry_price > capital:
                shares = int(capital / entry_price)

            if shares > 0:
                active_trade = {'entry': entry_price,
                                'sl': sl, 'tp': tp, 'shares': shares}

    return {'Profit': capital - INITIAL_CAPITAL, 'Trades': len(trades), 'Wins': len([t for t in trades if t['Result'] == 'WIN']), 'DD': max_drawdown * 100}


def send_discord_report(csv_file, total_tested):
    if not os.path.exists(csv_file):
        return
    df = pd.read_csv(csv_file)
    if df.empty:
        return

    profitable = len(df[df['Profit'] > 0])
    avg_trades = df['Trades'].mean() if not df.empty else 0

    # --- FORMATTING MENJADI TABEL ---
    top_header = f"{'TICKER':<10} | {'FREQ':<5} | {'WIN%':<5} | {'ROI':<6}"
    top_str = top_header + "\n" + "-"*35 + "\n"

    sorted_df = df.sort_values(by='Trades', ascending=False).head(10)
    for _, row in sorted_df.iterrows():
        ticker_clean = row['Ticker'].replace('.JK', '')
        top_str += f"{ticker_clean:<10} | {row['Trades']:<5} | {row['WinRate']:<5.0f} | {row['ROI']:<6.1f}%\n"

    embed = {
        "username": "Backtest Engine",
        "embeds": [{
            "title": "🧪 Laporan Backtest (Max Frequency)",
            "description": f"Analisa selesai pada **{total_tested}** saham.",
            "color": 3447003,
            "fields": [
                {"name": "📈 Statistik Global",
                    "value": f"✅ Saham Profit: **{profitable}**\n🔄 Rata-rata Trade: **{avg_trades:.1f}x / saham**", "inline": False},
                {"name": "🏆 Top 10 Teraktif",
                    "value": f"```prolog\n{top_str}```", "inline": False}
            ],
            "footer": {"text": "Mode Agresif: Stoch < 50, Zone Lebar 15%"}
        }]
    }
    try:
        with open(csv_file, "rb") as f:
            requests.post(DISCORD_WEBHOOK_URL, data={
                          "payload_json": json.dumps(embed)}, files={"file": f})
    except:
        pass


if __name__ == "__main__":
    tickers = load_tickers(FILE_FILENAME)
    if not tickers:
        print("❌ Stopped.")
    else:
        print(f"🚀 Starting AGGRESSIVE Backtest on {len(tickers)} stocks...")
        csv_file = "backtest_results.csv"
        with open(csv_file, "w") as f:
            f.write("Ticker,Trades,WinRate,Profit,ROI,MaxDD\n")

        for idx, ticker in enumerate(tickers):
            print(f"   [{idx+1}/{len(tickers)}] Testing {ticker}...", end="\r")
            try:
                df = get_data(ticker)
                if df is not None:
                    res = run_simulation(df)
                    wr = (res['Wins']/res['Trades'] *
                          100) if res['Trades'] > 0 else 0
                    roi = (res['Profit']/INITIAL_CAPITAL)*100
                    with open(csv_file, "a") as f:
                        f.write(
                            f"{ticker},{res['Trades']},{wr:.1f},{res['Profit']:.0f},{roi:.1f},{res['DD']:.1f}\n")
            except:
                continue
        print("\n✅ Backtest Complete.")
        send_discord_report(csv_file, len(tickers))
