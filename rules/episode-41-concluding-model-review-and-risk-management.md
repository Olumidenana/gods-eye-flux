# Episode 41: 2022 ICT Mentorship - Episode 41 & Final

**Source URL:** [https://www.youtube.com/watch?v=2XhDi5GoNUI](https://www.youtube.com/watch?v=2XhDi5GoNUI)

## Summary of Episode
This final episode of the 2022 Mentorship serves as a technical wrap-up and a deep dive into risk and trade management. Michael Huddleston (ICT) reviews price action on the E-mini S&P 500 (ES) futures for June 23, 2022. He provides exact operating hours for the New York Index AM and PM sessions and emphasizes that the "2022 Model" (Liquidity sweep -> Market Structure Shift with displacement -> FVG entry) remains the core strategy. The latter half of the video provides concrete, algorithmic rules for position sizing, scaling risk down after losses, and a specific "Stop Loss Trimming" procedure based on price reaching percentage milestones of a target range.

## Concrete Trading Rules

- **RULE:** The New York Index AM Session (Killzone) operating hours are from 08:30 AM to 11:00 AM New York Local Time.
- **CATEGORY:** Session/Killzone.
- **NUMBERS:** 08:30 AM – 11:00 AM EST.
- **SOURCE:** 03:34 (Said and Showed).
- **CLARITY:** Clear.

- **RULE:** The New York Index PM Session (Killzone) operating hours are from 01:30 PM to 04:00 PM New York Local Time.
- **CATEGORY:** Session/Killzone.
- **NUMBERS:** 01:30 PM – 04:00 PM EST.
- **SOURCE:** 06:20 (Said and Showed).
- **CLARITY:** Clear.

- **RULE:** Do not enter or hold new positions during the New York lunch hour, defined as 12:00 PM to 01:00 PM.
- **CATEGORY:** Session/Killzone.
- **NUMBERS:** 12:00 PM – 01:00 PM EST.
- **SOURCE:** 07:15 (Said).
- **CLARITY:** Clear.

- **RULE:** The standard risk for a trade is 1% of the account equity.
- **CATEGORY:** Risk/Position Size.
- **NUMBERS:** 1%.
- **SOURCE:** 22:27 (Said).
- **CLARITY:** Clear.

- **RULE:** If a trade resulting in a 1% loss occurs, the risk on the subsequent trade must be reduced to 0.5%.
- **CATEGORY:** Risk/Position Size.
- **NUMBERS:** 0.5%.
- **SOURCE:** 31:17 (Said).
- **CLARITY:** Clear.

- **RULE:** To return to a 1% risk level after a loss, the trader must earn back 50% of the lost amount using the reduced risk (0.5%).
- **CATEGORY:** Risk/Position Size.
- **NUMBERS:** 50% of loss recovery.
- **SOURCE:** 32:03 (Said).
- **CLARITY:** Clear.

- **RULE:** If the 0.5% risk trade also results in a loss, the risk on the next trade must be reduced further to 0.25%.
- **CATEGORY:** Risk/Position Size.
- **NUMBERS:** 0.25%.
- **SOURCE:** 43:22 (Said).
- **CLARITY:** Clear.

- **RULE:** When price reaches 50% of the targeted range (from entry to target objective), the Stop Loss can be trimmed by 25%.
- **CATEGORY:** Trade Management.
- **NUMBERS:** 50% of target range reached, move Stop Loss to reduce original risk by 25%.
- **SOURCE:** 49:57 (Said and Showed).
- **CLARITY:** Clear.

- **RULE:** When price reaches 75% of the targeted range, the Stop Loss must be moved to Break Even.
- **CATEGORY:** Trade Management.
- **NUMBERS:** 75% of target range reached.
- **SOURCE:** 50:57 (Said and Showed).
- **CLARITY:** Clear.

- **RULE:** The point multiplier for E-mini S&P 500 (ES) is $50 per point; the multiplier for Micro E-mini (MES) is $5 per point.
- **CATEGORY:** Risk/Position Size.
- **NUMBERS:** $50 and $5.
- **SOURCE:** 33:37 (Said).
- **CLARITY:** Clear.

## Chart Examples

### Chart Example 1 (AM Session)
- **Timestamp:** 03:09
- **Instrument:** E-mini S&P 500 (ESU2022)
- **Timeframe:** 15m / 5m / 2m
- **Date/Time:** June 23, 2022, morning
- **Reference Levels identified:** Buy-side liquidity above old highs; FVG on 2-minute chart.
- **Liquidity Sweep / Price Action:** Price rallies above short-term buy-side liquidity but fails to reach the primary target (3805.50).
- **Entry point / trigger:** Long entry at the 2-minute FVG.
- **Stop Loss placement:** Below the low formed during the liquidity sweep.
- **Target / Take Profit:** 3805.50 (higher-timeframe draw).
- **Outcome:** Stop hit at +2 points (stopped in profit/trim). ICT notes his expectation for a deep run was wrong, and price broke down into lunch.

### Chart Example 2 (PM Session)
- **Timestamp:** 18:10
- **Instrument:** E-mini S&P 500 (ESU2022)
- **Timeframe:** 5m
- **Date/Time:** June 23, 2022, 01:30 PM - 04:00 PM
- **Reference Levels identified:** Old high (Target 1), 3805.50 (Target 2), FVG on 5m.
- **Liquidity Sweep / Price Action:** Price drops into a 5-minute FVG/Order Block after a market structure shift at 01:30 PM.
- **Entry point / trigger:** Long at 3754.75 (FVG entry).
- **Stop Loss placement:** 3745.75 (9 points risk).
- **Target / Take Profit:** 3780.25 (Initial Objective), 3805.50 (Final Target).
- **Outcome:** Successful trade. Price reached both targets. ICT demonstrated stop management (trimming) during this walk-through.

## Conditions that Cancel a Setup / Filters (What NOT to do)

- **Do not trade if a Fed Chair (Powell) is speaking** unless you are prepared for extreme volatility or potential failure of technical expectations (noted at 00:33).
- **Do not chase a run into the lunch hour (12:00 PM - 01:00 PM).** ICT explicitly states he closes the computer if his AM expectation fails leading into noon (05:04).
- **Avoid setups that do not show "meaningful movement" (displacement)** below or above the old high/low after a sweep. He points out an FVG he would *not* take because the market didn't displace enough below an old low first (21:10).
- **Stop trading for the day if you lose twice.** Although not explicitly stated as a hard number in this video, the risk-reduction rules imply a stopping point as risk reaches 0.25%.

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences

- **Multipliers:** Explicitly mentions the $50 (Mini) and $5 (Micro) multipliers for S&P 500 Index Futures for calculation purposes.
- **Targeting:** Notes that Index Futures are highly sensitive to the New York local time killzones (08:30-11:00 and 01:30-04:00), which may differ from Forex killzones.

## Ambiguities and Open Questions

- **Trimming Stop Loss Calculation:** When ICT says "trim the Stop Loss by 25%," it is technically ambiguous whether he means:
    1. Reducing the *distance* between entry and stop by 25% (moving the stop price closer to entry).
    2. Closing 25% of the *position size* (partial take profit).
    *Context of "Stop Management" at 49:57 strongly suggests moving the price of the stop to reduce the monetary risk by 25%.*
- **Displacement Definition:** ICT mentions "meaningful movement" for displacement but does not give a point or pip threshold. It remains a visual/subjective requirement for a programmer without further quantification.
