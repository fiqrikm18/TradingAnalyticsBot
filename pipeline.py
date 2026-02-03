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
    # Jalankan Backtest dulu untuk update list pemenang
    if run_step("backtest.py", "1 (AGGRESSIVE BACKTEST)"):
        print("⏳ Cooldown (3s)...")
        time.sleep(3)
        # Jalankan Scanner untuk cari sinyal live
        run_step("main.py", "2 (RISK-AWARE SCANNER)")