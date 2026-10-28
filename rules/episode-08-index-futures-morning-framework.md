# Episode 08: 2022 ICT Mentorship Episode 8

**Source URL:** https://www.youtube.com/watch?v=7rbV8aWkcqY

## Summary of Episode
In this episode, Michael J. Huddleston (ICT) demonstrates how to apply the 2022 Mentorship model to the Foreign Exchange (Forex) markets. Using the EUR/JPY cross pair, he outlines how high-timeframe (HTF) Daily setups translate down to lower-timeframe (LTF) execution charts during specific session Killzones. Additionally, he introduces currency correlation analysis using individual currency futures contracts (such as 6E for Euro and 6J for Yen) to establish a directional bias, and explains how to project expansion targets using Fibonacci Standard Deviations when immediate historical reference points are unavailable on the execution timeframe.

---

## Concrete Trading Rules

*   **RULE:** The TradingView chart timezone must always be manually configured to New York local time (UTC-5 or UTC-4 depending on Daylight Saving Time) to ensure precise execution session mapping.
    *   **CATEGORY:** session/killzone
    *   **NUMBERS:** New York Time (UTC-5 / UTC-4).
    *   **SOURCE:** 06:05 (SHOWED on chart and SAID)
    *   **CLARITY:** CLEAR

*   **RULE:** For Forex intraday setups, the New York Session trade search window (New York Killzone) is defined strictly between 07:00 AM and 10:00 AM New York local time.
    *   **CATEGORY:** session/killzone
    *   **NUMBERS:** 07:00 to 10:00 New York Time.
    *   **SOURCE:** 05:35, 06:12, 11:32 (SHOWED on chart and SAID)
    *   **CLARITY:** CLEAR

*   **RULE:** For Forex intraday setups, the London Session trade search window (London Killzone) is defined strictly between 02:00 AM and 05:00 AM New York local time.
    *   **CATEGORY:** session/killzone
    *   **NUMBERS:** 02:00 to 05:00 New York Time.
    *   **SOURCE:** 10:15 (SAID)
    *   **CLARITY:** CLEAR

*   **RULE:** To frame a high-timeframe institutional order flow direction, identify relative equal lows (or relative equal highs) on the Daily (1D) chart, wait for price to sweep below/above them, and look for a subsequent Daily shift in market structure (MSS) leaving behind a Daily Fair Value Gap (FVG).
    *   **CATEGORY:** reference level
    *   **NUMBERS:** Daily (1D) timeframe.
    *   **SOURCE:** 01:45 - 02:40 (SHOWED on chart)
    *   **CLARITY:** CLEAR

*   **RULE:** For lower-timeframe execution, once a Daily structural bias is confirmed, identify a sweep of a short-term swing low (for longs) or swing high (for shorts) followed by a structural displacement (Market Structure Shift) that creates a local Fair Value Gap (FVG) on the 5-minute or 3-minute chart within the designated session Killzone.
    *   **CATEGORY:** confirmation
    *   **NUMBERS:** 5-minute or 3-minute execution timeframes.
    *   **SOURCE:** 07:07 - 07:44 (SHOWED on chart and SAID)
    *   **CLARITY:** CLEAR

*   **RULE:** When trading a currency cross pair (e.g., EUR/JPY), confirm the directional bias by checking that the base currency's futures contract (e.g., 6E Euro futures) is strong/bullish and the quote currency's futures contract (e.g., 6J Yen futures) is weak/bearish.
    *   **CATEGORY:** confirmation
    *   **NUMBERS:** Not stated.
    *   **SOURCE:** 12:10 - 13:13 (SHOWED on chart and SAID)
    *   **CLARITY:** CLEAR

*   **RULE:** When targeting an upside expansion move that lacks immediate local resistance levels on the execution chart, draw a Fibonacci tool from the preceding consolidation's key swing low to its swing high to project the -1.0 Standard Deviation level as a take-profit target.
    *   **CATEGORY:** take profit
    *   **NUMBERS:** -1.0 Standard Deviation.
    *   **SOURCE:** 08:35 - 09:30 (SHOWED on chart and SAID)
    *   **CLARITY:** CLEAR

---

## Chart Examples

### Example 1: EUR/JPY Bullish Daily Framework to Intraday Execution
*   **Timestamp:** 00:50 - 10:00
*   **Instrument:** EUR/JPY
*   **Timeframe:** Daily (HTF analysis) scaled down to 15-minute, 5-minute, and 3-minute (LTF execution).
*   **Date/Time (if visible):** Execution Day: February 10, 2022. HTF relative equal lows traced back to August/September 2021.
*   **Reference Levels identified:** Daily relative equal lows.
*   **Liquidity Sweep / Price Action:** The Daily chart swept key relative equal lows in December 2021, displacement rallied higher, broke market structure to the upside, pulled back to discount Daily Fair Value Gaps, and resumed its expansion higher.
*   **Entry point / trigger:** On February 10, 2022, during the New York Killzone (07:00 AM - 10:00 AM NY Time), price swept a local swing low on the 3-minute chart, shifted market structure back to the upside with displacement, and left a 3m FVG. Entry was taken inside the retracement to the 3-minute Fair Value Gap.
*   **Stop Loss placement:** Implied below the swing low formed by the displacement leg.
*   **Target / Take Profit:** A Fibonacci projection drawn from the structural low prior to the expansion to the subsequent swing high yielded a -1.0 Standard Deviation target of exactly 133.153.
*   **Outcome:** Price moved directly to the -1.0 expansion level (high print of 133.153) before reversing down.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)
*   **Do not** trade these specific intraday setups outside the defined New York Killzone (07:00 AM - 10:00 AM NY Time) or London Killzone (02:00 AM - 05:00 AM NY Time) windows.
*   **Do not** use local computer timezone settings on TradingView charts; setting the timezone incorrectly offsets the session vertical dividers and invalidates the setup rules.
*   **Avoid trading Yen (JPY) pairs** if you prefer single-pass, clean retracements. ICT notes that Yen pairs frequently make a "double return" (deep double pullback/test of key reference levels), making them harder to hold.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
*   **Forex Session Times:** While Index Futures setups focus on the 08:30 AM - 11:00 AM and 01:30 PM - 04:00 PM EST windows, Forex setups are strictly anchored to the London Session Killzone (02:00 AM - 05:00 AM NY Time) and the New York Session Killzone (07:00 AM - 10:00 AM NY Time).
*   **Cross Currency Dynamics:** Unlike stock indices, cross currency pairs can be broken down into their individual component futures contracts (such as 6E for Euro and 6J for Yen) to verify relative strength and weakness alignment before establishing a bias.

---

## Ambiguities and Open Questions
*   **Fibonacci Configuration Parameters:** ICT mentions that his precise Fibonacci tool settings are detailed in his "OTE Primer" video, but he does not display the entire parameter configuration panel on screen in this episode (only demonstrating 0.0, 1.0, and -1.0 SD values). 
*   **The "Double Return" Metric:** The concept that Yen pairs do a "double return" to a specific level is presented as a reason to dislike the pair, but the exact quantitative criteria for what defines a double return (or how an algorithm should account for this behavior with stop-loss padding) is left open.
