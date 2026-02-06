import requests
import json
import logging
import os
from datetime import datetime
from config.settings import DISCORD_WEBHOOK_URL


def send_alert(ticker, filters, score, chart_path, trade_setup, fundamentals=None, override_status=None, failure_reason=None):
    """Sends a rich Discord embed alert."""

    if not DISCORD_WEBHOOK_URL:
        logging.warning("Discord Webhook URL not set. Skipping alert.")
        if os.path.exists(chart_path):
            os.remove(chart_path)
        return

    color = 5763719  # Green-ish (Default Success)
    title = f"🚨 Accumulation Detected: {ticker}"

    # Failure Overrides
    if override_status == "NEGATIVE":
        color = 15548997  # Red
        title = f"❌ Analysis Negative: {ticker}"
        trade_setup['recommendation'] = "WAIT"

    # Gold Status for High Score
    elif score > 0.85:
        color = 15158332  # Gold

    # Execution Block
    exec_block = f"""```yaml
ENTRY : {trade_setup['entry']:,.0f} (Market)
TP    : {trade_setup['tp']:,.0f} (RR 1:2.5)
SL    : {trade_setup['sl']:,.0f} (-{trade_setup['sl_pct']:.1f}%)
```"""

    # Money Block
    money_block = f"""```prolog
Lots  : {trade_setup['lots']} Lot
Modal : Rp {trade_setup['capital_req']:,.0f}
Risk  : Rp {trade_setup['potential_loss']:,.0f}
Loss/Lot   : Rp {trade_setup['loss_per_lot']:,.0f}
Profit/Lot : Rp {trade_setup['profit_per_lot']:,.0f}
```"""

    # SMC Block
    dz = trade_setup['demand_zone']
    smc_block = f"**Demand Zone (OB):** `{dz['bottom']:,.0f}` - `{dz['top']:,.0f}`\n**Struct:** Accumulation (Phase B)"

    # Fundamentals Block
    fa_block = "Data N/A"
    if fundamentals:
        fa_block = f"**MCap:** `{fundamentals['mcap']}`\n**PER:** `{fundamentals['per']:.1f}x` | **PBV:** `{fundamentals['pbv']:.2f}x`\n**ROE:** `{fundamentals['roe']*100:.1f}%`"

    # Fields Construction

    # Safe Filter Access
    dist_str = "N/A"
    tech_str = "N/A"
    if filters:
        if 'dist_from_low' in filters:
            dist_str = f"{filters['dist_from_low']*100:.1f}% from Low"
        if 'volatility' in filters and 'obv_slope' in filters:
            tech_str = f"Volatility: `{filters['volatility']*100:.1f}%`\nOBV Slope: `+{filters['obv_slope']:.2f}`"

    fields = [
        {"name": "🧠 AI Confidence", "value": f"`{score*100:.1f}%`", "inline": True},
        {"name": "📉 Price Location",
            "value": dist_str, "inline": True},
        {"name": "🔭 Recommendation",
            "value": f"**{trade_setup['recommendation']}**", "inline": False}
    ]

    if failure_reason:
        fields.insert(
            2, {"name": "⚠️ Reason", "value": f"`{failure_reason}`", "inline": False})

    fields.extend([
        {"name": "🚥 Trade Setup", "value": exec_block, "inline": False},
        {"name": "💰 Money Management", "value": money_block, "inline": False},
        {"name": "📊 Fundamentals", "value": fa_block, "inline": False},
        {"name": "🏦 Smart Money Concepts", "value": smc_block, "inline": False},
        {"name": "📊 Technicals",
            "value": tech_str, "inline": False}
    ])

    embed = {
        "username": "Wyckoff AI Scanner",
        "embeds": [{
            "title": title,
            "description": f"**Phase B Candidate** (Sideways + Buying)",
            "color": color,
            "fields": fields,
            "footer": {"text": f"Scanned at {datetime.now().strftime('%H:%M WIB')}"}
        }]
    }

    try:
        with open(chart_path, "rb") as f:
            requests.post(DISCORD_WEBHOOK_URL, data={
                          "payload_json": json.dumps(embed)}, files={"file": f})
        os.remove(chart_path)
    except Exception as e:
        logging.error(f"Failed to send Discord alert: {e}")


def send_scan_summary(total_scanned, candidates_found):
    """Sends a summary of the scan results."""
    if not DISCORD_WEBHOOK_URL:
        return

    color = 5763719  # Green
    title = "✅ Wyckoff Scan Complete"

    fields = [
        {"name": "🔍 Scanned", "value": f"`{total_scanned} stocks`", "inline": True},
        {"name": "✨ Patterns Found",
            "value": f"`{candidates_found} candidates`", "inline": True}
    ]

    embed = {
        "username": "Wyckoff AI Scanner",
        "embeds": [{
            "title": title,
            "description": f"Scan finished at {datetime.now().strftime('%H:%M WIB')}.",
            "color": color,
            "fields": fields,
            "footer": {"text": "Wyckoff Accumulation Screener"}
        }]
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, data={
                      "payload_json": json.dumps(embed)})
    except Exception as e:
        logging.error(f"Failed to send summary: {e}")
