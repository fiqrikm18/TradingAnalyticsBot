# IHSG Analytics


A Python project for backtesting and analyzing strategies on the Indonesia Stock Exchange (IHSG).

## Setup Guide

### 1. Clone the Repository
```
git clone <repo-url>
cd ihsg-analytics
```

### 2. Create and Activate a Virtual Environment
```
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
If you use `pyproject.toml` with Poetry:
```
pip install poetry
poetry install
```
Or, if using pip:
```
pip install -r requirements.txt  # If requirements.txt exists
```

### 4. Run the Project
```
python main.py
```

### 5. (Optional) Run Backtest Directly
```
python backtest.py
```

---

## Features
- Backtesting engine
- Data pipeline
- Configurable constants
- Result export to CSV

## Project Structure
- `main.py` - Main entry point
- `pipeline.py` - Data pipeline logic
- `backtest.py` - Backtesting logic
- `consts.py` - Project constants
- `backtest_results.csv` - Output results

## Getting Started
1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies (see `pyproject.toml`)
4. Run the main script:
   ```bash
   python main.py
   ```

## License
MIT
