import os
from dotenv import load_dotenv

load_dotenv()

# --- DATABASE ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- AI MODEL ---
# Using absolute path to ensure model can be found from anywhere
BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MODEL_FILENAME = "wyckoff_lstm.keras"
MODEL_PATH = os.path.join(BASE_DIR, MODEL_FILENAME)
RETRAIN_INTERVAL_DAYS = 0

# --- SCREENER FILTERS ---
LOOKBACK_DAYS = 60
STD_DEV_THRESHOLD = 0.15
LOW_PCT_THRESHOLD = 0.35
MIN_PRICE = 200
MIN_AVG_VOLUME = 1000000

# --- MONEY MANAGEMENT ---
CAPITAL_IDR = int(os.getenv("CAPITAL_IDR", 1400000))
RISK_PCT = float(os.getenv("RISK_PCT", 0.02))
MIN_WIN_RATE = float(os.getenv("MIN_WIN_RATE", 60.0))

# --- PATHS ---
STOCK_LIST_FILE = os.getenv("STOCK_LIST_FILE", "Stock_List.xlsx")
# Ensure stock list path is absolute if needed, or relative to CWD
if not os.path.isabs(STOCK_LIST_FILE):
    STOCK_LIST_FILE = os.path.join(BASE_DIR, STOCK_LIST_FILE)

# --- DISCORD ---
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_Result", "")
