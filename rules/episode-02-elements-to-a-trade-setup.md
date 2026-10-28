# Episode 02: Episode 2: Elements To A Trade Setup

**Source URL:** [https://www.youtube.com/watch?v=tmeCWULSTHc](https://www.youtube.com/watch?v=tmeCWULSTHc)

---

## Summary of Episode
In this episode, Michael J. Huddleston ("ICT") introduces the core framework of his 2022 Mentorship model, focusing specifically on Index Futures (E-mini Nasdaq-100). He outlines a structured, top-down approach to setting up a trade. The process starts at the macro level (determining Weekly Bias) and scales down to execution timeframes (1-minute, 2-minute, or 3-minute charts). Key topics covered include the definition of Premium vs. Discount, identifying engineered liquidity pools (buy stops and sell stops), detecting a lower-timeframe Market Structure Break (MSB), and identifying a Fair Value Gap (FVG) as the execution trigger.

---

## Concrete Trading Rules

### Rule 1: Weekly Bias Selection
- **RULE:** Before a new trading week begins, determine whether the next weekly candle is more likely to expand higher or expand lower based on macro factors, market tone, and seasonality (predicting candle expansion direction, not its closing price).
- **CATEGORY:** General principle / reference level.
- **NUMBERS:** Weekly chart timeframe.
- **SOURCE:** `12:44 - 13:40` (Said and showed on chart).
- **CLARITY:** **AMBIGUOUS**. Determining the bias relies on subjective analysis of "market tone," earnings season volatility, Fed interest rate discussions, and discretionary seasonal tendencies.

### Rule 2: Primary Trading Session Window
- **RULE:** The primary intraday execution window for index setups must be limited to the morning session from 8:30 AM to 11:00 AM New York local time.
- **CATEGORY:** Session/killzone.
- **NUMBERS:** 8:30 AM – 11:00 AM New York local time.
- **SOURCE:** `24:00 - 24:45` (Said).
- **CLARITY:** **CLEAR**.

### Rule 3: Execution Timeframes
- **RULE:** Lower-timeframe intraday setups must be executed on either 1-minute, 2-minute, or 3-minute charts (with 5-minute being the absolute maximum threshold) because high-frequency algorithms process structural imbalances at these speeds.
- **CATEGORY:** General principle.
- **NUMBERS:** 1m, 2m, 3m, or 5m charts.
- **SOURCE:** `16:40 - 17:30` (Said).
- **CLARITY:** **CLEAR**.

### Rule 4: Market Structure Break (MSB) Confirmation
- **RULE:** For a bearish trade setup, after buy-side liquidity is swept, a candle must close below the lowest point of a defined short-term swing low on the execution timeframe to confirm a change in structural state.
- **CATEGORY:** Sweep / confirmation.
- **NUMBERS:** Short-term swing low on 1m, 2m, or 3m timeframes.
- **SOURCE:** `17:56 - 18:03` (Said and showed on chart).
- **CLARITY:** **CLEAR**.

### Rule 5: Fair Value Gap (FVG) Definition
- **RULE:** A Fair Value Gap (imbalance) is defined as a 3-candle sequence where there is an empty price gap between Candle 1's low and Candle 3's high (for a bearish FVG) or Candle 1's high and Candle 3's low (for a bullish FVG).
- **CATEGORY:** Reference level.
- **NUMBERS:** 3-candle sequence.
- **SOURCE:** `18:10 - 18:35` and `20:02 - 20:25` (Said and showed on chart).
- **CLARITY:** **CLEAR**.

### Rule 6: Execution Trigger
- **RULE:** Execute a short market or limit order immediately when price retraces back up into the bearish Fair Value Gap on the lower-timeframe execution chart.
- **CATEGORY:** Entry.
- **NUMBERS:** Not stated (no specific point buffer; entry is when price touches the FVG boundaries).
- **SOURCE:** `18:25 - 18:39` and `22:20 - 22:33` (Said and showed on chart).
- **CLARITY:** **CLEAR**.

### Rule 7: Stop Loss Placement (Two Options)
- **RULE:** Place the protective stop loss either immediately above the high of the swing high established during the stop hunt (sweep) OR above the high of Candle 1 of the 3-candle Fair Value Gap formation.
- **CATEGORY:** Stop loss.
- **NUMBERS:** Swing high or FVG Candle 1 high.
- **SOURCE:** `22:35 - 22:45` (Said and showed on chart).
- **CLARITY:** **CLEAR**.

### Rule 8: Premium vs. Discount Filter
- **RULE:** Short setups must only be taken in the Premium zone (defined as any price level above the 50% midpoint of the daily trading range from the current low of the day to the high of the day).
- **CATEGORY:** General principle / reference level.
- **NUMBERS:** 50% midpoint of the established intraday high-to-low range.
- **SOURCE:** `21:10 - 21:55` (Said and showed on chart).
- **CLARITY:** **CLEAR**.

### Rule 9: Profit Target / Take Profit
- **RULE:** Take profits at the closest logical sell-side liquidity pool (sell stops below an old low) or a bullish Fair Value Gap that resides in the Discount zone (below the 50% midpoint).
- **CATEGORY:** Take profit.
- **NUMBERS:** Must be in the Discount zone (<50% of the range).
- **SOURCE:** `23:10 - 23:45` and `25:50 - 26:30` (Said and showed on chart).
- **CLARITY:** **CLEAR**.

---

## Chart Examples

### Example 1: Bearish Morning Short Setup
- **Timestamp:** `12:43 - 23:45`
- **Instrument:** E-mini Nasdaq-100 Index Futures (March 2022 Contract, `NQ1!`)
- **Timeframe:** Top-down: Weekly -> Daily -> 1-Hour -> 15-Minute -> 2-Minute
- **Date/Time:** Friday, January 21, 2022 (Morning Session)
- **Reference Levels identified:**
  - *Daily Chart:* Major old daily support low (from October).
  - *1-Hour Chart:* Thursday sell-off low (~14700) and relative equal short-term highs (~14800).
- **Liquidity Sweep / Price Action:** At market open, price initially broke lower to sweep overnight sell-side stops, inducing retail traders to sell short. Price then aggressively reversed upward, clearing the relative equal highs to sweep buy-side stops (engineered liquidity pool).
- **Entry point / trigger:** On the 2-Minute chart, after sweeping the buy stops, price broke below a short-term swing low, confirming a bearish Market Structure Break. A Fair Value Gap (FVG) formed between `14798.25` and `14784.50` in the Premium zone. The entry trigger was a limit order executed when price retraced back up into the FVG.
- **Stop Loss placement:** Above the session swing high.
- **Target / Take Profit:** Overnight low/sell stops in the Discount zone (at `14675.75`).
- **Outcome:** Price declined rapidly to the target, filling the discount imbalance and sweeping the sell stops. The trade captured over 100 points (handles) on NQ.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)
- **Do Not Chase Price:** If price breaks market structure and drops significantly below the swing low without a clean, immediate retrace, do not chase it with market orders far below the FVG. Doing so expands the required stop-loss distance and violates acceptable risk-to-reward parameters. (`22:56 - 23:18`)
- **No Shorts in Discount:** Do not enter short positions if the FVG or price trigger resides below the 50% midpoint of the daily range. (`21:50`)
- **No Longs in Premium:** Do not enter long positions if the setup triggers above the 50% midpoint of the daily range. (`21:50`)
- **Avoid Overtrading:** Developing traders must not trade every intraday session or every calendar day. Doing so builds an unrealistic expectation of constant profitability, leading to emotional, irrational trading after a loss. (`24:00 - 24:40`)

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
- This episode introduces a model specifically designed for **Index Futures** (NQ, ES, and YM).
- **Handle (Point) Valuation Details:**
  - **E-mini Nasdaq-100 (NQ):** 1 handle (point) equals 4 ticks. Each tick is worth $5.00, meaning 1 handle equals $20.00 of risk/reward per contract. NQ is described as faster and more aggressive. (`16:15 - 16:35`)
  - **E-mini S&P 500 (ES):** 1 handle (point) equals 4 ticks. Each tick is worth $12.50, meaning 1 handle equals $50.00 of risk/reward per contract. (`15:53 - 16:12`)
- *Gold and Forex Pairs:* No differences or specific rules for Gold or Forex pairs are discussed in this episode.

---

## Ambiguities and Open Questions
- **Defining "Midpoint" Dynamically:** Michael uses a Fibonacci tool to find the 50% level from the "low of the day to the high of the day." In an automated system, if price makes a new high after a retracement has started but before hitting our FVG, the range changes. It is unclear if the algorithm should dynamically lock the range at the moment the sweep occurs or update it continuously.
- **Mechanical Definition of "Swing Low":** While Michael manually identifies the swing low that triggers the Market Structure Break on the chart, he does not state a hard mathematical rule for identifying a swing low in code (e.g., a candle with a lower low than the candle to its left and right). Explicit programming parameters for structural low validation are left unstated in this episode.
