# Episode 04: 2022 ICT Mentorship Episode 4

**Source URL:** https://www.youtube.com/watch?v=L-ReMHiavPM

## Summary of Episode
This episode focuses on the practical application of the market structure concepts introduced in Episode 3, specifically analyzing **Internal Range Liquidity** and **Market Structure Shifts (MSS)**. Michael J. Huddleston ("ICT") walks through historical chart examples of the E-mini S&P 500 (ES) and E-mini Nasdaq 100 (NQ) futures. The core lesson demonstrates how to identify a valid dealing range, locate premium and discount zones, wait for buy-side liquidity sweeps after a specific time filter, confirm a shift in market structure with a concurrent Fair Value Gap (FVG), and execute short trades targeting discount targets.

---

## Concrete Trading Rules

### Rule 1: Time Filter for Trade Hunting
* **RULE:** The search for liquidity sweeps and setup configurations (referred to as "the hunt") begins strictly at 08:30 AM New York time.
* **CATEGORY:** session/killzone
* **NUMBERS:** 08:30 AM New York time (EST/EDT).
* **SOURCE:** Timestamp ~03:05 - 03:11 (SAID and SHOWED).
* **CLARITY:** Clear.

### Rule 2: Timeframe Hierarchy
* **RULE:** Start technical analysis on the 5-minute timeframe to identify the overall structure, and work down to lower timeframes (such as the 2-minute) to find precise entry patterns.
* **CATEGORY:** general principle
* **NUMBERS:** 5-minute and 2-minute timeframes.
* **SOURCE:** Timestamp ~06:12 - 06:17 (SAID).
* **CLARITY:** Clear.

### Rule 3: Defining the Dealing Range and Equilibrium
* **RULE:** A trade setup must be framed within an active dealing range, defined by a distinct swing low and swing high. A Fibonacci retracement tool must be anchored from this low to high to determine the 50% Equilibrium level; short positions must only be established in the Premium zone (above 50%) and targets must reside in the Discount zone (below 50%).
* **CATEGORY:** reference level
* **NUMBERS:** 50% (Equilibrium).
* **SOURCE:** Timestamp ~01:17 - 01:25 and ~02:27 - 02:37 (SAID and SHOWED).
* **CLARITY:** AMBIGUOUS. The exact programmatic definition of what constitutes the "major" swing high and swing low to anchor the Fibonacci tool is not defined mechanically; he states "you'll see why I picked that low... because it's the low."

### Rule 4: Liquidity Sweep Requirement
* **RULE:** For a bearish setup, price must sweep Buy-side Liquidity resting above a short-term high established prior to 08:30 AM New York time before looking for a sell trigger.
* **CATEGORY:** sweep
* **NUMBERS:** High established before 08:30 AM.
* **SOURCE:** Timestamp ~03:11 - 03:15 (SAID and SHOWED).
* **CLARITY:** Clear.

### Rule 5: Market Structure Shift (MSS) with Displacement and FVG
* **RULE:** A bearish Market Structure Shift is validated only when a displacement candle closes below a prior short-term swing low and simultaneously leaves a Fair Value Gap (FVG) within the displacement leg.
* **CATEGORY:** confirmation
* **NUMBERS:** Not stated (no minimum tick or point value specified for the displacement or FVG).
* **SOURCE:** Timestamp ~01:38 - 01:54 and ~03:20 - 03:34 (SAID and SHOWED).
* **CLARITY:** Clear.

### Rule 6: Execution Entry Trigger
* **RULE:** Enter a short position at the open (or within the boundary) of the newly formed 2-minute or 5-minute Fair Value Gap (FVG) when price retraces back up into it.
* **CATEGORY:** entry
* **NUMBERS:** Not stated.
* **SOURCE:** Timestamp ~03:27 - 03:37 (SAID and SHOWED).
* **CLARITY:** Clear.

### Rule 7: Target Selection (Take Profit)
* **RULE:** The primary profit targets must be identified in the Discount zone (below the 50% Equilibrium level of the dealing range), targeting either internal range liquidity (imbalances/FVGs) or old swing lows.
* **CATEGORY:** take profit
* **NUMBERS:** Must be below the 50% Equilibrium level.
* **SOURCE:** Timestamp ~02:31 - 02:52 (SAID and SHOWED).
* **CLARITY:** Clear.

---

## Chart Examples

### Example 1: E-mini S&P 500 Futures (ES)
* **Timestamp:** ~00:25 - 06:05
* **Instrument:** E-mini S&P 500 Futures (March 2022 Contract)
* **Timeframe:** 2-minute (2 min)
* **Date/Time (if visible):** Wednesday, January 26, 2022
* **Reference Levels identified:** Swing Low at ~03:00, Swing High at ~10:00, 50% Equilibrium level, and Buy-side Liquidity level (pre-08:30 AM high).
* **Liquidity Sweep / Price Action:** Price rallies above the pre-08:30 AM high to sweep buy-side liquidity. It attempts a structure shift but fails to create an FVG (invalidating the first shift). Price rallies again to form a higher high, then displaces aggressively downward, closing below a short-term swing low and leaving a clear 2-minute FVG.
* **Entry point / trigger:** Price retraces back up into the 2-minute FVG (around 4419).
* **Stop Loss placement:** Not explicitly defined with a strict mechanical rule in the audio, though visually implied above the swing high (the 4429/4430 area).
* **Target / Take Profit:** A discount old swing low below the 50% equilibrium level (around 4382).
* **Outcome:** Price falls cleanly into the target at 4382.

### Example 2: E-mini Nasdaq 100 Futures (NQ)
* **Timestamp:** ~06:06 - 08:11
* **Instrument:** E-mini Nasdaq 100 Futures (March 2022 Contract)
* **Timeframe:** 5-minute (5 min)
* **Date/Time (if visible):** Thursday, January 27, 2022
* **Reference Levels identified:** Buy-side Liquidity (relatively equal highs), Swing Low, Swing High, 50% Equilibrium level, and Discount targets.
* **Liquidity Sweep / Price Action:** Price sweeps Buy-side Liquidity resting above relatively equal highs after 08:30 AM. A structural break occurs but fails to create an FVG, so it is skipped. Price pushes higher once more, then displaces down, breaking a short-term swing low and leaving a 5-minute FVG.
* **Entry point / trigger:** Retracement back up into the 5-minute FVG (marked as FVG on the chart).
* **Stop Loss placement:** Not explicitly defined, visually implied above the high.
* **Target / Take Profit:** Multiple discount targets: an old low, intermediate swing lows, and a discount FVG/imbalance.
* **Outcome:** Price moves directly into all discount targets.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)
* **No FVG Filter:** If a market structure shift occurs (price closes below a short-term swing low) but **no Fair Value Gap** is left behind by the displacement leg, the setup is immediately invalidated. You must wait for another run-up and structure shift that does produce an FVG.
* **Premature Trading:** Do not look for setups or execute entries before the 08:30 AM New York time filter is met.
* **Forcing Setups:** Do not force trades or assume a setup is present if the exact structural signatures (Sweep $\rightarrow$ MSS $\rightarrow$ FVG $\rightarrow$ Return to FVG $\rightarrow$ Target in Discount) are missing: *"You can't force it, you can't think it's there; it's there or it's not."*

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
* **None mentioned in this episode.** The principles are demonstrated exclusively on Index Futures (E-mini S&P 500 and E-mini Nasdaq 100).

---

## Ambiguities and Open Questions
1. **Mechanical Swing Identification:** The exact programmatic definition of the major swing high and swing low used to anchor the Fibonacci tool for Equilibrium (50%) is highly subjective. To code this, an algorithm requires strict parameters (e.g., a fractal swing definition, session-high/low boundaries, or specific candle-back lookbacks).
2. **Stop Loss Rule:** The lesson does not specify the precise, rule-based placement for the stop loss. An algorithmic implementation must determine whether to place the stop loss above the high of the displacement candle, the swing high of the sweep, or the high of the first candle in the FVG three-candle formation.
