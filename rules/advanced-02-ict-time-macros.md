# 2023 ICT Mentorship - Algorithmic Price Delivery & Time Macros Intro

**Source URL:** https://www.youtube.com/watch?v=kYJ7x4k8Wyk

## Summary of Video
In this video, ICT introduces the concept of "Macros"—specific 20-minute windows of time where the central bank algorithm is programmed to execute specific price delivery functions. He argues that time is more important than price. The video focuses on identifying these windows (specifically in the AM and PM sessions) and observing how price seeks liquidity or closes Fair Value Gaps (FVGs) during these intervals. The 1-minute timeframe is the primary tool for observing these delivery "engines."

## Concrete Trading Rules

- **RULE:** The algorithm operates on specific 20-minute "Macro" windows during the New York session.
- **CATEGORY:** session/killzone
- **NUMBERS:** 08:50 AM – 09:10 AM, 09:50 AM – 10:10 AM, 10:50 AM – 11:10 AM, 01:50 PM – 02:10 PM, 02:50 PM – 03:10 PM (All times New York Local Time).
- **SOURCE:** 05:20 (Said/Shown on screen), 22:50 (Reiterated).
- **CLARITY:** Clear.

- **RULE:** During a Macro window, price will specifically seek to either run for Liquidity (Old Highs/Lows) or rebalance a Fair Value Gap (FVG).
- **CATEGORY:** reference level
- **NUMBERS:** Not stated (depends on nearest Draw on Liquidity).
- **SOURCE:** 06:15 (Said), 13:45 (Shown on chart).
- **CLARITY:** AMBIGUOUS. ICT does not specify which FVG or which Liquidity pool takes priority if multiple exist; it requires a "Draw on Liquidity" analysis first.

- **RULE:** If price has not reached its intended Draw on Liquidity by the start of a Macro window, the Macro will provide the "injection" of volatility to reach it.
- **CATEGORY:** general principle
- **NUMBERS:** Not stated.
- **SOURCE:** 15:40 (Said).
- **CLARITY:** Clear.

- **RULE:** Use the 1-minute chart to identify the "Internal Range Liquidity" or "Market Structure Shifts" that occur precisely within the Macro timestamps.
- **CATEGORY:** confirmation
- **NUMBERS:** 1-minute timeframe.
- **SOURCE:** 11:10 (Shown on chart).
- **CLARITY:** Clear.

- **RULE:** The 10:50 AM to 11:10 AM Macro is often the "spoiler" or the final delivery window for the morning session trend.
- **CATEGORY:** session/killzone
- **NUMBERS:** 10:50 AM – 11:10 AM.
- **SOURCE:** 24:15 (Said).
- **CLARITY:** Clear.

- **RULE:** If price is in a "Seek and Destroy" or consolidative profile, Macros will likely sweep both sides of the 1-minute range.
- **CATEGORY:** general principle
- **NUMBERS:** Not stated.
- **SOURCE:** 35:20 (Said).
- **CLARITY:** AMBIGUOUS. Requires the trader to pre-identify the "Seek and Destroy" profile.

## Chart Examples

### Example 1: GBPUSD (Cable)
- **Timestamp:** 11:45 (start of chart analysis)
- **Instrument:** GBPUSD
- **Timeframe:** 1-minute
- **Date/Time (if visible):** February 23, 2023
- **Reference Levels identified:** Buy-side Liquidity (Equal Highs) and a 1-minute Fair Value Gap.
- **Liquidity Sweep / Price Action:** Price consolidated until the 10:50 AM Macro started. At 10:50 AM exactly, price began moving aggressively toward the Draw on Liquidity.
- **Entry point / trigger:** Entry at the 1-minute FVG that formed at the beginning of the 10:50 AM window.
- **Stop Loss placement:** Below the low formed at 10:50 AM.
- **Target / Take Profit:** The Buy-side Liquidity (Old High) located above price.
- **Outcome:** Price hit the target at 11:02 AM, within the Macro window.

### Example 2: NQ (Nasdaq Futures) - Mentions only
- **Timestamp:** 04:30
- **Instrument:** NQ
- **Timeframe:** 1-minute
- **Date/Time (if visible):** Late Feb 2023
- **Reference Levels identified:** 09:50 AM Macro window.
- **Liquidity Sweep / Price Action:** He shows how the 09:50 AM Macro specifically targets the liquidity generated during the 09:30 AM open.
- **Entry point / trigger:** Not explicitly detailed with an entry, but identifies the *move* starting at 09:50 AM.
- **Stop Loss placement:** Not stated.
- **Target / Take Profit:** High of the day/Buy-side Liquidity.
- **Outcome:** Price delivers to the target within the 20-minute window.

## Conditions that Cancel a Setup / Filters (What NOT to do)

- **Condition:** If the "Draw on Liquidity" is unclear or there is no obvious FVG/Old High/Low nearby, do not trade the Macro. The Macro is a "delivery engine," not a signal in isolation.
- **Condition:** Do not look for new setups *after* the Macro window has closed (e.g., after 11:10 AM) for the morning session, as price often goes into lunch consolidation.
- **Condition:** If price reaches the target *seconds before* the Macro starts, the Macro may result in a reversal rather than a continuation.

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences

- **Indices (NQ/ES):** ICT notes that the 2023 mentorship is primarily centered on Index Futures. He states that the Macros are "highly precise" on NQ.
- **Forex (GBPUSD):** He uses GBPUSD to demonstrate that the algorithm is universal across asset classes, showing that the 10:50 AM Macro works on Cable exactly like it does on Indices.
- **Gold (XAUUSD):** No specific differences mentioned in this particular video.

## Ambiguities and Open Questions

1.  **Priority of Macros:** ICT lists several Macros (08:50, 09:50, 10:50). He does not provide a rule for which one will be the "primary" move of the day and which might be a retracement.
2.  **Gap Selection:** In the GBPUSD example, there are multiple 1-minute FVGs. The rule for selecting the "correct" one is not algorithmically defined other than "the one that forms as the Macro starts."
3.  **Macro Failures:** He does not show an example of a Macro "failing" to deliver. For an algorithmic programmer, "fail-safe" logic or a "no-trade" condition for when the algorithm ignores a Macro is missing.
4.  **Directionality:** The Macros tell you *when* price will move, but the *direction* is entirely dependent on the trader’s ability to identify the Draw on Liquidity (higher timeframe bias). The video does not provide a hard-coded rule for determining that bias.
