# Episode 11: 2022 ICT Mentorship Episode 11

**Source URL:** https://www.youtube.com/watch?v=Sqw2bww93Zo

---

## Summary of Episode
In this episode, Michael J. Huddleston (ICT) reviews a live short trade executed on the E-mini Nasdaq 100 Index Futures (NQ). He breaks down the structural framework from the daily chart down to the 3-minute chart, demonstrating how to align higher-timeframe bearish targets with precise lower-timeframe execution. 

Key concepts covered include:
* The structural distinction between the New York Midnight opening price (for daily range profiling) and the 8:30 AM New York opening price (for morning session profiling).
* Market structure validation using nested swing highs (short-term, intermediate-term, and long-term), referencing principles adapted from Larry Williams.
* Post-trade psychological discipline, specifically avoiding the urge to "push your edge" (overtrade) after a significant profitable trade, utilizing a demo account as a behavioral filter during low-probability holiday market conditions.
* Live account execution verification within TD Ameritrade's thinkorswim platform.

---

## Concrete Trading Rules

### RULE 1: Session Opening Price Reference Selection
* **RULE:** When analyzing the entire daily range profile, the algorithmic system must reference the New York Midnight opening price; when analyzing specifically the New York morning session profile, the system must reference the 8:30 AM New York opening price.
* **CATEGORY:** reference level
* **NUMBERS:** 
  * New York Midnight (00:00 EST/EDT) for daily range profiling.
  * 8:30 AM New York time (08:30 EST/EDT) for morning session profiling.
* **SOURCE:** 07:33 - 07:56. SAID.
* **CLARITY:** CLEAR.

### RULE 2: Mechanical Definition of a Swing High
* **RULE:** A swing high is validated only when a central candle achieves a high that is strictly higher than the high of the candle immediately to its left and strictly higher than the high of the candle immediately to its right.
* **CATEGORY:** reference level
* **NUMBERS:** 3-candle sequence (1 left, 1 center, 1 right).
* **SOURCE:** 13:58 - 14:09. SAID.
* **CLARITY:** CLEAR.

### RULE 3: Validation of an Intermediate-Term Swing High
* **RULE:** An Intermediate-Term Swing High is validated when a confirmed swing high (the central swing high) is flanked on both its left and right by confirmed swing highs that have lower peak absolute prices than the central swing high.
* **CATEGORY:** reference level
* **NUMBERS:** Requires a minimum of three distinct, sequential swing highs.
* **SOURCE:** 10:31 - 11:15 and 14:41 - 15:10. SAID and SHOWED on NQ 3-minute chart.
* **CLARITY:** CLEAR.

### RULE 4: Premium-Only Bearish Execution
* **RULE:** When the higher timeframe bias is bearish, the system is only permitted to initiate short positions above the session's opening price (i.e., inside a Premium market state).
* **CATEGORY:** entry
* **NUMBERS:** Above the New York 8:30 AM opening price for New York morning session setups.
* **SOURCE:** 07:11 - 07:23 and 08:08 - 08:21. SAID and SHOWED on NQ 5-minute chart.
* **CLARITY:** CLEAR.

### RULE 5: Execution in Volatile Conditions (Wick Disregard)
* **RULE:** During volatile market conditions, lower-timeframe candle bodies should be used to confirm structural support/resistance holding within a Fair Value Gap (FVG), while candle wicks (high/low extremes) can be disregarded if they exceed the gap boundaries.
* **CATEGORY:** trade management
* **NUMBERS:** Not stated.
* **SOURCE:** 08:59 - 09:19. SAID and SHOWED on NQ 5-minute and 4-minute charts.
* **CLARITY:** AMBIGUOUS. The exact allowable distance a wick may "color outside the lines" before the setup is mathematically invalidated is not quantified.

### RULE 6: Early Session Halts on US Bank Holidays
* **RULE:** On officially designated US Bank Holidays, live session trading must cease at 1:00 PM New York time and can only resume at 6:00 PM New York time.
* **CATEGORY:** session/killzone
* **NUMBERS:** Halt at 1:00 PM New York Time; resume at 6:00 PM New York Time.
* **SOURCE:** 04:15 - 04:25. SAID.
* **CLARITY:** CLEAR.

---

## Chart Examples

### Example 1: E-mini Nasdaq 100 Index Futures (NQ) Live Short Trade
* **Timestamp:** 02:56 - 06:15 (Theoretical breakdown) and 17:08 - 19:35 (Live statement/execution proof).
* **Instrument:** E-mini Nasdaq 100 Index Futures (NQ - March 2022 Contract).
* **Timeframe:** 1-Hour, 15-Minute, 5-Minute, 4-Minute, 3-Minute.
* **Date/Time:** Friday, February 18, 2022 (Execution at approximately 10:33 AM NY time).
* **Reference Levels identified:** 
  * 1-Hour Fair Value Gap (High: ~14,200, Low: ~14,050).
  * Key Daily Support Level/Old Daily Low (marked as a green horizontal line at ~13,700).
* **Liquidity Sweep / Price Action:** Price swept the stops above Friday morning's short-term high, filled the upper-timeframe bearish imbalance (FVG), and then displayed aggressive displacement lower.
* **Entry point / trigger:** Short entry executed at **13,858.25** inside the 3-minute FVG at 10:33 AM NY Time, once the price tested the upper boundary of the FVG.
* **Stop Loss placement:** Set above the validated Intermediate-Term Swing High (~13,910).
* **Target / Take Profit:** Exit targeted below the key daily support level (sell-side liquidity pool).
* **Outcome:** Profitable. Executed live fill to buy to cover at **13,612.25**, capturing 246.00 points ($4,920 profit per contract). Realized account statement shown live at 17:48.

### Example 2: New York AM Session Sell Model (Tuesday Session Setup)
* **Timestamp:** 04:58 - 05:19 and 14:15 - 15:19.
* **Instrument:** E-mini Nasdaq 100 Index Futures (NQ - March 2022 Contract).
* **Timeframe:** 3-Minute.
* **Date/Time:** Tuesday, February 22, 2022.
* **Reference Levels identified:** 9:30 AM Equities Open Price, relative equal lows resting below the pre-market low.
* **Liquidity Sweep / Price Action:** At 9:30 AM NY equities opening, price rallied up to sweep buy-side liquidity above an existing short-term high, then aggressively displaced down.
* **Entry point / trigger:** Sell short inside the newly created 3-minute FVG as price retraced back up to retest it.
* **Stop Loss placement:** Set above the newly formed high of the 9:30 AM liquidity sweep candle.
* **Target / Take Profit:** The sell-side liquidity pool resting beneath the relative equal lows.
* **Outcome:** Profitable. Price aggressively expanded downward through the targeted sell-side liquidity levels.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)

1. **Pre-Session Target Sweep:** If the targeted sell-side liquidity (key Daily Low / support level) is completely swept and cleared *before* the New York morning session opens, the short setup is invalidated. Price must not run to the target prematurely during the overnight session.
2. **Post-Win Live Trading (Overtrading Filter):** After capturing a major daily target/high-handle trade on a live account, live trading must be deactivated for the remainder of the session or day. To prevent emotional trade-back, any subsequent setups must only be executed on a demo account.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
* **Index Futures Session Halts:** Holiday session specifics (closes at 1:00 PM, resumes at 6:00 PM NY time) are highlighted specifically for CME Index Futures. 
* No other distinct rules comparing Forex or Gold are mentioned in this episode.

---

## Ambiguities and Open Questions

1. **Quantification of "Coloring Outside the Lines":** The video notes that wicks can exceed the boundaries of a Fair Value Gap under highly volatile conditions without invalidating the setup, but it does not specify a quantitative threshold (in points or ticks) for when a wick extension represents a true invalidation or stop sweep.
2. **Stop Loss Buffer:** While ICT shows the stop loss placed structurally above the intermediate-term swing high, he does not define a standard mathematical buffer (e.g., 2 ticks, 5 points, etc.) above the high of that candle to account for broker spread or slippage.
