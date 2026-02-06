import numpy as np
from sklearn.linear_model import LinearRegression
from config.settings import LOW_PCT_THRESHOLD, STD_DEV_THRESHOLD, MIN_PRICE, RISK_PCT, CAPITAL_IDR, MIN_AVG_VOLUME


def check_filters(df):
    """
    Returns True if stock passes Wyckoff Phase B Filters:
    1. Minimum Price
    2. Near 52-Week Low
    3. Low Volatility (Sideways)
    4. Rising OBV Trend
    """
    current_price = df['Close'].iloc[-1]

    # 0. Liquidity Filter (Avg Volume > X)
    avg_vol = df['Volume'].tail(20).mean()
    if avg_vol < MIN_AVG_VOLUME:
        return False, f"Volume too low ({avg_vol:,.0f} < {MIN_AVG_VOLUME:,.0f})", None

    # 0.5 Volume Spike Check (Instituional Footprint)
    # Require at least one day in last 10 where Vol > 1.5x Avg
    recent_vol = df['Volume'].tail(10)
    vol_spike = (recent_vol > (avg_vol * 1.5)).any()
    if not vol_spike:
        return False, "No Volume Spike (Passive)", None

    # 0.6 Min Price Filter (Restore)
    if current_price < MIN_PRICE:
        return False, f"Price below {MIN_PRICE}", None

    # 1. Price Location (Within X% of 52-week low)
    low_52w = df['Low'].min()
    dist_from_low = (current_price - low_52w) / low_52w

    if dist_from_low > LOW_PCT_THRESHOLD:
        return False, f"Price too high (> {LOW_PCT_THRESHOLD*100:.0f}% from low)", None

    # 2. Sideways Filter (Low Volatility on Close over last 30 days)
    recent = df['Close'].tail(30)
    std_dev = recent.std()
    mean_price = recent.mean()
    volatility = std_dev / mean_price

    if volatility > STD_DEV_THRESHOLD:
        return False, f"Volatility too high (> {STD_DEV_THRESHOLD*100:.0f}%)", None

    # 3. OBV Confirmation (Rising Trend over last 20 days)
    obv_recent = df['OBV'].tail(20).values
    x = np.arange(len(obv_recent)).reshape(-1, 1)
    y = obv_recent.reshape(-1, 1)
    reg = LinearRegression().fit(x, y)
    obv_slope = reg.coef_[0][0]

    if obv_slope <= 0.05:  # Strict Accumulation Slope
        return False, f"Weak OBV ({obv_slope:.2f})", None

    return True, "Passed", {
        "dist_from_low": dist_from_low,
        "volatility": volatility,
        "obv_slope": obv_slope
    }


def calculate_trade_setup(df):
    """Calculates entry, stop loss, and position size."""
    close = df['Close'].iloc[-1]
    low_swing = df['Low'].tail(10).min()

    # Entry: Current Price
    entry = close

    # Stop Loss: Just below recent swing low
    sl = low_swing * 0.98

    # Take Profit: 2.5x Risk/Reward
    risk = entry - sl
    tp = entry + (risk * 2.5)

    # Formatting
    sl_pct = (entry - sl) / entry * 100

    # Money Management
    risk_amount = CAPITAL_IDR * RISK_PCT
    risk_per_share = entry - sl

    if risk_per_share <= 0:
        position_size = 0
    else:
        position_size = int(risk_amount / risk_per_share)

    # Convert to Lots (1 Lot = 100 shares)
    lots = position_size // 100
    capital_required = lots * 100 * entry
    potential_loss = lots * 100 * risk_per_share

    # Profit Calculation
    profit_per_share = tp - entry
    profit_per_lot = profit_per_share * 100
    loss_per_lot = risk_per_share * 100

    # Recommendation
    recommendation = "WAIT"  # Default
    if sl_pct < 8:  # Only bullish if SL is tight enough
        recommendation = "BUY"

    return {
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "sl_pct": sl_pct,
        "demand_zone": {"top": low_swing * 1.02, "bottom": low_swing},
        "lots": lots,
        "capital_req": capital_required,
        "potential_loss": potential_loss,
        "loss_per_lot": loss_per_lot,
        "profit_per_lot": profit_per_lot,
        "recommendation": recommendation
    }
