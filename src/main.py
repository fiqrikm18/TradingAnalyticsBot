import sys
import logging
import time
import os
from datetime import datetime

# Services
from services import market_data, technical_analysis, ai_engine, charting, notification
from config.settings import STOCK_LIST_FILE, RETRAIN_INTERVAL_DAYS
import database as database
from database import Stock, ScreenerResult

# Configure Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def check_model_freshness():
    """Returns True if model needs retraining (older than RETRAIN_INTERVAL_DAYS)."""
    if not os.path.exists(ai_engine.MODEL_PATH):
        return True  # Missing model needs training

    try:
        file_time = datetime.fromtimestamp(
            os.path.getmtime(ai_engine.MODEL_PATH))
        age = datetime.now() - file_time
        if age.days >= RETRAIN_INTERVAL_DAYS:
            print(
                f"⚠️ Model expired ({age.days} days old > {RETRAIN_INTERVAL_DAYS} days). Retraining...")
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking model freshness: {e}")
        return True


def save_scan_result_to_db(ticker, score, filters):
    """Saves the scan result to the database."""
    db_gen = database.get_db()
    db = next(db_gen, None)

    if not db:
        return

    try:
        # Ensure Stock exists
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            stock = Stock(ticker=ticker, name=ticker, sector="Unknown")
            db.add(stock)
            db.commit()

        # Create Result
        result = ScreenerResult(
            ticker=ticker,
            score=float(score),
            phase="Accumulation",
            volatility=float(filters['volatility']),
            dist_from_low=float(filters['dist_from_low']),
            status="NEW"
        )
        db.add(result)
        db.commit()
        logging.info(f"💾 Saved {ticker} to database.")
    except Exception as e:
        logging.error(f"Failed to save to DB: {e}")
    finally:
        db.close()


def run_screener(target_ticker=None, force_retrain=False):
    print("🧠 Initializing Wyckoff AI...")

    # Auto-Retrain Check
    if not force_retrain and check_model_freshness():
        force_retrain = True

    model = None
    if not force_retrain:
        model = ai_engine.load_model()

    if model is None:
        model = ai_engine.train_model()

    if target_ticker:
        # Normalize ticker
        ticker = target_ticker.upper()
        if not ticker.endswith('.JK'):
            ticker = f"{ticker}.JK"
        tickers = [ticker]
        print(f"🔎 Scanning Single Target: {ticker}...")
    else:
        tickers = market_data.load_tickers(STOCK_LIST_FILE)
        print(f"🔎 Scanning {len(tickers)} stocks for Accumulation Patterns...")

    hits = 0
    for i, ticker in enumerate(tickers):
        print(f"   Scanning {ticker}...", end="\r")
        df = market_data.get_market_data(ticker)

        if df is None:
            continue

        # 1. Technical Filter
        passed, reason, filters = technical_analysis.check_filters(df)
        if not passed:
            if target_ticker:
                # Force generation of full report even on failure
                trade_setup = technical_analysis.calculate_trade_setup(df)
                chart_file = charting.generate_chart(
                    df, ticker, filters, trade_setup)
                fundamentals = market_data.get_fundamentals(ticker)

                # Send with NEGATIVE status
                notification.send_alert(ticker, filters, 0.0, chart_file, trade_setup, fundamentals,
                                        override_status="NEGATIVE", failure_reason=reason)
            continue

        # 2. AI Scoring
        score = ai_engine.get_lstm_score(model, df)

        if score >= 0.75:
            print(
                f"\n✨ FOUND {ticker}! Score: {score:.2f} | Low Dist: {filters['dist_from_low']:.2%}")

            trade_setup = technical_analysis.calculate_trade_setup(df)

            # Lot Size Filter (Money Management)
            if trade_setup['lots'] < 3:
                # print(f"   Skipped {ticker} (Small Position: {trade_setup['lots']} lots)")
                continue

            chart_file = charting.generate_chart(
                df, ticker, filters, trade_setup)
            fundamentals = market_data.get_fundamentals(ticker)

            notification.send_alert(ticker, filters, score, chart_file,
                                    trade_setup, fundamentals)

            # Save to Database
            save_scan_result_to_db(ticker, score, filters)

            # Save to Database
            save_scan_result_to_db(ticker, score, filters)

            hits += 1
        else:
            if target_ticker:
                print(f"   Skipped {ticker} (Score: {score:.2f})")
                trade_setup = technical_analysis.calculate_trade_setup(df)
                chart_file = charting.generate_chart(
                    df, ticker, filters, trade_setup)
                fundamentals = market_data.get_fundamentals(ticker)

                notification.send_alert(ticker, filters, score, chart_file, trade_setup, fundamentals,
                                        override_status="NEGATIVE", failure_reason=f"Low AI Score ({score:.2f})")

        # Rate Limit Protection
        time.sleep(0.5)

    print(f"\n✅ Scan Complete. Found {hits} candidates.")
    notification.send_scan_summary(len(tickers), hits)


if __name__ == "__main__":
    # Check for CLI arguments
    # Usage: python src/main.py [TICKER] [--retrain]

    target = None
    retrain = False

    args = sys.argv[1:]
    if "--retrain" in args:
        retrain = True
        args.remove("--retrain")

    if len(args) > 0:
        target = args[0]

    run_screener(target, retrain)
