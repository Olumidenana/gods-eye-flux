"""
Generate High-Resolution Institutional ICT Candlestick Chart References
Renders pixel-perfect, dark-mode TradingView/MT5 style chart diagrams for all core ICT Mentorship rules.
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Style parameters
BG_COLOR = '#07090E'
SURFACE_COLOR = '#0E131F'
GRID_COLOR = '#192237'
TEXT_COLOR = '#F8FAFC'
MUTED_TEXT = '#94A3B8'
GREEN_CANDLE = '#10B981'
RED_CANDLE = '#F43F5E'
CYAN_ACCENT = '#00F0FF'
GOLD_ACCENT = '#F59E0B'
INDIGO_ACCENT = '#6366F1'

def setup_chart_figure(title, subtitle, rule_badge):
    fig, ax = plt.subplots(figsize=(14, 8), facecolor=BG_COLOR)
    ax.set_facecolor(SURFACE_COLOR)
    
    # Title and Badges
    fig.text(0.08, 0.94, title, fontsize=16, fontweight='bold', color=TEXT_COLOR, family='sans-serif')
    fig.text(0.08, 0.91, subtitle, fontsize=11, color=MUTED_TEXT, family='sans-serif')
    fig.text(0.88, 0.93, rule_badge, fontsize=11, fontweight='bold', color=CYAN_ACCENT, 
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#0E131F', edgecolor=CYAN_ACCENT, alpha=0.9),
             horizontalalignment='right')
    
    # Watermark
    fig.text(0.50, 0.50, "ICT FLUX • INSTITUTIONAL CORE", fontsize=28, color='#151E33',
             ha='center', va='center', alpha=0.35, fontweight='black', rotation=15)
    
    ax.grid(True, color=GRID_COLOR, linestyle='--', linewidth=0.7, alpha=0.6)
    for spine in ax.spines.values():
        spine.set_color('#2A364F')
    ax.tick_params(colors=MUTED_TEXT, labelsize=9)
    return fig, ax

def draw_candle(ax, x, op, hi, lo, cl, width=0.55):
    color = GREEN_CANDLE if cl >= op else RED_CANDLE
    # Wick
    ax.plot([x, x], [lo, hi], color=color, linewidth=1.5, zorder=3)
    # Body
    body_low = min(op, cl)
    body_height = max(abs(cl - op), 0.0001)
    rect = patches.Rectangle((x - width/2, body_low), width, body_height, 
                             facecolor=color, edgecolor=color, zorder=4)
    ax.add_patch(rect)

# -----------------------------------------------------------------------------
# 1. FAIR VALUE GAP & CONSEQUENT ENCROACHMENT (FV-01 & FV-02)
# -----------------------------------------------------------------------------
def generate_chart_1(output_paths):
    fig, ax = setup_chart_figure(
        "01. Fair Value Gap (FVG) & Consequent Encroachment (CE 50%)",
        "Rule FV-01 (3-Candle Imbalance) & FV-02 (50% Displacement Equilibrium)",
        "RULE: FV-01 / FV-02"
    )
    
    draw_candle(ax, 1, 100.5, 101.2, 100.0, 100.8) # C0 consolidation
    draw_candle(ax, 2, 100.8, 101.5, 100.4, 101.0) # C1: Low is 100.4
    draw_candle(ax, 3, 100.9, 101.1, 98.2, 98.5)   # C2: Displacement Candle
    draw_candle(ax, 4, 98.5, 99.6, 98.0, 99.1)     # C3: High is 99.6
    
    fvg_top = 100.4
    fvg_bottom = 99.6
    fvg_ce = (fvg_top + fvg_bottom) / 2.0 # 100.0
    
    draw_candle(ax, 5, 99.1, 99.8, 98.9, 99.5)
    draw_candle(ax, 6, 99.5, 100.05, 99.3, 99.7)  # Taps CE 100.0
    draw_candle(ax, 7, 99.7, 99.8, 97.4, 97.6)    # Expansion delivery
    draw_candle(ax, 8, 97.6, 97.7, 96.0, 96.2)    # Take Profit hit
    
    fvg_rect = patches.Rectangle((2.3, fvg_bottom), 4.2, fvg_top - fvg_bottom,
                                 facecolor=CYAN_ACCENT, alpha=0.15, edgecolor=CYAN_ACCENT,
                                 linestyle='--', linewidth=1.5, zorder=2)
    ax.add_patch(fvg_rect)
    ax.plot([2.3, 7.5], [fvg_ce, fvg_ce], color=GOLD_ACCENT, linestyle=':', linewidth=2, zorder=5)
    
    ax.annotate("CANDLE 1\nLow: 100.40", xy=(2, 100.4), xytext=(0.5, 101.5),
                arrowprops=dict(facecolor=CYAN_ACCENT, arrowstyle='->', lw=1.2),
                color=TEXT_COLOR, fontsize=9, fontweight='bold', family='monospace')
    
    ax.annotate("CANDLE 2\nDisplacement Leg", xy=(3, 98.5), xytext=(2.6, 97.0),
                arrowprops=dict(facecolor=CYAN_ACCENT, arrowstyle='->', lw=1.2),
                color=TEXT_COLOR, fontsize=9, fontweight='bold', family='monospace')

    ax.annotate("CANDLE 3\nHigh: 99.60", xy=(4, 99.6), xytext=(4.3, 98.5),
                arrowprops=dict(facecolor=CYAN_ACCENT, arrowstyle='->', lw=1.2),
                color=TEXT_COLOR, fontsize=9, fontweight='bold', family='monospace')
    
    ax.annotate("CONSEQUENT ENCROACHMENT (50% CE: 100.00)\nOptimal Limit Entry Filled To The Tick", 
                xy=(6, fvg_ce), xytext=(5.0, 101.2),
                arrowprops=dict(facecolor=GOLD_ACCENT, arrowstyle='->', lw=1.5),
                color=GOLD_ACCENT, fontsize=10, fontweight='bold', family='monospace',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#0E131F', edgecolor=GOLD_ACCENT, alpha=0.9))

    ax.annotate("TAKE PROFIT PURGED (+3.50R)\nOpposing Sell-Side Liquidity", xy=(8, 96.2), xytext=(6.5, 95.0),
                arrowprops=dict(facecolor=GREEN_CANDLE, arrowstyle='->', lw=1.5),
                color=GREEN_CANDLE, fontsize=10, fontweight='bold', family='monospace')

    ax.set_xlim(0, 9)
    ax.set_ylim(94.5, 102.5)
    ax.set_ylabel("Price Level", color=MUTED_TEXT, fontsize=10)
    plt.tight_layout()
    for p in output_paths:
        fig.savefig(p, dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

# -----------------------------------------------------------------------------
# 2. ASIAN RANGE SWEEP & JUDAS SWING REVERSAL (KZ-04, SW-01, MS-02)
# -----------------------------------------------------------------------------
def generate_chart_2(output_paths):
    fig, ax = setup_chart_figure(
        "02. Asian Range Liquidity Sweep & London Judas Swing",
        "Rules KZ-04 (London Killzone), SW-01 (Sweep Buffer), MS-02 (Displacement MSS)",
        "RULE: KZ-04 / SW-01"
    )
    
    asian_box = patches.Rectangle((0.5, 1.3190), 3.0, 1.3215 - 1.3190,
                                  facecolor=INDIGO_ACCENT, alpha=0.15, edgecolor=INDIGO_ACCENT,
                                  linestyle='--', linewidth=1.5, zorder=2)
    ax.add_patch(asian_box)
    ax.text(0.7, 1.3218, "ASIAN SESSION CONSOLIDATION (20:00 - 00:00 NY)", color=INDIGO_ACCENT, 
            fontsize=9, fontweight='bold', family='monospace')

    draw_candle(ax, 1, 1.3200, 1.3212, 1.3198, 1.3208)
    draw_candle(ax, 2, 1.3208, 1.3215, 1.3202, 1.3205) # Asian High 1.3215
    draw_candle(ax, 3, 1.3205, 1.3208, 1.3190, 1.3195) # Asian Low 1.3190
    draw_candle(ax, 4, 1.3195, 1.3202, 1.3192, 1.3198)

    # 02:00 London KZ Judas Swing Sweep (Pierces Asian Low)
    draw_candle(ax, 5, 1.3198, 1.3200, 1.3178, 1.3182) # Judas Swing piercing 1.3190
    draw_candle(ax, 6, 1.3182, 1.3225, 1.3180, 1.3220) # MASSIVE BULLISH DISPLACEMENT CANDLE
    draw_candle(ax, 7, 1.3220, 1.3235, 1.3215, 1.3230)
    draw_candle(ax, 8, 1.3230, 1.3255, 1.3228, 1.3250) # Target reached

    ax.plot([0.5, 8.5], [1.3190, 1.3190], color=RED_CANDLE, linestyle='--', linewidth=1.5)
    ax.text(6.0, 1.3187, "ASIAN LOW SSL PURGED (1.3190)", color=RED_CANDLE, fontsize=9, family='monospace')

    ax.annotate("LONDON JUDAS SWING (02:00 NY)\nEngineered Liquidity Run Into SSL", 
                xy=(5, 1.3178), xytext=(2.2, 1.3165),
                arrowprops=dict(facecolor=RED_CANDLE, arrowstyle='->', lw=1.5),
                color=RED_CANDLE, fontsize=10, fontweight='bold', family='monospace',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#0E131F', edgecolor=RED_CANDLE, alpha=0.9))

    ax.annotate("MARKET STRUCTURE SHIFT (MSS)\nAggressive Displacement Across Swing High", 
                xy=(6, 1.3220), xytext=(4.0, 1.3245),
                arrowprops=dict(facecolor=GREEN_CANDLE, arrowstyle='->', lw=1.5),
                color=GREEN_CANDLE, fontsize=10, fontweight='bold', family='monospace',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#0E131F', edgecolor=GREEN_CANDLE, alpha=0.9))

    ax.set_xlim(0, 9)
    ax.set_ylim(1.3155, 1.3265)
    ax.set_ylabel("GBPUSD Price", color=MUTED_TEXT, fontsize=10)
    plt.tight_layout()
    for p in output_paths:
        fig.savefig(p, dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

# -----------------------------------------------------------------------------
# 3. RULE SW-02: ORDER OF LIQUIDITY PURGING (CAPITAL DEFENSE)
# -----------------------------------------------------------------------------
def generate_chart_3(output_paths):
    fig, ax = setup_chart_figure(
        "03. Order of Liquidity Purging Filter (The Gold Defense)",
        "Rule SW-02: BSL Must Be Taken First For Shorts; Reject Short If SSL Purged First",
        "RULE: SW-02 (ALGO DEFENSE)"
    )
    
    ax.plot([0.5, 9.5], [4130, 4130], color=RED_CANDLE, linestyle='--', linewidth=1.5)
    ax.text(0.7, 4125, "SELL-SIDE LIQUIDITY (SSL): 4130.00", color=RED_CANDLE, fontsize=9, family='monospace')

    ax.plot([0.5, 9.5], [4162, 4162], color=GOLD_ACCENT, linestyle='--', linewidth=1.5)
    ax.text(0.7, 4164, "BUY-SIDE LIQUIDITY (BSL): 4162.00", color=GOLD_ACCENT, fontsize=9, family='monospace')

    # Step 1: Early session sweeps SSL first
    draw_candle(ax, 1, 4145, 4148, 4135, 4138)
    draw_candle(ax, 2, 4138, 4140, 4126, 4132) # SSL Swept here!
    
    # Step 2: Gold rallies into BSL
    draw_candle(ax, 3, 4132, 4146, 4130, 4145)
    draw_candle(ax, 4, 4145, 4158, 4142, 4155)
    draw_candle(ax, 5, 4155, 4164, 4153, 4160) # Sweeps BSL at 4164
    
    # Step 3: Retail tries to short; Bot cancels setup due to SW-02
    draw_candle(ax, 6, 4160, 4162, 4154, 4156) # FVG print
    draw_candle(ax, 7, 4156, 4172, 4155, 4170) # Gold EXPLODES up!
    draw_candle(ax, 8, 4170, 4182, 4168, 4180)

    ax.annotate("STEP 1: SSL SWEPT FIRST\n[Delivery Order Dictates Higher Draw On BSL]", 
                xy=(2, 4126), xytext=(1.2, 4110),
                arrowprops=dict(facecolor=RED_CANDLE, arrowstyle='->', lw=1.5),
                color=RED_CANDLE, fontsize=9, fontweight='bold', family='monospace')

    ax.annotate("STEP 2: BSL SWEPT AT 4164\nRetail Enters Blind Short Market Orders", 
                xy=(5, 4164), xytext=(3.2, 4175),
                arrowprops=dict(facecolor=GOLD_ACCENT, arrowstyle='->', lw=1.5),
                color=GOLD_ACCENT, fontsize=9, fontweight='bold', family='monospace')

    cancel_box = patches.Rectangle((5.2, 4145), 3.8, 25,
                                   facecolor=GREEN_CANDLE, alpha=0.15, edgecolor=GREEN_CANDLE,
                                   linewidth=2, zorder=5)
    ax.add_patch(cancel_box)
    ax.text(5.4, 4165, "RULE SW-02 INTERCEPT:\nSHORT SETUP CANCELLED!", 
            color=GREEN_CANDLE, fontsize=10, fontweight='bold', family='monospace')
    ax.text(5.4, 4154, "Why: SSL was swept first.\nResult: Saved -$1,000 on Prop\nSaved -$20 on Micro Account!", 
            color=TEXT_COLOR, fontsize=8.5, family='monospace')

    ax.set_xlim(0, 10)
    ax.set_ylim(4100, 4195)
    ax.set_ylabel("XAUUSD Price", color=MUTED_TEXT, fontsize=10)
    plt.tight_layout()
    for p in output_paths:
        fig.savefig(p, dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

# -----------------------------------------------------------------------------
# 4. SILVER BULLET 60-MINUTE EXECUTION WINDOW (SB-01 to SB-04)
# -----------------------------------------------------------------------------
def generate_chart_4(output_paths):
    fig, ax = setup_chart_figure(
        "04. ICT Silver Bullet 60-Minute Execution Model",
        "Rules SB-01 (10:00–11:00 NY Window), SB-02 (First FVG), SB-03 (15-Pip Target)",
        "RULE: SB-01 / SB-02"
    )
    
    sb_box = patches.Rectangle((2.5, 5730), 4.5, 5780 - 5730,
                               facecolor=CYAN_ACCENT, alpha=0.08, edgecolor=CYAN_ACCENT,
                               linestyle='--', linewidth=1.5, zorder=2)
    ax.add_patch(sb_box)
    ax.text(2.7, 5776, "SILVER BULLET WINDOW (10:00 - 11:00 AM NY TIME)", color=CYAN_ACCENT, 
            fontsize=9.5, fontweight='bold', family='monospace')

    draw_candle(ax, 1, 5748, 5752, 5744, 5750)
    draw_candle(ax, 2, 5750, 5755, 5747, 5752)
    draw_candle(ax, 3, 5752, 5754, 5736, 5738) # Sweep
    draw_candle(ax, 4, 5738, 5756, 5737, 5754) # Displacement leaving FVG!
    draw_candle(ax, 5, 5754, 5757, 5743, 5745) # Retest taps FVG (Entry!)
    draw_candle(ax, 6, 5745, 5768, 5744, 5765) # Momentum run
    draw_candle(ax, 7, 5765, 5775, 5762, 5772) # Target hit within window!

    fvg = patches.Rectangle((3.6, 5742), 1.8, 5748 - 5742,
                            facecolor=GREEN_CANDLE, alpha=0.25, edgecolor=GREEN_CANDLE,
                            linestyle='--', linewidth=1.2, zorder=3)
    ax.add_patch(fvg)
    ax.text(3.7, 5744, "SB 5M FVG", color=GREEN_CANDLE, fontsize=8.5, family='monospace')

    ax.annotate("10:00 AM LIQUIDITY RUN\nSweeps 09:50 Swing Low", 
                xy=(3, 5736), xytext=(1.2, 5724),
                arrowprops=dict(facecolor=RED_CANDLE, arrowstyle='->', lw=1.5),
                color=RED_CANDLE, fontsize=9.5, fontweight='bold', family='monospace')

    ax.annotate("FIRST DISPLACEMENT FVG (SB-02)\nLimit Filled @ 5744.00", 
                xy=(5, 5744), xytext=(4.2, 5732),
                arrowprops=dict(facecolor=CYAN_ACCENT, arrowstyle='->', lw=1.5),
                color=CYAN_ACCENT, fontsize=9.5, fontweight='bold', family='monospace')

    ax.annotate("SILVER BULLET OBJECTIVE HIT (+3.12R)\n15+ Handles Secured Before 11:00 NY", 
                xy=(7, 5772), xytext=(5.5, 5782),
                arrowprops=dict(facecolor=GREEN_CANDLE, arrowstyle='->', lw=1.5),
                color=GREEN_CANDLE, fontsize=10, fontweight='bold', family='monospace')

    ax.set_xlim(0, 9)
    ax.set_ylim(5720, 5790)
    ax.set_ylabel("S&P 500 Index (US500)", color=MUTED_TEXT, fontsize=10)
    plt.tight_layout()
    for p in output_paths:
        fig.savefig(p, dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

# -----------------------------------------------------------------------------
# 5. INVERSION FVG & BALANCED PRICE RANGE (IV-01 & IV-02)
# -----------------------------------------------------------------------------
def generate_chart_5(output_paths):
    fig, ax = setup_chart_figure(
        "05. Inversion Fair Value Gap (IFVG) & Balanced Price Range",
        "Rules IV-01 (Inversion Support/Resistance Flip) & IV-02 (Balanced Price Range)",
        "RULE: IV-01 / IV-02"
    )

    draw_candle(ax, 1, 20120, 20135, 20115, 20130)
    draw_candle(ax, 2, 20130, 20140, 20080, 20085) # Initial Bearish FVG formed
    draw_candle(ax, 3, 20085, 20095, 20075, 20090)

    # Inversion: Price aggressively violates the bearish FVG to the upside!
    draw_candle(ax, 4, 20090, 20150, 20088, 20145) # Blows through gap!
    draw_candle(ax, 5, 20145, 20155, 20135, 20148)

    # Retest: Bearish FVG flips to BULLISH SUPPORT!
    draw_candle(ax, 6, 20148, 20150, 20132, 20140) # Taps flipped IFVG
    draw_candle(ax, 7, 20140, 20195, 20138, 20190) # Explosive expansion!
    draw_candle(ax, 8, 20190, 20220, 20185, 20215) # Target hit

    ifvg_rect = patches.Rectangle((1.5, 20095), 5.5, 20130 - 20095,
                                  facecolor=GOLD_ACCENT, alpha=0.15, edgecolor=GOLD_ACCENT,
                                  linestyle='--', linewidth=1.5, zorder=2)
    ax.add_patch(ifvg_rect)
    ax.text(1.7, 20110, "INVERSION FVG ZONE (20095 - 20130)\nBearish Gap Violated -> Flips To Support", 
            color=GOLD_ACCENT, fontsize=9, fontweight='bold', family='monospace')

    ax.annotate("GAP VIOLATED WITH DISPLACEMENT\nBearish FVG Disrespected (Polarity Flip)", 
                xy=(4, 20145), xytext=(2.2, 20170),
                arrowprops=dict(facecolor=CYAN_ACCENT, arrowstyle='->', lw=1.5),
                color=CYAN_ACCENT, fontsize=9.5, fontweight='bold', family='monospace')

    ax.annotate("IFVG SUPPORT RETEST ENTRY\nLong Limit Filled on Retest", 
                xy=(6, 20132), xytext=(4.5, 20065),
                arrowprops=dict(facecolor=GREEN_CANDLE, arrowstyle='->', lw=1.5),
                color=GREEN_CANDLE, fontsize=9.5, fontweight='bold', family='monospace')

    ax.annotate("BUY-SIDE LIQUIDITY EXPANSION (+3.40R)\nClean Institutional Target Purged", 
                xy=(8, 20215), xytext=(5.5, 20235),
                arrowprops=dict(facecolor=GREEN_CANDLE, arrowstyle='->', lw=1.5),
                color=GREEN_CANDLE, fontsize=10, fontweight='bold', family='monospace')

    ax.set_xlim(0, 9)
    ax.set_ylim(20050, 20250)
    ax.set_ylabel("Nasdaq 100 Index (NAS100)", color=MUTED_TEXT, fontsize=10)
    plt.tight_layout()
    for p in output_paths:
        fig.savefig(p, dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

if __name__ == '__main__':
    repo_dir = r"C:\Users\giant\Documents\ict-trader\docs\references\ict_charts"
    artifact_dir = r"C:\Users\giant\.gemini\antigravity\brain\b07f65d1-8dcb-4241-bae9-45fc96e41752"
    os.makedirs(repo_dir, exist_ok=True)
    os.makedirs(artifact_dir, exist_ok=True)
    
    charts = [
        (generate_chart_1, "01_ict_fvg_consequent_encroachment.png"),
        (generate_chart_2, "02_ict_liquidity_sweep_judas_swing.png"),
        (generate_chart_3, "03_ict_order_of_purging_rule_sw02.png"),
        (generate_chart_4, "04_ict_silver_bullet_execution_window.png"),
        (generate_chart_5, "05_ict_inversion_fvg_support_flip.png"),
    ]
    
    for fn, filename in charts:
        p1 = os.path.join(repo_dir, filename)
        p2 = os.path.join(artifact_dir, filename)
        fn([p1, p2])
        print(f"Generated {filename}")
