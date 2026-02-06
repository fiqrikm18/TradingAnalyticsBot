import subprocess
import sys
import time


def run_step(script_name, step_name):
    print(f"\n{'='*40}\n🚀 STEP {step_name}: {script_name}\n{'='*40}")
    try:
        subprocess.run([sys.executable, script_name], check=True)
        return True
    except:
        print(f"❌ {script_name} Failed.")
        return False


if __name__ == "__main__":
    # 1. First, get the "Big Picture" of the market
    run_step("src/daily_analytics.py", "1 (MARKET BRIEF)")

    time.sleep(2)

    # 2. Then, run the Backtest Filter
    if run_step("src/backtest.py", "2 (AGGRESSIVE BACKTEST)"):
        time.sleep(2)

        # 3. Finally, scan for specific Buy Signals
        run_step("src/analytics.py", "3 (DEEP DIVE SCANNER)")

        time.sleep(2)

        # 4. Wyckoff Accumulation Screener
        run_step("src/wyckoff_screener.py", "4 (WYCKOFF ACCUMULATION)")
    print("\n🚀 Pipeline Completed.")
