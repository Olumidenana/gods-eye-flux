# Episode 03: 2022 ICT Mentorship Episode 3

**Source URL:** https://www.youtube.com/watch?v=nQfHZ2DEJ8c

## Summary of Episode
This episode focuses on the relationship between **Internal Range Liquidity** (how liquidity pools reside inside a trading range) and **Market Structure Shifts (MSS)**. Michael J. Huddleston (ICT) reviews a homework assignment on E-mini Nasdaq-100 Futures (March 2022 contract) to explain how stop raids (sweeping buy-side or sell-side liquidity) set the stage for market structure shifts on lower timeframes (3-minute, 2-minute, and 1-minute). He provides a precise algorithmic definition of an "order block" as a change in the state of delivery, and then demonstrates a live, real-time trade execution on a 1-minute NQ chart to show how to execute this model inside a Fair Value Gap (FVG) targeting internal range liquidity.

---

## Concrete Trading Rules

### 1. Liquidity Location Rule
* **RULE:** Sell-side liquidity (sell stops) resides below old swing lows and double bottoms, while buy-side liquidity (buy stops) resides above old swing highs and relative equal highs.
* **CATEGORY:** Reference level.
* **NUMBERS:** Identified on a 15-minute chart for intraday bias.
* **SOURCE:** 01:23 - 02:08 (Said and showed on chart).
* **CLARITY:** Clear.

### 2. Timeframe Selection for MSS
* **RULE:** To identify intraday market structure shifts following a daily or 15-minute liquidity sweep, monitor the 3-minute, 2-minute, 1-minute, or sub-1-minute (45-second, 30-second, or 15-second) timeframes.
* **CATEGORY:** General principle.
* **NUMBERS:** 3-min, 2-min, 1-min, 45-sec, 30-sec, 15-sec.
* **SOURCE:** 06:13 - 06:30 (Said).
* **CLARITY:** Clear.

### 3. Bullish Market Structure Shift (MSS) Confirmation
* **RULE:** A bullish market structure shift is confirmed when price trades above the short-term swing high that was formed immediately prior to the lowest low, provided that lowest low swept sell-side liquidity first.
* **CATEGORY:** Confirmation.
* **NUMBERS:** Not stated.
* **SOURCE:** 06:56 - 07:30, 09:53 - 10:25 (Said and showed on chart).
* **CLARITY:** Clear.

### 4. Bearish Market Structure Shift (MSS) Confirmation
* **RULE:** A bearish market structure shift is confirmed when price trades below the short-term swing low that was formed immediately prior to the highest high, provided that highest high swept buy-side liquidity first.
* **CATEGORY:** Confirmation.
* **NUMBERS:** Not stated.
* **SOURCE:** 17:50 - 18:08 (Said and showed on chart).
* **CLARITY:** Clear.

### 5. MSS Candle Close Requirement
* **RULE:** The market structure shift does not require a candle to close beyond the key swing high or low; price only needs to trade through it by at least 1 tick (wicks are sufficient to confirm the shift).
* **CATEGORY:** Confirmation.
* **NUMBERS:** 1 tick minimum.
* **SOURCE:** 13:47 - 13:54 (Said and showed on chart).
* **CLARITY:** Clear.

### 6. Fair Value Gap Entry Trigger
* **RULE:** Following a confirmed market structure shift, enter a trade with a limit order positioned inside the Fair Value Gap (FVG) created during the expansion leg that caused the shift.
* **CATEGORY:** Entry.
* **NUMBERS:** Not stated.
* **SOURCE:** 14:03 - 14:28, 18:08 - 18:14 (Said and showed on chart).
* **CLARITY:** Clear.

### 7. Bullish Order Block Definition & Entry
* **RULE:** A bullish order block is defined as the series of consecutive down-close candles prior to the sweep of sell-side liquidity; when a Fair Value Gap is formed above this block, place a limit buy order at the opening price of the first down-close candle (adjusting for spread).
* **CATEGORY:** Entry.
* **NUMBERS:** Add +3 pips of padding for Forex; add +3 to +5 ticks of padding for Futures contracts to guarantee execution.
* **SOURCE:** 15:04 - 15:42 (Said and showed on chart).
* **CLARITY:** Clear.

### 8. Target Selection (Internal Range Liquidity)
* **RULE:** Target low-hanging fruit inside the internal range, such as relative equal highs/lows or the high/low of an opposing Fair Value Gap located near or beyond the 50% equilibrium mark of the dealing range.
* **CATEGORY:** Take profit.
* **NUMBERS:** 50% equilibrium level of the swing high-to-low dealing range.
* **SOURCE:** 18:13 - 18:25, 19:43 - 20:15 (Said and showed on chart).
* **CLARITY:** Clear.

### 9. Killzone Session Windows
* **RULE:** Identify major liquidity reference highs and lows created during three specific session windows: London (02:00 to 05:00), New York (07:00 to 10:00), and Asia (19:00 to 21:00) using New York local time.
* **CATEGORY:** Session/killzone.
* **NUMBERS:** 02:00 - 05:00 EST/EDT, 07:00 - 10:00 EST/EDT, 19:00 - 21:00 EST/EDT.
* **SOURCE:** 18:43 - 19:37 (Said).
* **CLARITY:** Clear.

### 10. Allowed Trading Windows
* **RULE:** Trade index futures primarily during the morning session between 08:30 and 11:00 New York local time; do not initiate new trades during New York lunch hour (12:00 to 13:00) due to low probability, choppy behavior.
* **CATEGORY:** Session/killzone.
* **NUMBERS:** Trade morning session 08:30 - 11:00 EST/EDT. Avoid 12:00 - 13:00 lunch hour. Afternoon window is active 13:00 to 16:00 (preferably 13:30 onwards), with setups typically forming between 14:00 and 15:00.
* **SOURCE:** 19:53 - 20:52 (Said).
* **CLARITY:** Clear.

### 11. Position Risk Limit
* **RULE:** Under competitive conditions, risk a maximum of 4.5% of account equity per trade, with standard, comfortable positioning set to risk between 3.0% and 3.5% per trade.
* **CATEGORY:** Risk/position size.
* **NUMBERS:** Maximum 4.5%, standard target risk 3.0% - 3.5%.
* **SOURCE:** 14:16 - 14:55 (Said).
* **CLARITY:** Clear.

### 12. Multiple Fair Value Gaps Retracement
* **RULE:** If there are two consecutive Fair Value Gaps formed inside the displacement leg, execute the buy order inside the first (higher) FVG, while using the lower, second FVG as a permitted drawdown buffer without invalidating the trade.
* **CATEGORY:** Entry.
* **NUMBERS:** Not stated.
* **SOURCE:** 12:44 - 13:29 (Said and showed on chart).
* **CLARITY:** Clear.

---

## Chart Examples

### Chart Example 1 (Homework Review - Bullish and Bearish Swings)
* **Timestamp:** 01:10 - 11:05
* **Instrument:** E-mini Nasdaq-100 Futures (March 2022)
* **Timeframe:** 15-minute (higher timeframe bias), 2-minute, and 1-minute (execution timeframes)
* **Date/Time (if visible):** Jan 21, 2022 (around 09:30 to 11:30 AM EST)
* **Reference Levels identified:** Old low at 14,600 (sell-side liquidity) and relative equal highs at 14,820 (buy-side liquidity).
* **Liquidity Sweep / Price Action:** Price drove down below the 14,600 level to trigger sell stops. It then shifted structure back above the swing high on the 1-minute/2-minute chart. Later, it ran up through the equal highs at 14,820 to sweep buy stops before shifting bearish.
* **Entry point / trigger:** Retracement into the lower-timeframe FVG at the open of the bullish order block (for the long); retracement into the bearish FVG after sweeping buy stops (for the short).
* **Stop Loss placement:** Below the swing low that ran the sell stops (for the long); above the swing high that ran the buy stops (for the short).
* **Target / Take Profit:** The relative equal highs at 14,820 (for the long); internal range sell stops and low-hanging fruit (for the short).
* **Outcome:** Successful. Both setups completed their targets precisely.

### Chart Example 2 (Live Trade Demonstration)
* **Timestamp:** 11:06 - 22:27
* **Instrument:** E-mini Nasdaq-100 Futures (March 2022)
* **Timeframe:** 1-minute
* **Date/Time (if visible):** January 25, 2022 (approx. 10:19 AM - 10:22 AM EST)
* **Reference Levels identified:** Intraday bullish Fair Value Gap (green box) and premium bearish FVG/imbalance (pink box).
* **Liquidity Sweep / Price Action:** A bullish MSS had occurred on the 1-minute chart. Michael identifies a premium imbalance (pink box) as target liquidity. Price retraces down into the discount FVG.
* **Entry point / trigger:** Michael buys 2 contracts at market at 10:19 AM EST inside the green FVG (around 14,103 - 14,104).
* **Stop Loss placement:** Set below the swing low of the displacement leg (visually around 14,085).
* **Target / Take Profit:** The low end of the premium bearish FVG (pink box) at approximately 14,154.
* **Outcome:** Successful. Price dipped slightly to fill the lower, unshaded FVG and then accelerated upward, reaching the target at 14,154 for an $1,190 profit on NQ.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)
* **Target Reached Early:** If price rallies up and completely fills the premium target (the target FVG or imbalance) *before* retracing down into the discount entry FVG, the setup is invalidated (nicked) and must be canceled.
* **Lunch Hour Restriction:** Do not take any new entries between 12:00 PM and 13:00 PM New York local time.
* **Unconfirmed MSS:** Do not enter a trade if a swing high or low has not been traded through on the lower timeframe. A market structure shift cannot be forced.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
* **Forex Pair Retracement Padding:** When trading Forex, add 3 pips of padding above/below the order block opening to ensure spread execution.
* **Futures Retracement Padding:** When trading Index Futures (NQ/ES), add 3 to 5 ticks of padding to limit orders to ensure execution.

---

## Ambiguities and Open Questions
* **Subjective Swing High Selection for MSS:** When multiple short-term swing highs exist prior to a liquidity sweep, Michael notes that "you could have used this high... but when I see equal highs, I'm going to use that." He does not provide a strict mathematical rule for choosing among multiple swing highs for an MSS trigger if no equal highs are present.
* **Drawdown Buffer Tolerances:** Michael mentions being comfortable taking drawdown into a second, lower FVG while entering at the first, but does not provide an exact rule on how much invalidation space can be left between consecutive FVGs before a stop loss must be hit.
