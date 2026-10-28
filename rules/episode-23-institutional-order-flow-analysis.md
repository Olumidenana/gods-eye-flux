# Episode 23: 2022 ICT Mentorship Episode 23

**Source URL:** https://www.youtube.com/watch?v=TV9TfwHXuqs

## Summary of Episode
This episode examines live price action on the Micro E-mini Nasdaq-100 Index Futures (June 2022 contract) during an FOMC interest rate announcement afternoon (May 4, 2022). Michael (ICT) demonstrates real-time algorithmic price delivery during high-impact news. 

Key topics covered include:
- The typical profile of an FOMC release: an initial knee-jerk/shakeout leg starting at 2:00 PM EST, often producing a fakeout leg, followed by the true institutional setup forming around 2:30 PM EST.
- The precise conceptual difference between "running" liquidity versus "sweeping" liquidity.
- Fibonacci projection techniques during high-volatility events, specifically comparing wick-to-wick projections versus candle body-to-body projections.
- Identifying discount Fair Value Gaps (FVG) and Bullish/Bearish Order Blocks inside the macro range to pinpoint exact turning points before expansion toward external liquidity targets (Tuesday's high).

---

## Concrete Trading Rules

### 1. Pre-FOMC Trading Restriction
- **RULE:** Do not enter trades immediately prior to or during the initial 2:00 PM EST FOMC interest rate release, as price behavior during this window is non-directional gambling.
- **CATEGORY:** news
- **NUMBERS:** 2:00 PM EST (New York time).
- **SOURCE:** 00:38–00:43, 16:27 (community post shown on screen); SAID and SHOWN.
- **CLARITY:** Clear.

### 2. FOMC Knee-Jerk & True Trend Timing Rule
- **RULE:** Allow 2:00 PM to approximately 2:30 PM EST for the market to complete its initial knee-jerk reaction and fakeout legs; the primary institutional setup typically prices in and initiates around 2:30 PM EST.
- **CATEGORY:** session/killzone
- **NUMBERS:** 2:00 PM to 2:30 PM EST (New York time).
- **SOURCE:** 00:40–00:43, 01:46–02:02, 11:34–11:51; SAID.
- **CLARITY:** Clear.

### 3. "Running" vs. "Sweeping" Liquidity Definitions
- **RULE:** A "sweep" occurs when price trades shallowly above an old high (or below an old low) and immediately reverses back into the range; a "run" occurs when price trades through the old reference level and displaces continuously in that direction without looking back.
- **CATEGORY:** sweep
- **NUMBERS:** Not stated.
- **SOURCE:** 04:42–05:51, 15:21–15:30; SAID.
- **CLARITY:** Clear.

### 4. Stop Loss Placement for FVG Scalp Short
- **RULE:** When entering short on a retracement into a Bearish Fair Value Gap, place the protective stop loss immediately above the high of the most recent up-close (green) candle to the left of the entry.
- **CATEGORY:** stop loss
- **NUMBERS:** Not stated (structural candle placement).
- **SOURCE:** 02:47–02:58, 03:30–03:35; SAID and SHOWN.
- **CLARITY:** Clear.

### 5. High-Impact News Fibonacci Anchor Selection (Wicks vs. Bodies)
- **RULE:** During high-volatility news events (e.g., FOMC), measure Fibonacci expansion targets using candle wicks to capture the full extreme range; for precise standard target delivery, compare against the candle bodies (highest and lowest open/close).
- **CATEGORY:** reference level
- **NUMBERS:** 50% equilibrium threshold; standard extension levels (e.g., -0.618 / -1.0).
- **SOURCE:** 09:23–09:48, 12:13–13:21; SAID and SHOWN.
- **CLARITY:** Clear.

### 6. Discount Fair Value Gap Target Filter
- **RULE:** To identify an institutional buy zone after a market peak, measure the price swing range from high to low; the valid discount target must reside below the 50% equilibrium level of that defined range.
- **CATEGORY:** reference level
- **NUMBERS:** 50% (Equilibrium).
- **SOURCE:** 09:23–09:48; SAID and SHOWN.
- **CLARITY:** Clear.

### 7. Bullish Order Block Identification
- **RULE:** After price reaches a key discount objective/FVG and turns higher, consecutive down-close candles preceding an impulsive up-move constitute a Bullish Order Block, which acts as support on subsequent retests.
- **CATEGORY:** entry
- **NUMBERS:** Not stated.
- **SOURCE:** 15:13–15:21; SAID and SHOWN.
- **CLARITY:** Clear.

---

## Chart Examples

### Chart Example: FOMC Afternoon Nasdaq-100 Reversal and Expansion
- **Timestamp:** 00:05–16:30
- **Instrument:** Micro E-mini Nasdaq-100 Index Futures (June 2022 contract, MNQM2022 / NQ)
- **Timeframe:** 1-minute chart (primary) and 15-minute chart (side panel at 00:05)
- **Date/Time:** May 4, 2022, between 14:00 and 15:35 EST
- **Reference Levels Identified:**
  - Tuesday's High (external buy-side liquidity target).
  - 14:00 EST swing high at ~13,184.00.
  - 1-minute Bearish FVG between ~13,115.00 and ~13,140.00.
  - Discount Fair Value Gap (turquoise box) situated below the 50% equilibrium level of the 14:00–14:32 drop (~12,975.00 to ~13,010.00).
  - Sell-side liquidity pool beneath the prior relative low (~13,012.00).
- **Liquidity Sweep / Price Action:**
  - Price briefly swept Tuesday's high pre-2:00 PM EST and immediately reversed lower.
  - At 2:00 PM EST, price broke downward impulsively, retested a bearish FVG, tagged an order block, and expanded down to 12,965.00, fully sweeping sell-side liquidity below the 13,012.00 low into the discount FVG.
  - At ~14:32 EST, price rejected out of the discount FVG, formed a bullish market structure shift and order block, and rallied aggressively.
- **Entry Point / Trigger:**
  - *Short Scalp:* Retracement into the 1-minute bearish FVG around 14:14–14:18 EST (~13,100–13,120).
  - *Long Institutional Trade:* Retracement into the bullish order block (consecutive down-close candles around 14:33–14:36 EST) after tagging the turquoise discount FVG.
- **Stop Loss Placement:**
  - *Short Scalp:* Placed directly above the high of the most recent up-close (green) candle to the left (~13,140.00).
  - *Long Trade:* Below the swing low established inside the turquoise discount FVG (~12,965.00).
- **Target / Take Profit:**
  - *Short Target:* The turquoise discount FVG / sell-side liquidity below 13,012.00.
  - *Long Target:* Fibonacci expansion target at 13,437.00, followed by running Tuesday's high.
- **Outcome:** Price hit the short discount target cleanly at ~14:32 EST, reversed sharply, and expanded over 450 points upward, reaching 13,437.00 and running well through Tuesday's high.

---

## Conditions that Cancel a Setup / Filters (What NOT to do)

1. **Do not take directional setups immediately prior to 2:00 PM EST on FOMC days:** Entering before the FOMC rate release is explicitly classified as gambling.
2. **Do not trade the immediate 2:00 PM spike blindly:** The initial 2:00 PM reaction is often a fakeout leg designed to engineer liquidity. Wait for the shakeout to conclude (typically around 2:30 PM EST).
3. **Do not buy in Premium for a high-timeframe reversal:** Long positions must not be entered until price reaches a discount level below 50% of the defined price swing.
4. **Fair Value Gap Invalidation:** If price trades completely through and closes past a Fair Value Gap in the wrong direction, that imbalance is invalidated as a support/resistance level.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
- None mentioned in this episode. (The entire session focuses exclusively on Index Futures: Micro E-mini Nasdaq-100 Futures).

---

## Ambiguities and Open Questions

1. **Discretionary FVG Selection:** ICT highlights multiple potential Fair Value Gaps during the 14:00 drop; the rule for deciding whether price will reverse from the higher FVG versus driving deeper into the lowest discount FVG relies on observing whether price "sweeps" or "runs" intermediate liquidity.
2. **Fibonacci Anchor Coordinates:** When demonstrating the Fibonacci projection at 12:13–13:21, ICT switches between wick-to-wick and candle body-to-body measurements. Algorithmic rules must define whether body-to-body or wick-to-wick is the default setting for calculating specific extension targets (e.g., 13,437.00).
3. **Eight Intraday Setups:** ICT notes there are eight distinct trade setups across the FOMC price swings, but does not explicitly enumerate every single entry rule and trigger for all eight, leaving some secondary micro-scalps ambiguous.
