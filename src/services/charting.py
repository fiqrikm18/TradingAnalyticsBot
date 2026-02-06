import uuid
import os
import matplotlib.pyplot as plt
import mplfinance as mpf
import matplotlib
matplotlib.use('Agg')  # Force non-interactive backend


def generate_chart(df, ticker, filters, trade_setup):
    """Generates a Wyckoff-style chart matching the user's aesthetic."""
    temp_filename = f"chart_{ticker}_{uuid.uuid4().hex[:6]}.png"

    # 1. Theme Configuration
    # Up Candle: White, Down Candle: DodgerBlue (Cool Contrast)
    mc = mpf.make_marketcolors(
        up='#ffffff', down='#0091ea',
        edge='inherit',
        wick='inherit',
        volume={'up': '#4caf50', 'down': '#ef5350'}
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        base_mpf_style='nightclouds',
        facecolor='#000000',      # Pure Black Background
        edgecolor='#444444',      # Subtle grey borders
        gridcolor='#444444',      # Subtle grid
        gridstyle=':',            # Dotted grid
        rc={'axes.labelsize': 10, 'xtick.labelsize': 8, 'ytick.labelsize': 8}
    )

    # 2. Add Plots (Indicators & Overlays)
    apds = []

    # SMA 50 (Yellow Line)
    # Check if SMA50 is already calculated, otherwise calculate it
    if 'SMA50' not in df.columns:
        df['SMA50'] = df['Close'].rolling(window=50).mean()

    apds.append(mpf.make_addplot(
        df['SMA50'], color='#ffff00', width=1.5, label='SMA 50'))

    # OBV (Panel 2 - Bright Green)
    if 'OBV' in df.columns:
        apds.append(mpf.make_addplot(
            df['OBV'], panel=2, color='#00ff00', width=1.5, ylabel='OBV'))

    # 3. Create Figure
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=s,
        volume=True,
        title=f"\nWyckoff Accumulation: {ticker}",
        addplot=apds,
        figsize=(12, 10),
        panel_ratios=(5, 1, 1.5),  # Bigger Price Panel
        tight_layout=True,
        scale_width_adjustment=dict(volume=0.6, candle=1.2),  # Fatter candles
        returnfig=True,
        savefig=dict(fname=temp_filename, dpi=100, bbox_inches='tight')
    )

    # 4. Custom Annotations (Support / Resistance Lines & Labels)
    ax_main = axes[0]

    # Resistance Line (Red Dash-Dot)
    # Using Top of DZ as proxy or finding resistance
    res_price = trade_setup['demand_zone']['top']
    # Note: Trade setup gives Demand Zone (Support). We need a resistance level.
    # We'll calculate a simple resistance based on recent highs for visualization
    resistance_price = df['High'].tail(60).max()
    support_price = trade_setup['demand_zone']['bottom']

    # Plot Resistance Line
    ax_main.axhline(resistance_price, color='#ff0000',
                    linestyle='-.', linewidth=1, alpha=0.8)
    ax_main.text(0, resistance_price * 1.01, f"Resistance: {resistance_price:,.0f}",
                 color='red', fontsize=9, va='bottom', ha='left', transform=ax_main.get_yaxis_transform())

    # Plot Support Line (Green Dash-Dot)
    ax_main.axhline(support_price, color='#00ff00',
                    linestyle='-.', linewidth=1, alpha=0.8)
    ax_main.text(0, support_price * 1.01, f"Support: {support_price:,.0f}",
                 color='green', fontsize=9, va='bottom', ha='left', transform=ax_main.get_yaxis_transform())

    # Save manually since returnfig=True prevents auto-save
    fig.savefig(temp_filename, dpi=100, bbox_inches='tight', facecolor='black')
    plt.close(fig)

    return temp_filename
