# Episode 10: 2022 ICT Mentorship Episode 10

**Source URL:** [https://www.youtube.com/watch?v=S9ORTYmXwdE](https://www.youtube.com/watch?v=S9ORTYmXwdE)

---

## Summary of Episode
This episode focuses on implementing economic calendar events with the market open, focusing heavily on Nasdaq 100 (NQ) index futures. Michael J. Huddleston (ICT) introduces the news embargo lifting at 08:30 AM EST (New York time) as "crosshairs time"—the designated starting point for daily analysis. 

He explains the **Power of 3 (Accumulation, Manipulation, Distribution)** framework on the daily chart and reveals a unique projection technique: taking the distance from the Open to the High of the daily bar (the Judas swing) and projecting it below the opening price to define the "opening range" or "sell zone." 

Additionally, ICT demonstrates a **Top-Down Timeframe Strip** technique (scaling down from the 5-minute chart to the 1-minute chart) to locate a Fair Value Gap (FVG) and execute a short position when the market structure shifts with displacement. He finishes with a stern warning on risk management, advocating for a minimum of $15,000 capital per single NQ mini contract to survive current high-volatility environments.

---

## Concrete Trading Rules

### 1. The 08:30 AM News Embargo "Crosshairs" Rule
* **RULE:** The trader must use 08:30 AM New York time as the starting point ("crosshairs time") to monitor the market for setups, as this is when the morning news embargo lifts and high-impact economic data is released.
* **CATEGORY:** session/killzone
* **NUMBERS:** 08:30 AM New York Time (EST/EDT).
* **SOURCE:** `01:35 - 01:52` (Said/Showed on economic calendar slide).
* **CLARITY:** Clear.

### 2. Daily Dealing Range Equilibrium Filter
* **RULE:** To identify trade opportunities, divide the daily dealing range (from the daily swing high to the daily swing low) at the 50% level (equilibrium); look for short entries only when price is above 50% (premium market) and long entries only when price is below 50% (discount market).
* **CATEGORY:** reference level
* **NUMBERS:** 50% Equilibrium level.
* **SOURCE:** `04:02 - 04:35` (Said/Showed on NQ Daily Chart).
* **CLARITY:** Clear.

### 3. Power of 3 (AMD) Daily Range Rule
* **RULE:** On a day with a bearish bias, anticipate the daily candle/bar to open, rally above the opening price (Judas swing/Manipulation) to accumulate short positions, sell off down below the open (Distribution), and close near its daily low.
* **CATEGORY:** general principle
* **NUMBERS:** Not stated.
* **SOURCE:** `08:05 - 09:12` & `12:50 - 13:13` (Said/Showed on daily candlestick and bar diagrams).
* **CLARITY:** Clear.

### 4. Opening Range / Judas Swing Projection Rule
* **RULE:** For a bearish trading day, measure the price distance from the Daily Open to the Daily High (the Judas swing range), and project this identical range down below the opening price; this defines the boundaries of the "opening range" where all short entries ( OTE, Fair Value Gaps, or stop raids) must be executed.
* **CATEGORY:** reference level
* **NUMBERS:** 1:1 projection of the Open-to-High range plotted below the Open.
* **SOURCE:** `13:30 - 14:24` (Said/Showed on daily bar chart diagram).
* **CLARITY:** Clear.

### 5. Top-Down Timeframe Strip Rule
* **RULE:** When a bearish Market Structure Shift (MSS) occurs with displacement on a 5-minute chart but lacks a 5-minute Fair Value Gap (FVG), the programmer must scan lower timeframes sequentially (4-minute, then 3-minute, then 2-minute, then 1-minute); execute the trade at the first FVG detected and do not check any lower timeframes.
* **CATEGORY:** entry
* **NUMBERS:** Timeframes: 5m $\rightarrow$ 4m $\rightarrow$ 3m $\rightarrow$ 2m $\rightarrow$ 1m.
* **SOURCE:** `17:54 - 18:40` (Said/Showed on NQ 5m & 4m charts).
* **CLARITY:** Clear.

### 6. Stop Loss Placement on Bearish Breaker Setups
* **RULE:** When entering short on a bearish breaker pattern (defined by a swing high, a swing low, and a higher swing high followed by displacement), place the stop loss just above the breaker candle (the highest down-closed candle right before the highest high) rather than above the highest swing high.
* **CATEGORY:** stop loss
* **NUMBERS:** Placing stop loss exactly above the high of the breaker candle.
* **SOURCE:** `11:00 - 11:15` & `14:02 - 14:14` (Said/Showed on NQ 4m chart).
* **CLARITY:** Clear.

### 7. Position Sizing Capitalization Rule for NQ Minis
* **RULE:** Maintain a minimum capital balance of $15,000 per single NQ (Nasdaq E-mini) contract traded to survive high-volatility fluctuations, and avoid high-leverage discount broker margin levels (such as $1,000 - $2,000 per mini contract).
* **CATEGORY:** risk/position size
* **NUMBERS:** Minimum $15,000 capital per 1 mini contract.
* **SOURCE:** `14:50 - 16:15` (Said only).
* **CLARITY:** Clear.

---

## Chart Examples

### Chart Example 1 (Daily, Hourly, 15m, 5m, 4m Top-Down Analysis)
* **Timestamp:** `04:00 - 22:25`
* **Instrument:** Nasdaq 100 E-mini Futures (NQ - Continuous Contract)
* **Timeframe:** Daily down to 4-minute
* **Date/Time:** Thursday, February 17, 2022
* **Reference Levels Identified:** 
  * Premium vs. Discount daily equilibrium (50%) level.
  * Daily Fair Value Gap (imbalance) premium level.
  * Relative equal lows on the 15-minute chart acting as Sell-side Liquidity at 14,381.
  * Midnight New York Open Price (horizontal line).
* **Liquidity Sweep / Price Action:** Price rallied up into the daily premium FVG during the London session, consolidated overnight, pushed slightly higher to sweep buy-side liquidity above relative equal highs around 07:00 AM New York time, and then experienced a swift, energetic break lower (displacement).
* **Entry point / trigger:** Scale down to find an FVG. No FVG is present on the 5-minute chart. Scale down to the 4-minute chart where a 4m FVG is visible. Place a short limit order inside the 4m FVG (above/near the opening price, within the projected opening range).
* **Stop Loss placement:** Placed just above the high of the 4-minute breaker candle (`14:02`).
* **Target / Take Profit:** Targeted the sell-side liquidity pool at the relative equal lows (`14,381`).
* **Outcome:** Price hit the target cleanly, delivering a massive short move (`22:22`).

---

## Conditions that Cancel a Setup / Filters (What NOT to do)
* **No FVG Filter:** If, during the top-down timeframe strip (from 5-minute down to 1-minute), no Fair Value Gap is found on any of the timeframes, do not take the trade.
* **Chase Prevention Filter:** If the market leaves the projected opening range zone (the measured open-to-high range distance projected below the opening price) and continues running lower without giving an entry, do not chase the trade.

---

## Gold (XAUUSD) vs. Forex Pairs vs. Indices Differences
* **Nasdaq (NQ) Volatility vs. Margin Requirements:** ICT notes that NQ is exceptionally volatile, citing a recent occurrence of a 100-point move inside a single 1-minute candle. Because of this high volatility, he explains that brokers like TD Ameritrade require nearly $22,000 in initial margin per NQ mini contract (and previously $17,160). He explicitly states that trying to leverage discount broker margins (which let you trade for $1,000 - $2,000 per contract) will quickly result in blowing your account due to slippage during rapid 100-point moves.

---

## Ambiguities and Open Questions
* **Defining the "Opening Price":** In the Power of 3 (AMD) explanation, ICT highlights the "Daily Open" as the reference price for his range projections. However, across his chart walk-throughs, he refers to both the *Midnight New York Open Price* and the *Equities Open Price* (09:30 AM). For a fully automated algorithm, it is slightly ambiguous which of these opens should act as the anchor for the Power of 3 projection unless specifically configured.
