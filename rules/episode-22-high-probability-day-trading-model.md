# Episode 22: 2022 ICT Mentorship Episode 22

**Source URL:** https://www.youtube.com/watch?v=QKc_i90chVg

---

## Summary of Episode
In this episode, Michael J. Huddleston (ICT) reviews the daily draw on liquidity on the E-mini S&P 500 (ES) and Nasdaq 100 (NQ) futures, demonstrating how the market reached the pre-identified relative equal daily lows. He breaks down the intraday price delivery on both instruments across multiple timeframes (1-hour, 15-minute, 5-minute, and 1-minute), explaining the mechanics of the 9:30 AM New York opening manipulation, Power of 3 (AMD: Accumulation, Manipulation, Distribution), and market structure shifts with displacement. 

He demonstrates SMT Divergence between ES and NQ around the morning highs to confirm underlying weakness, explains how candle bodies respect imbalances while wicks seek liquidity, details swing point hierarchy (Short-Term, Intermediate-Term, Long-Term Highs), shows how to handle multiple nested Fair Value Gaps, reviews pyramid position-sizing rules (starting with the largest size and decreasing size on subsequent adds), walks through his live-account short execution on NQ, and provides his exact TradingView Fibonacci tool coordinates for Optimal Trade Entry (OTE) and standard deviation projection targets.

---

## Concrete Trading Rules

- **RULE:** The New York session morning trading window runs from approximately 8:00 AM to 10:30 AM–11:00 AM New York time.
  - **CATEGORY:** session/killzone
  - **NUMBERS:** 8:00 AM to 10:30 AM–11:00 AM EST/EDT (New York local time).
  - **SOURCE:** 05:00–06:10 (SAID)
  - **CLARITY:** Clear.

- **RULE:** The afternoon session trading window begins around 1:30 PM New York time, after the lunch hour price action has smoothed out, offering retracements into Fair Value Gaps or Order Blocks.
  - **CATEGORY:** session/killzone
  - **NUMBERS:** 1:30 PM EST/EDT.
  - **SOURCE:** 18:50–19:15 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** At the 9:30 AM New York equity market open, price will often exhibit an initial manipulative run (rallying above the opening price and above a recent short-term high if bearish) before reversing lower in alignment with the higher-timeframe draw on liquidity (Power of 3 / Accumulation-Manipulation-Distribution).
  - **CATEGORY:** session/killzone
  - **NUMBERS:** 9:30 AM New York time.
  - **SOURCE:** 09:38–10:05, 13:08–13:25 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** In a bearish market, price trading above an old high or above the 8:30 AM New York opening price represents a short-term premium, whereas trading below an old low represents a discount.
  - **CATEGORY:** reference level
  - **NUMBERS:** 8:30 AM New York opening price; old highs/lows.
  - **SOURCE:** 10:48–11:47 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** When analyzing an imbalance (Fair Value Gap), price may wick through the gap to raid buy-side or sell-side liquidity, but the candle bodies should predominantly close within the bounds of the imbalance if the order flow is intact.
  - **CATEGORY:** general principle
  - **NUMBERS:** Not stated.
  - **SOURCE:** 08:42–09:18, 23:33–23:42 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** In a bearish displacement setup, when price creates multiple nested Fair Value Gaps (e.g., an initial gap and a higher gap during a retracement), the trader must expect price to stab into the upper gap; the stop loss must be placed above the high of the candle that formed the upper gap or above the swing high.
  - **CATEGORY:** entry
  - **NUMBERS:** Not stated.
  - **SOURCE:** 24:06–24:35, 25:55–26:15 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** Stop loss placement for a short entry in a Fair Value Gap must be placed at a minimum above the high of the candle that creates the Fair Value Gap (the third candle in the sequence when looking backwards, or candle 1 of the 3-candle pattern), or conservatively above the swing high that preceded the displacement.
  - **CATEGORY:** stop loss
  - **NUMBERS:** High of candle 1 of the FVG pattern, or swing high.
  - **SOURCE:** 17:46–18:02 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** When scaling into a position (pyramiding), open the largest position size on the initial entry, and add progressively smaller position sizes on subsequent re-entries (e.g., 3 contracts first, then 2 contracts, then 1 contract); never add more contracts on later entries than on the initial entry.
  - **CATEGORY:** risk/position size
  - **NUMBERS:** Example given: 3 contracts, then 2 contracts, then 1 contract.
  - **SOURCE:** 34:25–34:47, 35:41–35:58 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** When taking profit at a major draw on liquidity (such as an old daily low or relative equal lows), place the limit buy-to-cover order slightly above the exact level to avoid missed fills on shallow liquidity sweeps.
  - **CATEGORY:** take profit
  - **NUMBERS:** Slightly above the key level (demonstrated on NQ: low was 13,275.50; limit exit placed at 13,285.00).
  - **SOURCE:** 36:14–36:28 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** A Long-Term High is defined as a swing high with lower intermediate-term swing highs to both its left and right; an Intermediate-Term High is a swing high that either forms with a Fair Value Gap on the down move or is lower than an adjacent Long-Term High but higher than adjacent Short-Term Highs.
  - **CATEGORY:** reference level
  - **NUMBERS:** Not stated.
  - **SOURCE:** 25:56–26:47 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** SMT (Smart Money Technique) Divergence between correlated index futures: In an overall bearish market, if one index (e.g., NQ) makes a higher high relative to a prior swing high (such as an overnight high) while a correlated index (e.g., ES) makes a lower high over the same period, it confirms that the higher high on NQ is a stop run (turtle soup) and signals institutional distribution/weakness.
  - **CATEGORY:** confirmation
  - **NUMBERS:** 5-minute timeframe comparison of overnight high (02:00–02:30 AM) vs. morning rally (09:30–10:00 AM).
  - **SOURCE:** 42:00–45:27 (SAID & SHOWED)
  - **CLARITY:** Clear.

- **RULE:** The standard Fibonacci tool settings for Optimal Trade Entry (OTE) are 0.0 (anchor low), 1.0 (anchor high), 0.50 (Equilibrium), 0.62 (62% retracement), and 0.79 (79% retracement).
  - **CATEGORY:** reference level
  - **NUMBERS:** Levels: 0.0, 0.5, 0.62, 0.79, 1.0.
  - **SOURCE:** 46:48–47:16, 48:01–48:15 (SHOWED)
  - **CLARITY:** Clear.

- **RULE:** For Fibonacci standard deviation extension targets, use negative multiples: -1.0, -1.5, -2.0, -2.5 (or positive equivalents depending on anchor orientation) to project targets below the swing low.
  - **CATEGORY:** take profit
  - **NUMBERS:** Multiples: -1.0, -1.5, -2.0, -2.5 standard deviations.
  - **SOURCE:** 47:00–47:16, 49:10–49:25 (SHOWED)
  - **CLARITY:** Clear.

- **RULE:** When applying the Fibonacci tool to measure an Optimal Trade Entry (OTE) retracement, anchor the high to the highest candle body (Open or Close) of the swing high and anchor the low to the lowest candle body (Open or Close) of the swing low, rather than using the wick extremes, to capture the bulk of the volume.
  - **CATEGORY:** entry
  - **NUMBERS:** Candle bodies (Open/Close).
  - **SOURCE:** 49:35–49:50, 50:06–50:20 (SAID & SHOWED)
  - **CLARITY:** Clear.

---

## Chart Examples

### Chart Example 1: ES June 2022 Contract (Daily to 15-Minute)
- **Timestamp:** 00:40–02:05 (Daily), 08:00–10:45 (15-min)
- **Instrument:** E-mini S&P 500 Futures (ESM2022)
- **Timeframe:** Daily & 15-Minute
- **Date/Time:** April 29, 2022
- **Reference Levels identified:** Daily relative equal lows at ~4138.75 and ~4101.75; 15-minute imbalance / opening gap down from overnight.
- **Liquidity Sweep / Price Action:** Price opened at 9:30 AM NY time, spiked upward to run short-term buy-side liquidity above a local high, then displaced sharply downward breaking below local swing lows.
- **Entry point / trigger:** Retracement back up into the 15-minute Fair Value Gap formed by the displacement between 9:45 AM and 10:00 AM, situated above the 8:30 AM opening price.
- **Stop Loss placement:** Above the swing high of the 9:30 AM opening manipulation run.
- **Target / Take Profit:** Daily relative equal lows (~4138.75 and down to 4101.75).
- **Outcome:** Market sold off aggressively into the afternoon, expanding directly through the daily relative equal lows.

### Chart Example 2: ES June 2022 Contract (5-Minute Morning & Afternoon Sessions)
- **Timestamp:** 15:15–19:35
- **Instrument:** E-mini S&P 500 Futures (ESM2022)
- **Timeframe:** 5-Minute
- **Date/Time:** April 29, 2022
- **Reference Levels identified:** 5-minute relative equal highs, 8:30 AM opening price, 1:30 PM post-lunch FVG and Bearish Order Block.
- **Liquidity Sweep / Price Action:** Price swept the relative equal highs after 9:30 AM open, displaced lower, retested the FVG above the 8:30 AM open line, then dropped. In the afternoon session (after 1:30 PM), price retraced up into a 5-minute bearish order block and FVG.
- **Entry point / trigger:** Short entry inside the FVG above 8:30 open in the morning; secondary short entry at ~1:30 PM on retest of the bearish order block/FVG.
- **Stop Loss placement:** Above the 5-minute high of the manipulative run.
- **Target / Take Profit:** The daily target low (blue horizontal line).
- **Outcome:** Price hit the target low with high speed.

### Chart Example 3: NQ June 2022 Contract (1-Minute Live Trade Execution Walkthrough)
- **Timestamp:** 20:18–37:00
- **Instrument:** E-mini Nasdaq 100 Futures (NQM2022)
- **Timeframe:** 5-Minute down to 1-Minute
- **Date/Time:** April 29, 2022 (Overnight into morning session)
- **Reference Levels identified:** Overnight swing high at 2:30 AM (13,448.75), 5-minute displacement below swing low creating a 5-minute FVG, refined to a 1-minute bearish order block.
- **Liquidity Sweep / Price Action:** NQ ran higher to take out the overnight high (13,448.75), printing 13,458.75, while ES failed to take its overnight high (SMT Divergence). NQ then displaced downward.
- **Entry point / trigger:** 
  1. Entry 1: Short 3 contracts in the upper FVG at ~13,382.
  2. Entry 2: Short 2 contracts at 13,338.50 on the retest of the refined 1-minute bearish order block / FVG.
  3. Entry 3: Short 1 contract at 13,335.00 as price tapped the midpoint of the bearish order block (the lowest candle body open/close of the up-candle).
- **Stop Loss placement:** Above the upper Fair Value Gap / swing high (13,458.75).
- **Target / Take Profit:** Limit buy order to cover all 6 contracts placed at 13,285.00, just above the sell-side liquidity pool resting below the swing low at 13,275.50.
- **Outcome:** Price dropped directly into the 13,285 target, filling all 6 contracts in profit.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)

- **Do NOT execute live trades based on chat or live commentary:** Do not treat live stream chart annotations or market analysis as trade signals; use them purely for observational learning.
- **Do NOT enter on the lowest timeframe FVG if higher-level imbalances exist above:** If an upper Fair Value Gap sits above the initial gap within the same displacement structure, do not assume price will reverse from the lower gap without testing or stabbing into the upper gap.
- **Do NOT invert position sizing during scaling/pyramiding:** Never add more contracts than your initial position size on pullbacks (e.g., adding 3 contracts after an initial 1 contract is forbidden; sizing must taper down: 3, then 2, then 1).
- **Do NOT place target limit orders exactly at or below the target liquidity level:** For sell-side targets, do not place limit buy orders below or right at the tick of the low; place them slightly above to avoid missing fills due to shallow sweeps.
- **Do NOT trade during the lunch hour lull:** Avoid trading between 12:00 PM and 1:30 PM New York time; wait until 1:30 PM when the afternoon trend resumes.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
- **SMT Divergence specific to Index Futures:** ICT explicitly demonstrates SMT Divergence using correlated index pairs: E-mini S&P 500 (ES) vs. E-mini Nasdaq 100 (NQ). When NQ makes a higher high and ES fails to make a higher high, it reveals artificial manipulation / stop-running on NQ and confirms institutional weakness in equity index futures.
- No differences for Gold or Forex pairs mentioned in this episode.

---

## Ambiguities and Open Questions

- **Fibonacci Standard Deviation Anchoring Direction:** In TradingView, depending on whether the Fibonacci tool is dragged top-to-bottom or bottom-to-top, negative values (-1.0, -1.5, -2.0) project downward or upward. Algorithmic rules must strictly enforce the math: $\text{Target} = \text{Low} - k \times (\text{High} - \text{Low})$ for downward projections, regardless of chart tool polarity.
- **Distance of Take-Profit Offset Above Key Lows:** ICT states he placed his take profit "just above" the key low (target set at 13,285.00 vs. low at ~13,275.50, an offset of ~9.5 points / 38 ticks on NQ). He does not provide a fixed point or tick formula for this buffer across different asset classes.
- **Criteria for choosing initial pyramid size:** While he illustrates a 3-2-1 contract pyramid structure, the rule for determining whether a setup qualifies for multi-tier pyramiding versus a single full-size entry is not formalized mathematically.
