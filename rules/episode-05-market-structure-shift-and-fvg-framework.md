# Episode 05: 2022 ICT Mentorship Episode 5

**Source URL:** https://www.youtube.com/watch?v=N29ZJ-o31xs

## Summary of Episode
This episode focuses on understanding intraday order flow and the mechanics of the daily range. Michael J. Huddleston (ICT) outlines the exact timing structures of the trading day, specifically for Index Futures (ES and NQ). He explains how to transition between contract delivery months using barchart.com to track volume and open interest. He introduces the daily time bands—including the Morning Session, the strict Lunch Hour No-Trade Zone, and the Afternoon Session—and details how algorithms deliver price within these parameters. Additionally, he defines the structural definitions of Swing Highs and Swing Lows, the three-drives stop-hunt pattern, the concept of sharp "displacement" (using the elephant in a kiddie pool analogy), and how to execute trades using Fair Value Gaps (FVGs) on 5-minute and 1-minute charts.

---

## Concrete Trading Rules

### RULE 1: Index Futures Contract Roll-over Selection
- **RULE:** Trade only the contract delivery month that holds the largest open interest; track this on barchart.com starting one week prior to the delivery month's expiration (the third Friday of March, June, September, and December).
- **CATEGORY:** Risk/position size / General principle.
- **NUMBERS:** Expiration occurs on the 3rd Friday of March (H), June (M), September (U), and December (Z). Roll over 1 week prior when the next contract's open interest exceeds the front month.
- **SOURCE:** [02:05 - 05:40] (Said and shown on web browser/chart).
- **CLARITY:** Clear.

### RULE 2: Chart Time Zone Calibration
- **RULE:** Always calibrate the charting platform's time zone strictly to New York local time (EST/EDT) to ensure algorithm time alignments are accurate.
- **CATEGORY:** Session/killzone.
- **NUMBERS:** New York Time (UTC-5 or UTC-4 depending on Daylight Saving Time).
- **SOURCE:** [09:00 - 09:45] (Said and shown on chart).
- **CLARITY:** Clear.

### RULE 3: Morning Session Execution Band
- **RULE:** The Morning Session run begins at 8:30 AM New York time (due to high-impact economic news releases) and extends to 12:00 PM (noon), with new trade entries preferred before 11:00 AM.
- **CATEGORY:** Session/killzone.
- **NUMBERS:** 8:30 AM to 12:00 PM New York Time. Preference to be positioned prior to 11:00 AM.
- **SOURCE:** [08:04 - 08:45], [10:50 - 11:20] (Said and shown on chart).
- **CLARITY:** Clear.

### RULE 4: Strict Lunch No-Trade Zone
- **RULE:** Do not execute any trade entries or demo practices between the hours of 12:00 PM (noon) and 1:00 PM New York time under any circumstances.
- **CATEGORY:** Session/killzone / Trade management.
- **NUMBERS:** 12:00 PM to 1:00 PM New York Time.
- **SOURCE:** [10:00 - 10:20] (Said and shown on chart).
- **CLARITY:** Clear.

### RULE 5: Afternoon Session Execution Band
- **RULE:** The Afternoon Session trading window begins at 1:30 PM New York Time (prompted by a 1:30 PM algorithmic macro release) and runs until the equity close at 4:00 PM.
- **CATEGORY:** Session/killzone.
- **NUMBERS:** 1:30 PM to 4:00 PM New York Time.
- **SOURCE:** [08:45 - 08:54], [22:25 - 22:42] (Said and shown on chart).
- **CLARITY:** Clear.

### RULE 6: Swing High Structural Definition
- **RULE:** A Swing High is defined strictly as a three-candle pattern where the middle candle possesses a high that is higher than both the candle to its immediate left and the candle to its immediate right (candle body color/close does not matter).
- **CATEGORY:** Reference level.
- **NUMBERS:** 3-candle pattern.
- **SOURCE:** [14:23 - 14:44] (Said and shown on chart).
- **CLARITY:** Clear.

### RULE 7: Swing Low Structural Definition
- **RULE:** A Swing Low is defined strictly as a three-candle pattern where the middle candle possesses a low that is lower than both the candle to its immediate left and the candle to its immediate right (candle body color/close does not matter).
- **CATEGORY:** Reference level.
- **NUMBERS:** 3-candle pattern.
- **SOURCE:** [14:45 - 15:02] (Said and shown on chart).
- **CLARITY:** Clear.

### RULE 8: Key Reference Level Selection (Morning Session)
- **RULE:** Prior to the 8:30 AM New York open, identify the most obvious, significant Swing High and Swing Low on the 15-minute chart to serve as your liquidity boundary lines.
- **CATEGORY:** Reference level.
- **NUMBERS:** 15-minute timeframe, levels marked prior to 8:30 AM New York Time.
- **SOURCE:** [14:02 - 14:22] (Said and shown on chart).
- **CLARITY:** Clear.

### RULE 9: Key Reference Level Selection (Afternoon Session)
- **RULE:** Prior to the 1:30 PM New York macro window, identify the nearest Swing High and Swing Low on the 15-minute chart (often formed during late morning or the lunch hour) to act as target liquidity pools.
- **CATEGORY:** Reference level.
- **NUMBERS:** 15-minute timeframe, levels marked prior to 1:30 PM New York Time.
- **SOURCE:** [22:54 - 23:15], [25:54 - 26:10] (Said and shown on chart).
- **CLARITY:** Clear.

### RULE 10: Displacement and Fair Value Gap Execution
- **RULE:** Trade entries are valid only when price sweeps a mapped liquidity level and immediately produces a sharp, aggressive displacement leg in the opposite direction, leaving behind a 5-minute or 1-minute Fair Value Gap (FVG); enter a position when price retraces back into this FVG.
- **CATEGORY:** Entry.
- **NUMBERS:** 5-minute or 1-minute chart.
- **SOURCE:** [18:18 - 19:18] (Said and shown on chart).
- **CLARITY:** Clear.

---

## Chart Examples

### Example 1: E-mini S&P 500 Futures (ES) - Morning Session
- **Timestamp:** [14:00 - 15:30] (15-min Setup), [20:30 - 21:30] (5-min Execution)
- **Instrument:** ES (E-mini S&P 500 Futures)
- **Timeframe:** 15-minute and 5-minute
- **Date/Time (if visible):** February 1, 2022
- **Reference Levels identified:** Pre-8:30 AM Swing High (4514.50) and Swing Low (4481.50).
- **Liquidity Sweep / Price Action:** Price did not run straight up to the 15-minute high; instead, it formed three progressively higher short-term highs (Three Drives/Three Little Indians pattern) creeping up to the old high, building buy-side liquidity above them.
- **Entry point / trigger:** Price sweeps above these short-term highs near 4514.50, then aggressively breaks down (displacement). This sharp displacement creates a bearish FVG on the 5-minute chart. The entry trigger is a short position when price trades back up into the 5-minute FVG.
- **Stop Loss placement:** Not explicitly calculated on this chart, but implied above the high of the displacement move.
- **Target / Take Profit:** Sell-side liquidity resting below the pre-8:30 AM 15-minute Swing Low (4481.50).
- **Outcome:** Price falls rapidly during the morning session and successfully cleans out the sell-side liquidity target before the lunch hour.

### Example 2: E-mini Nasdaq-100 Futures (NQ) - Afternoon Session
- **Timestamp:** [27:18 - 28:44] (5-min Setup), [28:45 - 29:38] (1-min Execution)
- **Instrument:** NQ (E-mini Nasdaq-100 Futures)
- **Timeframe:** 5-minute and 1-minute
- **Date/Time (if visible):** February 1, 2022
- **Reference Levels identified:** PM Session Swing Low (formed around 14:02) and relative equal highs to the left.
- **Liquidity Sweep / Price Action:** At 14:21, the market aggressively sweeps below the 14:02 swing low to run sell stops.
- **Entry point / trigger:** Immediately after sweeping the low, NQ shows a sharp, energetic displacement higher. Michael switches to the 1-minute chart to locate the newly created bullish FVG. The entry trigger is a long trade executed directly inside this 1-minute FVG.
- **Stop Loss placement:** Implied below the swing low swept at 14:21.
- **Target / Take Profit:** The buy-side liquidity resting above the relative equal highs.
- **Outcome:** Price surges aggressively upward, clearing out all buy-side liquidity targets into the afternoon equity close.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)
1. **No-Trade Time Filter:** Do not trade or practice demo setups between 12:00 PM and 1:00 PM New York Time (the Lunch Hour).
2. **Anemic Price Actions:** If the market runs above/below a key high/low but displays a weak, lazy, or slow reaction (no sharp displacement), the setup is invalidated. Do not trade sluggish reversals.
3. **No Retrace, No Trade:** If price sweeps liquidity and displaces aggressively but fails to pull back into the FVG, do not chase the market. If there is no retrace into the FVG, there is no trade.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
- **Indices vs. Forex Pairs:** Michael explicitly states that Asian Range trading concepts (popular in Forex) do **not** apply to Index Futures (ES/NQ/YM). 
- **Market Predictability:** He notes that Forex pairs can occasionally display "funky," vulgar, or ruthless delivery behavior due to interbank conditions. Index futures, by contrast, are more structurally clean and systematically handled by algorithms because they are heavily traded by large institutions and professionals.

---

## Ambiguities and Open Questions
1. **Daily Bias Determination:** Michael mentions that daily bias is the foundation for selecting the morning/afternoon trade direction but states that the rules to define daily bias will be taught in detail "next week" (subsequent episodes).
2. **Algorithmic Macros:** He notes that an algorithmic macro starts running at 1:30 PM New York Time but states that the inner workings of this macro are "beyond the scope of this mentorship," leaving the exact code of the macro open.
