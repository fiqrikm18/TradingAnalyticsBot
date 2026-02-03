import os
import requests
import json
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import math
import time
from datetime import datetime

import consts

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = consts.DISCORD_WEBHOOK_Result

STOCK_LIST_FILE = consts.STOCK_LIST_FILE
BACKTEST_FILE = consts.BACKTEST_FILE

# SETTINGS
MIN_WIN_RATE = 70.0
MIN_TRADES = 8
CAPITAL_IDR = consts.CAPITAL_IDR
RISK_PCT = consts.RISK_PCT

stock_stats = {}


def load_tickers_with_filter(filename, backtest_csv):
    if not os.path.exists(filename):
        print(f"❌ Error: {filename} not found.")
        return []

    try:
        if filename.endswith('.xlsx'):
            df_master = pd.read_excel(filename)
        else:
            df_master = pd.read_csv(filename)
        df_master.columns = df_master.columns.str.strip()
    except Exception as e:
        print(f"❌ Read Error: {e}")
        return []

    valid_boards = ['Main', 'Development', 'Ekonomi Baru']
    if 'Listing Board' in df_master.columns:
        df_master = df_master[df_master['Listing Board'].isin(valid_boards)]

    if 'Code' not in df_master.columns:
        return []
    all_tickers = [str(code) + ".JK" for code in df_master['Code'].tolist()]

    if os.path.exists(backtest_csv):
        try:
            df_bt = pd.read_csv(backtest_csv)
            good_stocks = df_bt[(df_bt['WinRate'] >= MIN_WIN_RATE) & (
                df_bt['Trades'] >= MIN_TRADES)]
            for _, row in good_stocks.iterrows():
                stock_stats[row['Ticker']] = {
                    'wr': row['WinRate'], 'roi': row['ROI'], 'dd': row['MaxDD']}
            good_tickers = good_stocks['Ticker'].tolist()
            final_list = [t for t in all_tickers if t in good_tickers]
            print(f"🧠 Filter: {len(final_list)} Active Stocks")
            return final_list
        except:
            return all_tickers
    else:
        return all_tickers


def get_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="2y", interval="1d")
        if df.empty:
            return None
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        df.ta.stochrsi(length=14, rsi_length=14, k=3, d=3, append=True)
        df.ta.adx(length=14, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df['VOL_SMA_20'] = df['Volume'].rolling(window=20).mean()
        return df
    except:
        return None


def calculate_fibonacci(df, lookback=120):
    recent = df.tail(lookback)
    high = float(recent['High'].max())
    low = float(recent['Low'].min())
    diff = high - low
    return {'0.0': high, '0.5': high - 0.5 * diff, '0.618': high - 0.618 * diff, '0.786': high - 0.786 * diff}


def analyze_market_structure(close, sma200, ema50, adx):
    trend = "Unknown"
    strength = "Weak"
    if close > sma200:
        if close > ema50:
            trend = "Strong Uptrend"
        else:
            trend = "Uptrend (Deep Pullback)"
    else:
        if close > ema50:
            trend = "Recovery Attempt"
        else:
            trend = "Downtrend"
    if adx > 25:
        strength = "Strong"
    return trend, strength


def strategy_deep_dive(df, ticker):
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    close = float(curr['Close'])
    vol = float(curr['Volume'])
    vol_ma = float(curr.get('VOL_SMA_20', vol))

    sma200 = float(curr['SMA_200'])
    ema50 = float(curr['EMA_50'])
    adx = float(curr['ADX_14'])
    rsi = float(curr['RSI_14'])

    k_curr = float(curr['STOCHRSIk_14_14_3_3'])
    d_curr = float(curr['STOCHRSId_14_14_3_3'])
    k_prev = float(prev['STOCHRSIk_14_14_3_3'])
    d_prev = float(prev['STOCHRSId_14_14_3_3'])

    macd_val = float(curr.get('MACD_12_26_9', 0))
    fib = calculate_fibonacci(df)

    score = 0
    reasons = []
    warnings = []

    # 1. Trend
    trend_desc, trend_strength = analyze_market_structure(
        close, sma200, ema50, adx)
    if close > sma200 or close > ema50:
        score += 20
    else:
        warnings.append("Weak Trend")

    # 2. Momentum
    stoch_cross = (k_curr > d_curr) and (k_prev < d_prev) and (k_curr < 50)
    if stoch_cross:
        score += 30
        reasons.append(f"Stoch Momentum ({k_curr:.0f})")

    if macd_val > 0:
        score += 10

    # 3. Volume
    vol_str = "Normal"
    if vol_ma > 0:
        ratio = vol / vol_ma
        vol_str = f"{ratio:.1f}x"
        if ratio > 1.0:
            score += 10
            reasons.append(f"Vol > Avg")

    # 4. Zone
    dist_fib = abs(close - fib['0.618']) / close
    if dist_fib < 0.15:
        score += 30
        reasons.append("In Value Zone")

    # Signal
    signal = "WAIT"
    if stoch_cross and (score >= 40):
        signal = "⚡ AGGRESSIVE BUY"
        if score >= 70:
            signal = "💎 DIAMOND SETUP"

    # Execution
    entry_price = close
    tp_price = fib['0.0']
    sl_price = fib['0.786']

    risk_per_share = entry_price - sl_price
    if risk_per_share <= 0:
        risk_per_share = entry_price * 0.05

    max_loss_rp = CAPITAL_IDR * RISK_PCT
    lots = math.floor(max_loss_rp / risk_per_share / 100)

    capital_req = lots * 100 * entry_price
    potential_profit = (tp_price - entry_price) * lots * 100
    potential_loss = (sl_price - entry_price) * lots * 100
    rrr = (tp_price - entry_price) / \
        risk_per_share if risk_per_share > 0 else 0

    # Risk Metrics
    sl_pct = (risk_per_share / entry_price) * 100
    risk_per_lot = risk_per_share * 100
    be_trigger = entry_price + risk_per_share

    return {
        "ticker": ticker,
        "signal": signal,
        "score": score,
        "entry": entry_price,
        "tp": tp_price,
        "sl": sl_price,
        "lots": lots,
        "capital_req": capital_req,
        "pnl": {"win": potential_profit, "loss": potential_loss},
        "rrr": round(rrr, 2),
        "risk_mgmt": {
            "sl_pct": sl_pct,
            "risk_lot": risk_per_lot,
            "be_trigger": be_trigger
        },
        "thesis": {
            "trend": trend_desc,
            "strength": f"{adx:.1f} ({trend_strength})",
            "volume": vol_str,
            "rsi": f"{rsi:.1f}",
            "reasons": reasons,
            "warnings": warnings
        },
        "fib": fib
    }


def generate_chart(df, ticker, data):
    mc = mpf.make_marketcolors(up='#2ebd85', down='#f6465d', inherit=True)
    s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)
    ap_stoch = mpf.make_addplot(
        df['STOCHRSIk_14_14_3_3'], panel=1, color='cyan', ylabel='Stoch')
    ap_sma = mpf.make_addplot(df['SMA_200'], color='gold', width=1.5)
    fib = data['fib']
    hlines = [data['entry'], data['tp'], data['sl'], fib['0.618']]
    colors = ['white', 'green', 'red', 'lime']
    filename = f"chart_{ticker}.png"
    try:
        mpf.plot(df, type='candle', style=s, title=f"{ticker} - Analysis", ylabel='IDR',
                 addplot=[ap_stoch, ap_sma],
                 hlines=dict(hlines=hlines, colors=colors,
                             linewidths=[1]*4, linestyle='dashed'),
                 volume=False, savefig=dict(fname=filename, dpi=100, pad_inches=0.25))
    except:
        return None
    return filename


def send_discord_alert(data, chart_path):
    if "WAIT" in data['signal']:
        return
    color = 3066993 if data['score'] >= 70 else 3447003

    thesis = data['thesis']
    risk = data['risk_mgmt']
    reasons_list = "\n".join([f"✅ {r}" for r in thesis['reasons']])
    warnings_list = "\n".join(
        [f"⚠️ {w}" for w in thesis['warnings']]) if thesis['warnings'] else "No Warnings"

    hist_stats = stock_stats.get(data['ticker'], None)
    backtest_info = f"🏆 **WR:** `{hist_stats['wr']:.0f}%` | 📉 **DD:** `{hist_stats['dd']:.1f}%`" if hist_stats else "🆕 *Unfiltered*"

    embed = {
        "username": "Risk Manager Bot",
        "embeds": [{
            "title": f"{data['signal']} : {data['ticker']}",
            "description": f"**Score:** `{data['score']}/100`\n**Thesis:** {thesis['trend']}\n{reasons_list}",
            "color": color,
            "fields": [
                {
                    "name": "📊 Market Data",
                    "value": f"**Vol:** {thesis['volume']}\n**RSI:** {thesis['rsi']}\n{backtest_info}",
                    "inline": True
                },
                {
                    "name": "💰 Financials (Risk 2%)",
                    # ADDED LOT RECOMMENDATION HERE
                    "value": f"**Rec. Lots:** `{data['lots']}`\n**Capital:** `Rp {data['capital_req']:,.0f}`\n**Max Loss:** `Rp {data['pnl']['loss']:,.0f}`",
                    "inline": True
                },
                {
                    "name": "🛡️ RISK MANAGEMENT PLAN",
                    "value": (
                        f"🔴 **Stop Loss:** `{data['sl']:,.0f}` (**-{risk['sl_pct']:.1f}%**)\n"
                        f"🟢 **R:R Ratio:** `1 : {data['rrr']}`\n"
                        f"⚠️ **Risk per Lot:** `Rp -{risk['risk_lot']:,.0f}`\n"
                        f"🛡️ **Move to Break Even:** @ `{risk['be_trigger']:,.0f}`"
                    ),
                    "inline": False
                },
                {
                    "name": "🚪 Execution",
                    "value": f"**ENTRY (Market):** `{data['entry']:,.0f}`\n**TP (High):** `{data['tp']:,.0f}`",
                    "inline": True
                }
            ],
            "footer": {"text": f"Scanned at {datetime.now().strftime('%H:%M')}"}
        }]
    }
    if chart_path and os.path.exists(chart_path):
        with open(chart_path, "rb") as f:
            requests.post(DISCORD_WEBHOOK_URL, data={
                          "payload_json": json.dumps(embed)}, files={"file": f})
    else:
        requests.post(DISCORD_WEBHOOK_URL, data={
                      "payload_json": json.dumps(embed)})


def run_bot():
    print("🚀 Starting Risk-Aware Scanner...")
    tickers = load_tickers_with_filter(STOCK_LIST_FILE, BACKTEST_FILE)
    if not tickers:
        return
    print(f"🔎 Scanning {len(tickers)} stocks... (Ctrl+C to stop)")
    hits = 0
    for idx, ticker in enumerate(tickers):
        print(f"   [{idx+1}/{len(tickers)}] {ticker}...", end="\r")
        try:
            df = get_data(ticker)
            if df is None:
                continue
            strat = strategy_deep_dive(df, ticker)
            if "BUY" in strat['signal'] or "SETUP" in strat['signal']:
                print(f"\n✨ ANALYSIS: {ticker} -> Score: {strat['score']}")
                chart_file = generate_chart(df.tail(150), ticker, strat)
                send_discord_alert(strat, chart_file)
                if chart_file and os.path.exists(chart_file):
                    os.remove(chart_file)
                hits += 1
                time.sleep(2)
        except Exception as e:
            continue

    print(f"\n✅ Scan Complete. Sent {hits} detailed reports.")


if __name__ == "__main__":
    run_bot()
