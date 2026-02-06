from config.settings import STOCK_LIST_FILE, MODEL_PATH, LOOKBACK_DAYS
from services import market_data, technical_analysis, ai_engine
import sys
import os
import logging
import random
import pandas as pd
import numpy as np
import tensorflow as tf
from concurrent.futures import ThreadPoolExecutor

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


# Config
TEST_DAYS = 365  # Look back 1 year
SIMULATION_TICKS = 20  # Simulate trading on 20 random stocks
AI_THRESHOLD = 0.75

logging.basicConfig(level=logging.INFO, format='%(message)s')


def run_simulation(ticker, model):
    """Simulates trading on a single stock over the past year."""
    try:
        # Get long history
        df = market_data.get_market_data(ticker, period="2y")
        if df is None:
            # print(f"Skipping {ticker}: No Data")
            return None

        if len(df) < (TEST_DAYS + LOOKBACK_DAYS):
            # print(f"Skipping {ticker}: Not enough data ({len(df)} rows)")
            return None

        # Slice simulation period
        sim_data = df.iloc[-(TEST_DAYS + LOOKBACK_DAYS):]

        capital = 10000000  # 10 Million IDR
        balance = capital
        full_log = []
        trades = []
        in_position = False
        entry_price = 0
        entry_date = None
        stop_loss = 0
        target_price = 0

        # print(f"[{ticker}] Data OK. Simulating {len(sim_data)-LOOKBACK_DAYS} days...")

        # Iterate day by day
        for i in range(LOOKBACK_DAYS, len(sim_data)):
            current_date = sim_data.index[i]
            current_close = sim_data['Close'].iloc[i]

            # Update Position
            if in_position:
                # Check Exit
                if current_close <= stop_loss:
                    pnl = (current_close - entry_price)/entry_price
                    params = {'exit': current_close, 'result': 'LOSS',
                              'pnl': pnl}
                    trades.append(params)
                    balance = balance * (1 + params['pnl'])
                    in_position = False
                    # print(f"  [{ticker}] SELL LOSS: {pnl:.2%}")
                elif current_close >= target_price:
                    pnl = (current_close - entry_price)/entry_price
                    params = {'exit': current_close, 'result': 'WIN',
                              'pnl': pnl}
                    trades.append(params)
                    balance = balance * (1 + params['pnl'])
                    in_position = False
                    # print(f"  [{ticker}] SELL WIN: {pnl:.2%}")
                continue

            # Check Entry
            # 1. Prepare Window
            window = sim_data.iloc[i-LOOKBACK_DAYS:i]

            # 2. Tech Filters
            passed, reason, filters = technical_analysis.check_filters(window)
            if not passed:
                continue

            # 3. AI Score
            score = ai_engine.get_lstm_score(model, window)

            if score >= AI_THRESHOLD:
                # BUY SIGNAL
                setup = technical_analysis.calculate_trade_setup(window)
                in_position = True
                entry_price = current_close
                entry_date = current_date
                stop_loss = setup['sl']
                target_price = setup['tp']
                # print(f"  [{ticker}] BUY @ {entry_price} (Score: {score:.2f})")

        # Stats
        wins = len([t for t in trades if t['result'] == 'WIN'])
        losses = len([t for t in trades if t['result'] == 'LOSS'])
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        final_return = (balance - capital) / capital * 100

        return {
            'ticker': ticker,
            'trades': total,
            'win_rate': win_rate,
            'return': final_return
        }

    except Exception as e:
        # print(f"Error {ticker}: {e}")
        return None


def main():
    print(f"🚀 Starting Backtest Simulation (Threshold {AI_THRESHOLD})...")

    # Load Model
    model = ai_engine.load_model()
    if not model:
        print("Error: Model not found. Train it first using src/main.py")
        return

    # Load Tickers
    tickers = market_data.load_tickers(STOCK_LIST_FILE)
    if not tickers:
        print("Error: No tickers found.")
        return

    # Select Random Sample (Prioritize known good stocks for verification)
    sample = random.sample(tickers, min(len(tickers), SIMULATION_TICKS))

    print(f"Testing on {len(sample)} stocks over past {TEST_DAYS} days...")

    results = []
    for ticker in sample:
        print(f"Testing {ticker}...", end="\r")
        res = run_simulation(ticker, model)
        if res:
            results.append(res)

    print("\n\n📊 SIMULATION RESULTS")
    print("="*40)
    print(f"{'Ticker':<10} {'Trades':<8} {'Win Rate':<10} {'Return':<10}")
    print("-" * 40)

    avg_win = []
    avg_ret = []

    for r in results:
        print(
            f"{r['ticker']:<10} {r['trades']:<8} {r['win_rate']:.1f}%      {r['return']:.1f}%")
        if r['trades'] > 0:
            avg_win.append(r['win_rate'])
            avg_ret.append(r['return'])

    print("="*40)
    if avg_win:
        print(f"Overall Win Rate: {np.mean(avg_win):.1f}%")
        print(f"Overall Return:   {np.mean(avg_ret):.1f}%")
    else:
        print("No trades triggered.")


if __name__ == "__main__":
    main()
