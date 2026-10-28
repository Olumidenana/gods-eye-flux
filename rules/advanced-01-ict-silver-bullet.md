# 2023 ICT Mentorship - ICT Silver Bullet Time Based Trading Model

**Source URL:** https://www.youtube.com/watch?v=k45a-hO9Wp0

## Summary of Video
Michael J. Huddleston introduces the "Silver Bullet" model, a time-based trading strategy designed to be highly mechanical and frequent. It operates on the premise that the market consistently provides a setup within specific 60-minute windows every day (London Open, AM Session, and PM Session). The model does not require a higher-timeframe daily bias; instead, it relies on price reaching for a specific liquidity pool or Fair Value Gap (FVG) and entering on a 1-minute or 5-minute displacement that creates an FVG within that hour. It is presented as a "bread and butter" setup for a minimum of 10-15 pips/handles.

## Concrete Trading Rules

- **RULE:** The AM Session Silver Bullet time window is defined as 10:00 AM to 11:00 AM New York Local Time.
  - **CATEGORY:** Session/Killzone
  - **NUMBERS:** 10:00 AM - 11:00 AM (EST/EDT).
  - **SOURCE:** 02:40 (Said and Shown).
  - **CLARITY:** Clear.

- **RULE:** The PM Session Silver Bullet time window is defined as 2:00 PM to 3:00 PM New York Local Time.
  - **CATEGORY:** Session/Killzone
  - **NUMBERS:** 2:00 PM - 3:00 PM (EST/EDT).
  - **SOURCE:** 02:45 (Said and Shown).
  - **CLARITY:** Clear.

- **RULE:** The London Open Silver Bullet time window is defined as 3:00 AM to 4:00 AM New York Local Time.
  - **CATEGORY:** Session/Killzone
  - **NUMBERS:** 3:00 AM - 4:00 AM (EST/EDT).
  - **SOURCE:** 03:02 (Said and Shown).
  - **CLARITY:** Clear.

- **RULE:** Before an entry is taken, price must have an identifiable "Draw on Liquidity" which can be an Old High/Low, Session High/Low, Previous Day High/Low, or an unfilled FVG.
  - **CATEGORY:** Reference Level
  - **NUMBERS:** Not stated.
  - **SOURCE:** 05:40, 11:15 (Said and Shown).
  - **CLARITY:** AMBIGUOUS (The choice of which specific liquidity pool to target is subjective; an algorithm would need a hierarchy of targets).

- **RULE:** The entry must be based on a Fair Value Gap (FVG) that is formed within the specific 60-minute Silver Bullet window.
  - **CATEGORY:** Entry
  - **NUMBERS:** 1-minute or 5-minute timeframe.
  - **SOURCE:** 04:30 (Said and Shown).
  - **CLARITY:** Clear.

- **RULE:** The trade must target a minimum of 10 handles (Indices) or 10-15 pips (Forex).
  - **CATEGORY:** Take Profit
  - **NUMBERS:** 10 handles (NQ/ES); 10-15 pips (GBP/EUR).
  - **SOURCE:** 04:45, 12:30 (Said).
  - **CLARITY:** Clear.

- **RULE:** The Stop Loss must be placed at the swing high (for shorts) or swing low (for longs) formed immediately before the displacement that created the FVG.
  - **CATEGORY:** Stop Loss
  - **NUMBERS:** Not stated (based on price action).
  - **SOURCE:** 13:40 (Shown on chart).
  - **CLARITY:** Clear.

- **RULE:** If a Fair Value Gap is formed and price returns to it within the window, the entry is a limit order at the start of the FVG (the first candle's high/low).
  - **CATEGORY:** Entry
  - **NUMBERS:** Not stated.
  - **SOURCE:** 14:15 (Shown on chart).
  - **CLARITY:** Clear.

## Chart Examples

### Example 1: GBP/USD (London Session)
- **Timestamp:** 10:45
- **Instrument:** GBP/USD
- **Timeframe:** 5-minute
- **Date/Time (if visible):** February 2nd
- **Reference Levels identified:** Previous Day Low.
- **Liquidity Sweep / Price Action:** Price trades below the Previous Day Low just before the 3:00 AM window.
- **Entry point / trigger:** Entry into a 5-minute FVG at approximately 3:15 AM - 3:30 AM.
- **Stop Loss placement:** Below the low formed at the sweep.
- **Target / Take Profit:** 15 pips.
- **Outcome:** Success.

### Example 2: NASDAQ (NQ) AM Session
- **Timestamp:** 12:50
- **Instrument:** NQ Futures
- **Timeframe:** 1-minute
- **Date/Time (if visible):** February 2nd
- **Reference Levels identified:** Internal Sell Side Liquidity (Old Lows).
- **Liquidity Sweep / Price Action:** Price displaces lower at 10:00 AM, creating an FVG.
- **Entry point / trigger:** 1-minute FVG entry at approximately 10:03 AM.
- **Stop Loss placement:** Above the 10:01 AM swing high.
- **Target / Take Profit:** 10 handles.
- **Outcome:** Success.

### Example 3: Gold (XAUUSD) London Session
- **Timestamp:** 28:20
- **Instrument:** XAUUSD
- **Timeframe:** 5-minute
- **Date/Time (if visible):** February 2nd
- **Reference Levels identified:** Discount FVG on higher timeframe.
- **Liquidity Sweep / Price Action:** Displacement higher within the 3:00 AM window.
- **Entry point / trigger:** Retest of a 5-minute FVG at 3:45 AM.
- **Stop Loss placement:** Below the candle low that preceded the FVG.
- **Target / Take Profit:** 2:1 Reward to Risk or clear liquidity pool.
- **Outcome:** Success.

## Conditions that Cancel a Setup / Filters (What NOT to do)

- **Do Not Trade Outside the Window:** If an FVG forms and is filled before 10:00 AM, 2:00 PM, or 3:00 AM, it is not a Silver Bullet setup.
- **Target Already Hit:** If the target (10 pips/handles or the liquidity pool) is reached *before* price enters the FVG, the setup is lower probability or invalidated.
- **Lack of Displacement:** If price drifts into a gap without a sharp "displacement" (energetic move), it is not a valid Silver Bullet.
- **No Clear Draw:** If there is no clear liquidity target for price to run to, do not take the trade.

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences

- **Indices (NQ/ES):** ICT emphasizes a "10 handle" objective. He notes that NQ moves faster and offers these setups with more volatility than ES.
- **Forex (GBP/EUR):** The objective is 10-15 pips. The London window (3 AM - 4 AM) is particularly potent for Forex.
- **Gold (XAUUSD):** Gold is treated similarly to Forex but respects the time windows strictly. It often uses the London window to establish the trend for the AM session.

## Ambiguities and Open Questions

1.  **Multiple FVGs:** If the displacement creates multiple FVGs within the 1-hour window, the video implies taking the first one reached, but does not explicitly state the protocol for "overlapping" or "consecutive" FVGs.
2.  **Stop Loss Refinement:** While he shows stop loss at the swing high/low, in some examples he suggests the stop can be above/below the FVG candle itself for tighter risk. This needs a hard rule for an algorithm.
3.  **Hierarchy of Liquidity:** The model requires a "Draw on Liquidity." For automation, one would need to program a hierarchy (e.g., Priority 1: PDH/PDL, Priority 2: Session H/L, Priority 3: H1 FVG).
4.  **Timeframe Preference:** He switches between 1-minute and 5-minute charts. It is unclear if a 1-minute FVG is "invalid" if it exists inside a 5-minute FVG, or which takes precedence.
