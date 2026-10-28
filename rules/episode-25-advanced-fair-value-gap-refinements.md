# Episode 25: 2022 ICT Mentorship Episode 25

**Source URL:** https://www.youtube.com/watch?v=CnTXwAuDi9Y

## Summary of Episode
In Episode 25, Michael J. Huddleston (ICT) demonstrates the 2022 mentorship model applied to the E-mini S&P 500 Futures (ES, June 2022 contract) for Tuesday, May 10, 2022. He establishes the top-down narrative starting on the daily chart, highlighting the seasonal bearish tendency of May, a daily bearish order block, and targets resting at sell-side liquidity below prior swing lows. 

He introduces the concept of daily rebalancing: when Monday produces an extended large-range down day, Tuesday can open and retrace upward to rebalance the range by reaching back to Friday's daily low before resuming the downward trend. He explains how the algorithm initiates price movement at 08:30 AM New York time and delivers the Judas Swing manipulation at the 09:30 AM equity open into buy-side liquidity and Friday's low. He then illustrates the multi-timeframe execution process: identifying the displacement leg on a 5-minute chart, measuring equilibrium (50%) to ensure entries are taken only in a Premium, stepping down through lower timeframes (5m, 4m, 3m, 2m) until a valid Fair Value Gap (FVG) is located, setting initial stops and trailing rules, and targeting sell-side liquidity below the previous day's low into the London Close/Lunch window.

---

## Concrete Trading Rules

### Session / Killzone & Timing Rules
- RULE: The true trading day is defined and measured starting from midnight New York time (00:00 NY / Eastern Standard Time).
  - CATEGORY: session/killzone
  - NUMBERS: 00:00 (Midnight) New York time.
  - SOURCE: 26:00–26:25 (SAID and SHOWED on chart).
  - CLARITY: Clear.

- RULE: At 08:30 AM New York time (when the morning economic news embargo is lifted), the algorithm begins spooling and seeking liquidity.
  - CATEGORY: news / session/killzone
  - NUMBERS: 08:30 AM New York time.
  - SOURCE: 34:06–34:18, 40:08–40:18 (SAID and SHOWED on chart).
  - CLARITY: Clear.

- RULE: At 09:30 AM New York time (US Equity market open), the primary Judas Swing manipulation occurs, driving price into opposite liquidity before distributing in the intended direction.
  - CATEGORY: session/killzone
  - NUMBERS: 09:30 AM New York time.
  - SOURCE: 27:10–27:24, 34:32–34:40, 43:32–43:40 (SAID and SHOWED on chart).
  - CLARITY: Clear.

### Reference Level & Daily Range Rules
- RULE: When analyzing daily candles, traders must study the open, high, low, and close of the trailing three days.
  - CATEGORY: reference level
  - NUMBERS: 3 trailing trading days.
  - SOURCE: 20:09–20:16 (SAID).
  - CLARITY: Clear.

- RULE: If the previous day (e.g., Monday) was a large-range trending down day closing near its low, the next trading day can open and rally to rebalance Monday's range back up to the day prior to Monday's low (Friday's low) before continuing lower.
  - CATEGORY: reference level
  - NUMBERS: Trailing day 2 low (Friday's low).
  - SOURCE: 21:56–22:25, 27:10–27:24, 34:24–34:32 (SAID and SHOWED on chart).
  - CLARITY: Clear.

- RULE: In a bearish order block, the candle high is the invalidation threshold and should not be pierced.
  - CATEGORY: reference level
  - NUMBERS: Candle high price.
  - SOURCE: 08:00–08:18 (SAID and SHOWED on chart).
  - CLARITY: Clear.

### Order of Liquidity Purging & Bias Confirmation
- RULE: In a bearish market bias, price must run buy-side liquidity (or an old high/rebalance level) FIRST before running sell-side liquidity.
  - CATEGORY: sweep / confirmation
  - NUMBERS: Not stated.
  - SOURCE: 28:36–29:05 (SAID and SHOWED on chart).
  - CLARITY: Clear.

- RULE: If price takes out the previous day's low or sell-side liquidity FIRST and then rallies, the price action is NOT bearish and cancels a short setup.
  - CATEGORY: confirmation / filter
  - NUMBERS: Previous day low.
  - SOURCE: 28:40–28:51 (SAID).
  - CLARITY: Clear.

### Entry Rules
- RULE: To take a short entry, calculate the Fibonacci retracement from the swing high to the swing low of the displacement leg; an entry is ONLY permitted at or above the 50% equilibrium level (in Premium).
  - CATEGORY: entry
  - NUMBERS: $\ge 50\%$ (Equilibrium/Premium threshold).
  - SOURCE: 36:44–36:53, 38:43–39:02 (SAID and SHOWED on chart).
  - CLARITY: Clear.

- RULE: If a higher timeframe (e.g., 5-minute, 4-minute, 3-minute) displacement does not present an FVG in the Premium zone ($\ge 50\%$), drill down step-by-step through lower timeframes (5m $\to$ 4m $\to$ 3m $\to$ 2m $\to$ 1m) until an FVG is found above the 50% equilibrium level.
  - CATEGORY: entry
  - NUMBERS: Timeframes 5m, 4m, 3m, 2m, 1m; threshold $\ge 50\%$.
  - SOURCE: 36:18–36:26, 37:30–37:34, 40:24–40:28, 40:53–41:20 (SAID and SHOWED on chart).
  - CLARITY: Clear.

### Stop Loss Placement Rules
- RULE: For a standard/aggressive short stop loss, place the stop 1 to 2 ticks above the high of the candle that formed the top of the Fair Value Gap (Candle 1 high in the 3-candle sequence).
  - CATEGORY: stop loss
  - NUMBERS: 1 to 2 ticks above Candle 1 high.
  - SOURCE: 42:15–42:25, 43:35–43:45 (SAID and SHOWED on chart).
  - CLARITY: Clear.

- RULE: For a conservative/ample stop loss, place the stop above the swing high (the high of the day / Judas Swing high).
  - CATEGORY: stop loss
  - NUMBERS: Above swing high of the day.
  - SOURCE: 43:45–43:55 (SAID and SHOWED on chart).
  - CLARITY: Clear.

### Trade Management & Trailing Stop Rules
- RULE: Do not trail the stop loss tight immediately upon price moving into profit.
  - CATEGORY: trade management
  - NUMBERS: Not stated.
  - SOURCE: 42:47–42:54, 43:24–43:30 (SAID).
  - CLARITY: Clear.

- RULE: Only trail the stop loss lower after a larger market structure shift occurs (a significant intermediate swing low is broken to the downside). Once that swing low breaks, move the stop down to above the entry FVG or the new lower intermediate swing high.
  - CATEGORY: trade management
  - NUMBERS: Not stated.
  - SOURCE: 44:50–45:15 (SAID and SHOWED on chart).
  - CLARITY: Clear.

### Take Profit / Exit Rules
- RULE: Take partial profits below initial short-term lows, and place the main terminal take profit at sell-side liquidity resting below the previous day's low.
  - CATEGORY: take profit
  - NUMBERS: Previous day's low.
  - SOURCE: 28:09–28:22, 38:08–38:22 (SAID and SHOWED on chart).
  - CLARITY: Clear.

- RULE: In index futures day trading, the target delivery is ideally expected to be reached by 12:00 PM (Noon) New York time, though acceptable delivery can extend into the lunch window up to approximately 12:30 PM.
  - CATEGORY: take profit / session/killzone
  - NUMBERS: 12:00 PM to 12:30 PM New York time.
  - SOURCE: 49:05–49:33 (SAID).
  - CLARITY: Clear.

### Risk and Position Sizing Rules
- RULE: If market volatility requires a stop distance that exceeds risk parameters on standard contracts (e.g., E-mini S&P at $50/point), scale down to Micro contracts (e.g., Micro E-mini S&P at $5/point) rather than placing an inappropriately tight stop.
  - CATEGORY: risk/position size
  - NUMBERS: Micro futures ($5/point) vs. standard E-mini ($50/point).
  - SOURCE: 43:56–44:31 (SAID).
  - CLARITY: Clear.

### Seasonality Rules
- RULE: In US Equity Index Futures and stocks, the month of May historically exhibits a bearish seasonal tendency, typically beginning in the final week of April and extending through May.
  - CATEGORY: general principle
  - NUMBERS: End of April through the month of May.
  - SOURCE: 11:10–12:33 (SAID).
  - CLARITY: Clear.

---

## Chart Examples

### Chart Example: E-mini S&P 500 Futures (June 2022 Contract)
- **Timestamp:** 06:52–59:00
- **Instrument:** E-mini S&P 500 Futures (ESM2022)
- **Timeframe:** Daily $\to$ 1-Hour $\to$ 15-Minute $\to$ 5-Minute $\to$ 4-Minute $\to$ 3-Minute $\to$ 2-Minute
- **Date/Time:** Tuesday, May 10, 2022 (NY Session 08:30 AM to 12:30 PM NY)
- **Reference Levels identified:**
  - Daily bearish order block from late April (high kept intact).
  - Friday, May 6 low (red horizontal line on charts) acting as the daily rebalance level.
  - Relative equal highs from Monday afternoon/overnight acting as buy-side liquidity pool.
  - Monday, May 9 low acting as the primary sell-side liquidity pool.
- **Liquidity Sweep / Price Action:**
  - Monday (May 9) dropped aggressively, creating a large-range down day.
  - Tuesday (May 10) opened at midnight NY. At 08:30 AM, price spooled higher.
  - At 09:30 AM NY equity open, price executed a Judas Swing rally taking out the relative equal highs (buy-side liquidity) and tapping precisely into Friday's low.
  - Price displaced downward from 4065 down through multiple short-term lows to 4024.
- **Entry point / trigger:**
  - On the 5m, 4m, and 3m charts, no valid FVG formed in the Premium zone above the 50% equilibrium mark (4044.50).
  - On the 2-minute chart (at 41:14), an FVG formed above equilibrium (Premium) between ~4048 and 4053 following the break of a short-term low. Entry triggered on the retracement into this 2-minute FVG.
- **Stop Loss placement:**
  - Aggressive: 1–2 ticks above the candle 1 high of the 2-minute FVG (~4057.50).
  - Conservative: Above the high of the day / Judas Swing high (4065.00).
- **Target / Take Profit:**
  - Partials taken below the first intraday low.
  - Terminal target at sell-side liquidity resting below Monday's low (delivered at ~12:27 PM NY time).
- **Outcome:** Clean sell-off distributing down through Monday's low into the lunch window without breaching the stop.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)

1. **Do not sell in Discount:** A short setup is canceled/invalidated if the entry trigger or FVG does not reside at or above the 50% equilibrium level of the displacement leg (must be in Premium).
2. **Wrong liquidity sequence:** If price sweeps sell-side liquidity (or takes the previous day's low) FIRST during a supposed bearish day, the bearish Judas Swing short model is invalidated.
3. **Premature stop trailing:** Do not move the stop loss to break-even or trail it tightly until a major market structure shift (breaking a significant swing low) has confirmed.
4. **Trying to pick bottoms/tops:** Do not attempt to catch falling knives or buy extreme lows based on "oversold" indicator readings during a bearish daily narrative.
5. **Trading illiquid sessions:** Do not force this setup in illiquid times like the Asian session on index futures or non-Asia forex pairs.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
- **Forex vs. Indices:** ICT explicitly states that everything taught regarding this model works identical in Forex as it does in Index Futures (07:18–07:27).
- **Asian Session Specifics:** ICT notes that the model does not form as frequently or reliably in the Asian session due to illiquidity. However, if trading Forex during the Asian session, traders should restrict their focus to Yen pairs (JPY), New Zealand Dollar (NZD), and Australian Dollar (AUD) pairs, where local session volume provides sufficient movement (46:00–46:40).
- **Gold (XAUUSD):** None mentioned in this episode.

---

## Ambiguities and Open Questions

1. **Equilibrium Retracement Measurement:** In multi-stage displacement legs that break multiple swing lows, does the 50% equilibrium level strictly anchor from the absolute absolute session high down to the lowest point of the displacement run before the retracement, or does it re-anchor if additional lower lows are made before the FVG is tapped?
2. **Drill-Down Priority:** If a 1-minute chart has an FVG in Premium and the 2-minute also has an FVG in Premium, does the algorithm prioritize the higher-timeframe 2m FVG, or does it take the first touch of the 1m FVG?
3. **Execution Limit vs. Market:** While ICT displays limit orders at the FVG boundary, does he permit entering on market execution upon FVG touch, or does the order require limit placement at the top/bottom boundary?
