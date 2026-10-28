# Episode 15: 2022 ICT Mentorship Episode 15

**Source URL:** https://www.youtube.com/watch?v=tGxuitjtO88

## Summary of Episode
In this episode, Michael J. Huddleston (ICT) records a live trade execution session on Nasdaq Futures (NQM22) during the market open on an FOMC (Federal Open Market Committee) announcement day. He demonstrates "Narrative-driven" trading over purely mechanical patterns. Specifically, he outlines how the 09:30 AM New York market open creates volatility designed to sweep retail stop-losses before moving in the true direction. He enters a long position after retail sell stops are cleared inside a 1-minute Fair Value Gap (FVG) and manages the trade dynamically, explaining the logic of targeting premium-range FVGs and the necessity of finishing equity trading early on FOMC days.

---

## Concrete Trading Rules

*   **RULE 1:** A bullish market structure shift is validated on the lower-timeframe chart when price trades above a prior short-term swing high.
    *   **CATEGORY:** confirmation
    *   **NUMBERS:** 1-minute timeframe.
    *   **SOURCE:** 1:26 - 1:40 (SAID and SHOWED on chart).
    *   **CLARITY:** Clear.

*   **RULE 2:** During the 09:30 AM equity market open, price will often overshoot or whip below a bullish Fair Value Gap's low to hunt retail sell stops; wait for this sweep to occur and enter long as price trades back up into the FVG.
    *   **CATEGORY:** entry
    *   **NUMBERS:** 09:30 AM New York Time.
    *   **SOURCE:** 2:40 - 3:55 (SAID and SHOWED on chart).
    *   **CLARITY:** Clear.

*   **RULE 3:** When trading the highly volatile 09:30 AM market open, use a manual mental stop-loss instead of a hard limit stop-loss to prevent being swept out by rapid, brief wick expansions before price reverses.
    *   **CATEGORY:** stop loss
    *   **NUMBERS:** Not stated.
    *   **SOURCE:** 4:35 - 5:08 (SAID).
    *   **CLARITY:** AMBIGUOUS (The threshold for what constitutes trading "by a little bit" below the low before manually clicking "close at market" is highly subjective and not numerically defined).

*   **RULE 4:** Target a Fair Value Gap residing in a Premium market state (above the equilibrium of the current trading range) as a high-probability take-profit target.
    *   **CATEGORY:** take profit
    *   **NUMBERS:** Above the 50% equilibrium level of the dealer range.
    *   **SOURCE:** 5:27 - 5:42 (SAID).
    *   **CLARITY:** Clear.

*   **RULE 5:** Once a bullish expansion begins, any newly formed lower-timeframe FVG must act as support; price should not trade below the low of this new FVG.
    *   **CATEGORY:** trade management
    *   **NUMBERS:** 1-minute timeframe.
    *   **SOURCE:** 6:09 - 6:26 (SAID).
    *   **CLARITY:** Clear.

*   **RULE 6:** On FOMC announcement days, index futures can be traded during the morning session, but all positions must be fully closed and trading must be finished "early" in the morning.
    *   **CATEGORY:** news
    *   **NUMBERS:** Morning session only; exact exit time not specified but must be before afternoon FOMC volatility begins.
    *   **SOURCE:** 7:00 - 7:14 (SAID).
    *   **CLARITY:** AMBIGUOUS (The definition of "early" is not given a precise clock time cutoff).

---

## Chart Examples

### Example 1: Nasdaq Futures Live Trade
*   **Timestamp:** 0:05 - 9:02
*   **Instrument:** Nasdaq Futures June 2022 Contract (NQM22)
*   **Timeframe:** 1-minute (1m)
*   **Date/Time (if visible):** March 16, 2022 / 09:30 AM EST
*   **Reference Levels identified:** 1-minute FVG marked between 13,629.30 and 13,605.60 (gray/yellow box). Retail sell stops identified at 13,614.00. Target Premium FVG identified near the 13,680.00 level.
*   **Liquidity Sweep / Price Action:** At the 09:30 AM equity open, price dipped aggressively below the FVG low to 13,614.00, sweeping retail stops.
*   **Entry point / trigger:** Long entry filled at 13,625.75 on 1 contract after price swept the retail stops and traded back into the FVG (4:23).
*   **Stop Loss placement:** Manual stop-loss prepared to execute if price sustained trading below the swept 13,614.00 low.
*   **Target / Take Profit:** Limit sell order placed at 13,680.00.
*   **Outcome:** Price expanded aggressively upward to fill the target at 13,680.00 for a profit of $1,085.00 (plus $170.00 from an earlier morning micro-scalp, totaling $1,255.00).

---

## Conditions that Cancel a Setup / Filters (What NOT to do)
*   **Do Not Trade FOMC Afternoons:** Do not hold positions or attempt to enter setups during the afternoon session of an FOMC release day.
*   **Narrative Violation:** If price trades cleanly and remains below the swept swing low (violating the expectation of immediate institutional support), the bullish narrative is invalidated, and the trade must be closed immediately.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
*   None mentioned in this episode (focused entirely on Index Futures).

---

## Ambiguities and Open Questions
1.  **Mental Stop-Loss Threshold:** To implement this in an algorithm, what is the exact buffer size (in points/ticks) or candle-close requirement below the swept low that would trigger the programmatic market exit, since a "mental stop" with "flexibility" cannot be coded literally?
2.  **FOMC Day Cut-off Time:** What is the precise time (e.g., 11:30 AM NY time) when morning-session trading must cease on an FOMC day?
