# Wyckoff Strategy & Analytics Bot 🚀

An intelligent Python-based stock screener tailored for the **IHSG (Indonesia Stock Exchange)**. It uses a custom **LSTM Neural Network** combined with **Wyckoff Accumulation** logic to identify high-probability "Sniper" setups.

## 🌟 Key Features

* **🧠 Hybrid AI Engine**: Uses LSTM (Long Short-Term Memory) trained on synthetic Wyckoff patterns (accumulation, distribution, markups, springs) to classify market phases.
* **🎯 Sniper Mode Filters**: Aggressively filters for specific setups:
  * **Volume Spike**: Requires >1.5x Avg Volume (Institutional Footprint).
  * **Strict OBV**: Slope > 0.05 (Strong Accumulation).
  * **Liquidity**: Min Avg Volume > 1,000,000 shares.
  * **Money Management**: Skips trades with < 3 Lots allowed.
* **📊 Dark Theme Charts**: Generates professional, dark-themed charts with Support/Resistance levels, SMA50, and OBV panels.
* **🔔 Discord Integrations**: Sends rich embeds with analysis, charts, and trade setups directly to Discord.
* **💾 Database Integration**: Stores scan results in PostgreSQL for historical tracking.

## 🛠️ Installation

1. **Clone the Repository**

    ```bash
    git clone <repository_url>
    cd ihsg-analytics
    ```

2. **Install Dependencies**
    This project uses `uv` for fast package management.

    ```bash
    uv sync
    ```

    Or using pip:

    ```bash
    pip install -r requirements.txt
    ```

3. **Setup Environment**
    Copy the example environment file:

    ```bash
    cp .env.example .env
    ```

    Edit `.env` with your configuration:
    * `DATABASE_URL`: Your PostgreSQL connection string.
    * `DISCORD_WEBHOOK_Result`: Your Discord Webhook URL.

4. **Prepare Stock List**
    Ensure `Stock_List.xlsx` is present in the root directory.

## 🚀 Usage

### 1. Run the Screener (Sniper Scan)

Scans the market for accumulation patterns.

```bash
uv run python src/main.py
```

* **Optional**: Scan a single ticker: `uv run python src/main.py BBCA.JK`
* **Optional**: Force Retrain Model: `uv run python src/main.py --retrain`

### 2. Run Backtest Simulation

Verify the strategy profitability on historical data.

```bash
uv run python src/backtest.py
```

## 📂 Project Structure

```
src/
├── config/
│   └── settings.py       # Configuration & Constants
├── services/
│   ├── ai_engine.py      # LSTM Model Logic
│   ├── market_data.py    # Yahoo Finance Data Fetcher
│   ├── technical_analysis.py # Wyckoff Filters & Trade Setup
│   ├── charting.py       # MPLFinance Chart Generator
│   └── notification.py   # Discord Notification Service
├── main.py               # Main Entry Point
├── backtest.py           # Strategy Simulator
└── database.py           # Database Models
```

## 📈 Strategy Statistics (Verified)

* **Win Rate**: ~52.7%
* **Annual Return**: ~59.1%
* **Focus**: High Liquidity, Volatile Upside, Safe Entries.

## ⚠️ Disclaimer

This is for educational purposes only. Trade at your own risk.
