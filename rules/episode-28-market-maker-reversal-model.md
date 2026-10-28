# Episode 28: 2022 ICT Mentorship Episode 28

**Source URL:** https://www.youtube.com/watch?v=j0Z2EbuJXGU

## Summary of Episode
This video is a live execution tape reading demonstration on the 1-minute chart of the E-mini S&P 500 Futures (ESM2022) accompanied by on-screen text annotations. ICT illustrates how to identify and trade intermarket SMT divergence between the E-mini S&P 500 (ES) and the E-mini Nasdaq 100 (NQ). When NQ creates a lower low and ES forms a higher low, ES acts as the "Relative Strength Leader." ICT enters long on ES during the late-morning session, pyramiding into the position, targeting buyside liquidity above the morning highs prior to the New York lunch hour.

---

## Concrete Trading Rules

- **RULE:** When analyzing correlated index futures (ES and NQ) for a bullish reversal, compare the swing lows: if one index (NQ) prints a lower low while the other index (ES) prints a higher low (SMT divergence), buy the relative strength leader that formed the higher low.
  - **CATEGORY:** confirmation
  - **NUMBERS:** 1-minute timeframe comparison between ES and NQ.
  - **SOURCE:** 00:15–00:48 (SHOWED on chart and written in text: *"I am buying the Relative Strength Leader between the ES & NQ contract"* and *"Lower Low = Weaker of the Two Indices Nasdaq"*).
  - **CLARITY:** Clear.

- **RULE:** When entering a long position based on SMT divergence and market structure, place the initial stop loss below the recent key swing low / displacement origin.
  - **CATEGORY:** stop loss
  - **NUMBERS:** Initial stop placed at 3979.75 below the 11:15 swing low (entry at 3992.50).
  - **SOURCE:** 00:07–00:10 (SHOWED on chart execution).
  - **CLARITY:** Clear.

- **RULE:** After entering an initial position, additional contracts can be added (pyramided) when price consolidates and resumes displacement in the anticipated direction.
  - **CATEGORY:** entry
  - **NUMBERS:** Initial entry of 25 contracts at 3992.50 (11:27 NY time); secondary market buy of 25 contracts at 3999.00 (11:43 NY time).
  - **SOURCE:** 00:07 and 00:29–00:34 (SHOWED on chart execution).
  - **CLARITY:** Clear.

- **RULE:** During late-morning trend continuation into the New York lunch hour, allow the algorithm to reprice toward buyside liquidity above the morning session high before anticipating any reversal lower.
  - **CATEGORY:** session/killzone
  - **NUMBERS:** NY Lunch begins at 12:00 PM Eastern Time. Target reached between 11:55 AM and 12:00 PM Eastern Time.
  - **SOURCE:** 01:05–01:28 (SHOWED on chart via annotations: *"Buyside Liquidity is New York Lunch Hour Target"*, *"NY Lunch Begins"*, and *"Allow the Algorithm to reprice up here by the New York Lunch Hour. Avoid concern for 'Reversal Lower' before the Buy Stops are taken"*).
  - **CLARITY:** Clear.

- **RULE:** Trail the stop loss upward below newly formed swing lows as price expands toward the objective to lock in unrealized profits.
  - **CATEGORY:** trade management
  - **NUMBERS:** Stop trailed from 3979.75 up to 3987.50, and subsequently higher as price moves upward.
  - **SOURCE:** 00:52–00:56, 01:45–01:48 (SHOWED on chart).
  - **CLARITY:** Clear.

- **RULE:** The take-profit objective for an intraday long expansion is the Buyside Liquidity resting directly above the prominent swing high of the morning session.
  - **CATEGORY:** take profit
  - **NUMBERS:** Limit take profit set at 4020.25 (just above the morning high of 4020.00).
  - **SOURCE:** 00:11–00:13, 01:05, 02:22–02:29 (SHOWED on chart).
  - **CLARITY:** Clear.

---

## Chart Examples

### Chart Example 1: E-mini S&P 500 Index Futures (ES) Long Trade
- **Timestamp:** 00:05 – 02:35
- **Instrument:** CME E-mini S&P 500 Futures (ESM2022) compared against E-mini Nasdaq 100 Futures (NQM2022)
- **Timeframe:** 1-minute (`1m`)
- **Date/Time:** May 19, 2022 (approx. 11:27 AM – 12:00 PM EDT)
- **Reference Levels identified:**
  - Morning Swing High / Buyside Liquidity pool at 4020.00–4020.25.
  - Bullish Fair Value Gap / Order Block area on ES highlighted in yellow box around 3991.00–3993.00.
  - SMT divergence line between 10:20 swing low and 11:15 swing low.
- **Liquidity Sweep / Price Action:**
  - Between 10:20 and 11:15, NQ broke lower and made a lower low (weaker index).
  - ES failed to make a lower low, printing a higher low (bullish SMT divergence / relative strength leader).
- **Entry point / trigger:**
  - First entry: Market buy 25 contracts of ESM2022 at 3992.50 (~11:27 AM EDT) upon retesting the 1m support zone / FVG.
  - Second entry (pyramid): Market buy 25 contracts of ESM2022 at 3999.00 (~11:43 AM EDT).
- **Stop Loss placement:**
  - Initial stop loss: 3979.75 (below the 11:15 swing low).
  - Trailed to 3987.50, then progressively raised under newly formed 1-minute swing lows.
- **Target / Take Profit:**
  - Buyside Liquidity above morning high at 4020.25.
- **Outcome:**
  - Price expanded directly into the buyside liquidity target around 11:58 AM EDT, filling the 50-contract exit at 4020.25 for a net closed profit of over $70,000 on the day's session ($421,907.50 cumulative account equity). Marked with text: *"Bagged & Tagged"*.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)

- **Do not buy the weaker index:** When an SMT divergence occurs between ES and NQ at a market low, do not go long on the contract making the lower low (NQ); buy only the relative strength leader forming the higher low (ES).
- **Do not prematurely anticipate a reversal lower before liquidity is tagged:** Do not fear or exit on minor pauses prior to the lunch hour; the algorithm will typically seek to reprice to the target buyside liquidity before any reversal lower occurs.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences

- **Indices:** Specifically uses the intermarket correlation between ES (E-mini S&P 500) and NQ (E-mini Nasdaq 100) to gauge relative strength vs. relative weakness via SMT divergence.
- **Gold & Forex:** None mentioned in this episode.

---

## Ambiguities and Open Questions

- **Exact add-on trigger criteria:** ICT adds 25 contracts at 3999.00 (11:43 AM) on market order without an explicit textual rule defining whether the add-on was triggered by a specific 1-minute FVG, an order block, or simple momentum displacement.
- **Trailing stop exact tick buffer:** The stop was manually dragged and modified on TradingView; the exact point/tick buffer below the trailing swing lows was not quantified in text.
