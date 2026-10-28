# Master ICT 2022 Mentorship Trading Rules Register

This document is the authoritative, definitive rule specification for the `ict-trader` automated trading system. It synthesizes all concrete trading rules, execution parameters, risk management mandates, and market filters extracted directly from Michael J. Huddleston's (ICT) complete 41-episode *2022 ICT Mentorship* series.

Every automated decision made by the system (signal generation, level invalidation, entry trigger, stop loss placement, partial profit taking, trailing stop, news flattening, and session exit) cites one of these structured Rule IDs in its journal and execution telemetry.

---

## 1. Master Rule Register

### 1.1 Session Timing & Killzones (`KZ-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **KZ-01** | **New York Midnight True Day Open:** The daily algorithmic cycle and Power of 3 (Accumulation, Manipulation, Distribution) is anchored to 00:00 New York local time (Eastern). For bullish days, the low of the day is typically formed below the 00:00 midnight open; for bearish days, the high of the day forms above it. | Ep 25 [26:00], Ep 37 [14:58], Ep 38 [16:50], Ep 39 [09:21] (Said & Showed) | `strategy.midnight_open_anchor` | `00:00 America/New_York` | Confirmed |
| **KZ-02** | **New York AM News Embargo Lift:** At 08:30 New York local time, macroeconomic news releases lift embargo, initializing institutional algorithm spooling and volatility into liquidity pools. | Ep 08 [01:25], Ep 25 [34:06], Ep 39 [39:35] (Said & Showed) | `strategy.news_embargo_time` | `08:30 America/New_York` | Confirmed |
| **KZ-03** | **US Equity Market Open (Judas Swing Window):** At 09:30 New York local time, the US equity open creates the primary intraday manipulation / false run (Judas Swing) into opposing liquidity before true distribution begins. | Ep 08 [08:15], Ep 16 [12:30], Ep 24 [06:18], Ep 25 [27:10], Ep 36 [02:20] (Said & Showed) | `strategy.equity_open_time` | `09:30 America/New_York` | Confirmed |
| **KZ-04** | **London Session Killzone (Forex & Gold):** Primary London execution window is 02:00 to 05:00 New York local time. Establishes the London high or low of the day. | Ep 01 [10:45], Ep 21 [04:15], Ep 40 [08:31] (Said & Showed) | `strategy.killzones.london` | `02:00–05:00 America/New_York` | Confirmed |
| **KZ-05** | **New York AM Session Killzone (Forex):** Primary NY morning execution window for Forex currency pairs (GBPUSD, EURUSD, USDCAD) is 07:00 to 10:00 New York local time. | Ep 01 [11:15], Ep 11 [06:20], Ep 40 [08:31] (Said) | `strategy.killzones.ny_forex_am` | `07:00–10:00 America/New_York` | Confirmed |
| **KZ-06** | **New York AM Session Killzone (Indices & Gold):** Primary NY morning execution window for Index Futures (ES, NQ) and Gold (XAUUSD) is 08:30 to 11:00 New York local time. Setups must not be taken before 08:30 or after 11:00 in the morning. | Ep 02 [24:00], Ep 08 [01:25], Ep 40 [15:13], Ep 41 [03:34] (Said & Showed) | `strategy.killzones.ny_index_am` | `08:30–11:00 America/New_York` | Confirmed |
| **KZ-07** | **London Close Profit-Taking Window:** Between 10:00 and 11:00 New York local time, European institutions close intraday positions, creating significant liquidity absorption, counter-trend retracements, or acceleration into daily targets. | Ep 16 [28:10], Ep 40 [17:32] (Said & Showed) | `strategy.london_close_window` | `10:00–11:00 America/New_York` | Confirmed |
| **KZ-08** | **New York Midday Lunch Hour Blackout:** Trading is strictly forbidden between 12:00 and 13:00 New York local time (extended to 13:30 in low volatility). Price during lunch is random, choppy, whipsaw liquidity manipulation. | Ep 08 [14:40], Ep 15 [07:15], Ep 30 [01:17], Ep 31 [08:13], Ep 41 [07:15] (Said & Showed) | `strategy.lunch_blackout` | `12:00–13:00 America/New_York` | Confirmed |
| **KZ-09** | **New York PM Session Killzone:** Afternoon session operates from 13:30 to 16:00 New York local time. Active execution window is 13:30 to 15:00. Often sweeps the NY lunch hour highs/lows before continuation. | Ep 18 [09:15], Ep 27 [04:30], Ep 30 [05:37], Ep 33 [06:50], Ep 41 [06:20] (Said & Showed) | `strategy.killzones.ny_pm` | `13:30–16:00 America/New_York` | Confirmed |
| **KZ-10** | **Market-on-Close (MOC) Spooling Window:** Between 15:00 and 16:00 New York local time, algorithm spools price aggressively to clear remaining daily liquidity pools or mean-revert to the daily range 50% midpoint on consolidation days. | Ep 30 [05:12], Ep 32 [01:00], Ep 33 [07:00], Ep 39 [15:55] (Said & Showed) | `strategy.moc_window` | `15:00–16:00 America/New_York` | Confirmed |

---

### 1.2 Reference Levels & Dealing Ranges (`RL-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **RL-01** | **Prior Trading Day High / Low (PDH / PDL):** Previous day's high and low serve as external liquidity pools resting above/below the market. Daily rollover is anchored to 17:00 New York local time. | Ep 03 [05:12], Ep 12 [08:45], Ep 31 [00:53] (Said & Showed) | `strategy.use_prior_day_levels`, `strategy.day_rollover` | `true`, `17:00 America/New_York` | Confirmed |
| **RL-02** | **Asian Session Range:** High and low between 20:00 and 00:00 New York local time (Tokyo/Asian session) form key reference liquidity pools swept during the London or early NY killzones. | Ep 01 [08:30], Ep 03 [06:15], Ep 13 [14:20] (Said & Showed) | `strategy.reference_ranges.asia` | `20:00–00:00 America/New_York` | Confirmed |
| **RL-03** | **Sunday Opening Gap:** The gap formed between Friday's close (17:00 NY) and Sunday's futures open (18:00 NY) serves as a persistent dynamic support and resistance benchmark across the entire trading week. | Ep 34 [00:35, 09:46] (Said & Showed) | `strategy.track_sunday_open_gap` | `true` | Confirmed |
| **RL-04** | **Prior Week High / Low (PWH / PWL):** Prior week extreme levels serve as primary macro draw-on-liquidity targets for weekly expansions. | Ep 02 [12:44], Ep 33 [04:05], Ep 40 [20:12] (Said & Showed) | `strategy.use_prior_week_levels` | `true` | Confirmed |
| **RL-05** | **Trailing Three-Day Price Action Context:** Intraday price delivery must be evaluated in context of the open, high, low, and close of the trailing 3 trading days (e.g. Tuesday rebalancing Monday's range back to Friday's low). | Ep 25 [20:09, 34:24] (Said & Showed) | `strategy.trailing_days_lookback` | `3` | Confirmed |
| **RL-06** | **Dealing Range Equilibrium (50% Rule):** The active dealing range is measured from the significant swing low to the swing high of the impulse leg in the intended trade direction. Levels >50% are Premium; levels <50% are Discount. Longs ONLY in Discount; shorts ONLY in Premium. | Ep 02 [14:30], Ep 03 [11:15], Ep 29 [05:13], Ep 34 [15:38], Ep 36 [01:00] (Said & Showed) | `strategy.dealing_range_filter` | `true (Equilibrium = 0.50)` | Confirmed |
| **RL-07** | **Level Spent Once Swept That Day:** A reference level (PDH/PDL, session high/low) that has already been swept through is considered spent and cannot trigger a second reversal setup on the same trading day. | Ep 06 [14:20], Ep 12 [22:15], Ep 40 [18:02] (Said & Showed) | `strategy.invalidate_levels_taken_outside_killzone` | `true` | Confirmed |

---

### 1.3 Liquidity Sweeps & Purge Sequence (`SW-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **SW-01** | **Minimum Sweep Threshold:** Price must trade beyond a reference level by at least `min_sweep_pips` (or handles) inside a valid killzone to constitute a genuine liquidity sweep, rather than a mere tap. | Ep 04 [08:30], Ep 06 [11:10], Ep 16 [14:25] (Said & Showed) | `strategy.min_sweep_pips` | `0.5 pips (Forex) / 0.75 pts (ES) / 1.5 pts (Gold)` | Confirmed |
| **SW-02** | **Order of Liquidity Purging Filter:** For a valid short setup, price MUST sweep Buy-side Liquidity (BSL) first. If price sweeps Sell-side Liquidity (SSL) first, the short setup is immediately invalidated. Conversely, for a long setup, SSL must be swept first. | Ep 25 [15:10, 28:40] (Said & Showed) | `strategy.enforce_liquidity_purge_order` | `true` | Confirmed |
| **SW-03** | **Equal Highs / Equal Lows (EQH / EQL) as Primary Draw:** Relatively equal highs or lows represent engineered retail liquidity pools. They act as magnets and serve as the highest-probability targets for liquidity runs. | Ep 04 [12:15], Ep 06 [05:40], Ep 29 [01:15], Ep 39 [20:45] (Said & Showed) | `strategy.target_equal_highs_lows` | `true` | Confirmed |
| **SW-04** | **NY Lunch Liquidity Sweep for PM Continuation:** In a trending market, the highs or lows established during the 12:00–13:00 NY lunch hour are routinely swept between 13:00 and 14:00 to trap breakout traders before the true afternoon trend resumes. | Ep 30 [01:17], Ep 38 [20:20], Ep 39 [17:05] (Said & Showed) | `strategy.sweep_lunch_extremes_in_pm` | `true` | Confirmed |

---

### 1.4 Market Structure Shifts & Displacement (`MS-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **MS-01** | **Strict 3-Candle Swing Definition:** A valid swing high is defined strictly as a 3-candle pattern where the middle candle has a higher high than both the preceding and succeeding candles. A swing low requires the middle candle to have a lower low than both neighbors. | Ep 03 [08:20], Ep 05 [04:15], Ep 40 [04:39] (Said & Showed) | `strategy.swing_definition` | `3-candle pattern` | Confirmed |
| **MS-02** | **Market Structure Shift (MSS) with Displacement:** Following a liquidity sweep, price must aggressively displace across a recent 3-candle swing point with large-bodied candles, creating a structural shift. Merely wicking beyond a level without displacement is NOT a setup. | Ep 05 [06:30], Ep 22 [05:40], Ep 24 [06:28, 33:28], Ep 36 [02:40] (Said & Showed) | `strategy.require_displacement_mss` | `true` | Confirmed |
| **MS-03** | **Execution Timeframes for Structure:** Market structure shifts and Fair Value Gaps must be identified on execution timeframes: 1-minute, 2-minute, 3-minute, or 5-minute charts (15-minute serves as the higher-timeframe bellwether). | Ep 02 [16:40], Ep 05 [11:20], Ep 31 [05:10], Ep 38 [11:25] (Said) | `strategy.timeframe_minutes` | `5m (with 1m/2m micro refinement)` | Confirmed |
| **MS-04** | **Consolidation Range Break Requirement:** When price is trapped within early morning consolidation, no trades may be taken until the defining structural swing boundary (high or low) is decisively broken with displacement. | Ep 33 [01:23, 04:05], Ep 36 [05:25] (Said & Showed) | `strategy.wait_for_consolidation_break` | `true` | Confirmed |
| **MS-05** | **Bearish / Bullish Breaker Structure:** A breaker is formed when price creates a swing low/high, sweeps liquidity to a higher high/lower low, and then sharply breaks structure. Retracement into the breaker's origin candle is a high-probability re-entry. | Ep 05 [14:10], Ep 37 [02:25], Ep 39 [20:25] (Said & Showed) | `strategy.use_breaker_blocks` | `true` | Confirmed |

---

### 1.5 Fair Value Gaps & Imbalances (`FV-` & `OB-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **FV-01** | **3-Candle Fair Value Gap Definition:** A Fair Value Gap (FVG) is strictly an imbalance between Candle 1 and Candle 3 of a 3-candle sequence: for bearish FVG, gap between Candle 1 low and Candle 3 high; for bullish FVG, gap between Candle 1 high and Candle 3 low. | Ep 02 [18:10], Ep 05 [08:45], Ep 07 [03:15], Ep 34 [02:56] (Said & Showed) | `strategy.fvg_pattern` | `3-candle imbalance` | Confirmed |
| **FV-02** | **Displacement Leg 50% Equilibrium Filter:** For a bearish setup, the entry FVG MUST form in Premium (above 50% of the displacement leg). If the FVG forms in Discount (below 50%), the short setup is cancelled. Conversely, for a long setup, the FVG must form in Discount (below 50%). | Ep 29 [05:13–05:25], Ep 33 [05:30], Ep 34 [16:09] (Said & Showed) | `strategy.fvg_displacement_equilibrium_filter` | `true (>50% for shorts, <50% for longs)` | Confirmed |
| **FV-03** | **Consequent Encroachment (50% of FVG):** The midpoint (50%) of a Fair Value Gap is its Consequent Encroachment (CE). Price may touch the boundary or trade down to CE; sustained body closes through CE indicate gap failure. | Ep 07 [06:20], Ep 25 [11:15], Ep 34 [03:19] (Said & Showed) | `strategy.fvg_consequent_encroachment` | `0.50 of FVG range` | Confirmed |
| **FV-04** | **Rebalanced Gap Filter:** Once an FVG has been traded through and completely filled/rebalanced by subsequent price action, it is spent and cannot be used for new entry setups. | Ep 07 [14:40], Ep 25 [18:02], Ep 40 [18:02] (Said & Showed) | `strategy.invalidate_rebalanced_fvg` | `true` | Confirmed |
| **OB-01** | **Order Block Sensitive Levels:** The three sensitive price levels of an Order Block are its Low, its Open, and its Mean Threshold (50% midpoint of the total candle range). | Ep 07 [09:30], Ep 35 [00:37–01:12] (Said & Showed) | `strategy.order_block_levels` | `low, open, mean_threshold` | Confirmed |
| **OB-02** | **Mean Threshold Violation Continuation Rule:** If price trades into a daily/intraday bearish order block and exceeds its 50% Mean Threshold, it signals institutional strength and a high probability of continuation to purge the swing high above that block. | Ep 35 [00:54–01:08] (Said & Showed) | `strategy.ob_mean_threshold_continuation` | `0.50 of OB range` | Confirmed |

---

### 1.6 Confirmations & Smart Money Technique (`CF-` & `SMT-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **CF-01** | **3-Candle Swing Confirmation Inside FVG:** Rather than placing a blind limit order inside an FVG, enter after price trades into the FVG and prints a confirmed 3-candle swing high/low pattern on the execution timeframe. | Ep 31 [07:02–07:18] (Said & Showed) | `strategy.require_swing_confirmation_in_fvg` | `true (optional conservative trigger)` | Trader Choice |
| **SMT-01** | **Bullish SMT Divergence (Correlated Assets):** When one correlated asset (e.g. NQ) breaks a swing low to sweep sell-side liquidity while another correlated asset (e.g. ES) fails to break its swing low (making a higher low), smart money accumulation is confirmed. The asset making the higher low is the stronger candidate to trade long. | Ep 28 [03:50], Ep 29 [03:50], Ep 35 [07:06], Ep 38 [16:20] (Said & Showed) | `strategy.enable_smt_divergence` | `true` | Confirmed |
| **SMT-02** | **Bearish SMT Divergence:** When one correlated asset makes a higher high (sweeping buy-side liquidity) while the other makes a lower high, smart money distribution is confirmed. The asset making the lower high is the weaker candidate to trade short. | Ep 21 [08:45], Ep 28 [06:10], Ep 35 [08:14] (Said & Showed) | `strategy.enable_smt_divergence` | `true` | Confirmed |
| **SMT-03** | **SMT Divergence Timing:** SMT Divergence must be evaluated specifically around key timing windows: 08:30 NY news embargo, 09:30 NY equity open, or during scheduled high-impact releases. | Ep 35 [07:27–07:38], Ep 38 [19:35] (Said) | `strategy.smt_timing_windows` | `08:30, 09:30, and news releases` | Confirmed |
| **SMT-04** | **SMT Line Comparison Chart Settings:** When comparing correlated assets using line chart overlays, the comparison line must be plotted on "Low" for bullish divergence and "High" for bearish divergence (not "Close"). | Ep 35 [06:48–07:05] (Said & Showed) | `strategy.smt_comparison_mode` | `extreme (low/high, not close)` | Confirmed |

---

### 1.7 Entry Execution & Triggers (`EN-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **EN-01** | **FVG Retracement Limit Entry:** Place a limit order at the near boundary of the Fair Value Gap once a Market Structure Shift with displacement is validated. | Ep 02 [18:25], Ep 05 [10:30], Ep 22 [08:15], Ep 36 [05:40] (Said & Showed) | `strategy.entry_mode` | `fvg_boundary (limit)` | Confirmed |
| **EN-02** | **Consequent Encroachment Limit Entry:** Place a limit order at the exact 50% midpoint of the FVG for tighter stop loss and higher reward-to-risk ratio. | Ep 07 [06:20], Ep 25 [11:15] (Said & Showed) | `strategy.entry_mode` | `fvg_consequent_encroachment` | Trader Choice |
| **EN-03** | **Close Proximity Entry:** If a limit entry at an FVG boundary is narrowly missed by price, a market order is permitted as long as price remains within close proximity (within a defined tick/pip threshold) before displacement occurs. | Ep 29 [07:02–07:44], Ep 30 [01:37] (Said & Showed) | `strategy.close_proximity_entry_allowed`, `strategy.close_proximity_max_ticks` | `false`, `2 ticks / 0.5 pips` | Trader Choice |
| **EN-04** | **Stale Signal Expiration:** If an order placed at an FVG is not filled within `max_confirm_bars` bars after the market structure shift, the signal expires and the order is cancelled. | Ep 08 [12:10], Ep 22 [11:45] (Said) | `strategy.max_confirm_bars` | `3 bars (on 5m chart) / 15 minutes` | Confirmed |

---

### 1.8 Stop Loss Placement & Risk Management (`SL-` & `RK-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **SL-01** | **Protective Stop Placement (Sweep Extreme):** Place the protective stop loss immediately beyond the swing high (for shorts) or swing low (for longs) established during the liquidity sweep, plus a buffer. | Ep 02 [22:35], Ep 05 [12:10], Ep 22 [09:15], Ep 36 [04:17] (Said & Showed) | `strategy.stop_mode`, `strategy.stop_buffer_pips` | `swing_extreme`, `1.0 pip (Forex) / 1.5 pts (Gold/ES)` | Confirmed |
| **SL-02** | **Alternative Stop Placement (FVG Candle 1 Extreme):** Place the stop loss beyond Candle 1 of the 3-candle Fair Value Gap formation if the sweep extreme is too distant. | Ep 02 [22:45], Ep 40 [14:27, 16:45] (Said & Showed) | `strategy.stop_mode` | `fvg_candle_1` | Trader Choice |
| **SL-03** | **Minimum and Maximum Stop Distance Limits:** Reject any setup where the required stop distance is narrower than `min_stop_pips` (noise) or wider than `max_stop_pips` (excessive adverse excursion). | Ep 07 [16:20], Ep 40 [15:02] (Said) | `strategy.min_stop_pips`, `strategy.max_stop_pips` | `3 pips / 25 pips (Forex); 10 pts / 60 pts (Gold/ES)` | Confirmed |
| **SL-04** | **Milestone Stop Trimming (50% Target Reached):** When price reaches 50% of the distance from entry to the final target objective, trim the stop loss risk distance by 25%. | Ep 41 [49:57–50:30] (Said & Showed) | `strategy.trim_stop_at_50_pct_target` | `true (reduce stop distance by 25%)` | Confirmed |
| **SL-05** | **Milestone Breakeven (75% Target Reached):** When price reaches 75% of the distance from entry to the final target objective, move the stop loss to exact Breakeven (entry price + spread). | Ep 41 [50:57] (Said & Showed) | `strategy.move_be_at_75_pct_target` | `true` | Confirmed |
| **RK-01** | **Base Risk Per Trade:** Standard risk per trade is sized to 1.0% of current account equity (or 0.25% to 0.50% for prop firm challenges). | Ep 07 [18:15], Ep 41 [22:27] (Said) | `risk.risk_per_trade_pct` | `0.5% (Prop Firm) / 1.0% (Standard)` | Confirmed |
| **RK-02** | **Dynamic Risk Reduction After Losses:** If a trade loses, reduce the risk on the subsequent trade to 0.5%. If that trade also loses, reduce risk further to 0.25%. | Ep 41 [31:17, 43:22] (Said) | `risk.enable_dynamic_risk_reduction` | `true` | Confirmed |
| **RK-03** | **Risk Recovery Threshold:** To restore risk back to 1.0% after a drawdown, the trader must earn back at least 50% of the lost equity using the reduced risk tier. | Ep 41 [32:03] (Said) | `risk.loss_recovery_threshold_pct` | `50% of loss recovered` | Confirmed |
| **RK-04** | **Daily and Weekly Equity Loss Floors:** Account-level circuit breakers. If equity drops by `max_daily_loss_pct` (e.g. 2%) or `max_weekly_loss_pct` (e.g. 4%), all trading is immediately halted until the next session/week. | Ep 07 [20:10], Ep 41 [45:10] (Said) | `risk.max_daily_loss_pct`, `risk.max_weekly_loss_pct` | `2.0% daily / 4.0% weekly` | Confirmed |
| **RK-05** | **Maximum Consecutive Losses & Daily Trade Limits:** Maximum allowed trades per day is 2. Maximum consecutive losses is 2. Stop trading immediately after 2 losses in a single day. | Ep 18 [22:15], Ep 39 [51:57], Ep 41 [44:00] (Said) | `risk.max_trades_per_day`, `risk.max_consecutive_losses` | `2 trades / 2 losses` | Confirmed |

---

### 1.9 Take Profit & Trade Scaling (`TP-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **TP-01** | **Opposing Liquidity Pool Target:** Final take profit objective is anchored to the nearest un-swept external liquidity pool (prior day high/low, session high/low, or relative equal highs/lows). | Ep 02 [23:15], Ep 06 [08:30], Ep 22 [10:15] (Said & Showed) | `strategy.target_mode` | `opposing_liquidity` | Confirmed |
| **TP-02** | **Minimum Reward-to-Risk Ratio:** A setup must offer a projected reward-to-risk ratio of at least 1.5R to the primary target; otherwise the trade is skipped. | Ep 07 [15:20], Ep 14 [08:45] (Said) | `strategy.min_rr` | `1.5` | Confirmed |
| **TP-03** | **Low-Hanging Fruit Objective (Beginner / Scalp Target):** For index futures, target 5.0 handles on ES; for Forex, target 15 to 20 pips as a reliable partial profit or base scalp objective. | Ep 08 [10:30], Ep 39 [31:38, 48:24] (Said) | `strategy.low_hanging_fruit_pips` | `5.0 pts (ES) / 15.0 pips (Forex)` | Confirmed |
| **TP-04** | **Partial Scaling at Intermediate Pools:** Take 50% to 80% partial profit off the table upon reaching the first short-term swing point or London Close window (10:00–11:00 NY), leaving a runner position with risk moved to Breakeven. | Ep 09 [06:40], Ep 14 [07:15], Ep 31 [08:00], Ep 40 [17:32] (Said & Showed) | `strategy.partial_scale_pct` | `50% at TP1, runner to TP2` | Confirmed |
| **TP-05** | **Consolidation Day 50% Midpoint Fade Target:** On identified consolidation days, late-session (15:00–16:00 NY) fades of range sweeps target the exact 50% midpoint of the daily high-to-low range. | Ep 32 [06:53, 09:09] (Said & Showed) | `strategy.consolidation_midpoint_target` | `0.50 of daily high-low range` | Confirmed |

---

### 1.10 News & Macro Calendar Filters (`NF-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **NF-01** | **High-Impact News Blackout Window:** No new trade entries are permitted within 30 minutes before or 30 minutes after any scheduled Red Folder / High-Impact economic event affecting the traded currency. | Ep 11 [04:15], Ep 15 [07:00], Ep 24 [20:25] (Said) | `news.blackout_minutes_before`, `news.blackout_minutes_after` | `30 min before / 30 min after` | Confirmed |
| **NF-02** | **Pre-News Trade Flattening:** Open intraday positions must be fully closed 5 minutes prior to a scheduled high-impact macroeconomic release to eliminate slippage and spread widening risk. | Ep 11 [08:30], Ep 15 [07:14] (Said) | `news.flatten_minutes_before` | `5 minutes` | Confirmed |
| **NF-03** | **FOMC & Federal Reserve Chairman Speech Blackout:** On days with a scheduled 14:00 NY Federal Reserve interest rate decision or Fed Chair speech, do NOT trade the afternoon session; morning trading must finish early. | Ep 15 [07:00], Ep 29 [01:17], Ep 30 [00:23], Ep 41 [00:33] (Said) | `news.fomc_blackout` | `true (no PM trading on FOMC days)` | Confirmed |
| **NF-04** | **Non-Farm Payroll (NFP) Wednesday Cutoff:** On the week featuring the Friday NFP report, stop all trading for the week by the conclusion of the Wednesday New York session. Strictly no trading on NFP Thursday or Friday. | Ep 36 [08:08], Ep 37 [07:44, 11:20] (Said) | `news.nfp_week_stop_day` | `Wednesday 12:00 America/New_York` | Confirmed |
| **NF-05** | **Holiday and Pre-Holiday Blackout:** No trading on bank holiday Mondays, and no trading during Friday afternoons preceding a 3-day holiday weekend. | Ep 35 [15:26–16:15] (Said) | `news.holiday_blackout` | `true` | Confirmed |

---

### 1.11 Platform Execution & Session Flatten (`EX-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **EX-01** | **Mandatory Intraday Session Flatten:** Any open position must be unconditionally flattened at 16:00 New York local time (market close). No trades held overnight into electronic rollover. | Ep 08 [15:30], Ep 20 [14:15], Ep 41 [06:20] (Said) | `strategy.flatten_time` | `16:00 America/New_York` | Confirmed |
| **EX-02** | **Weekend Rollover Flatten:** All positions must be closed and orders cancelled by Friday 16:00 New York local time before the weekend shutdown. | Ep 08 [16:00], Ep 20 [14:40] (Said) | `strategy.weekend_flatten_time` | `Friday 16:00 America/New_York` | Confirmed |
| **EX-03** | **Zero AI / Deterministic Live Execution:** All live trade signals, state transitions, order entries, and risk management must execute deterministically without real-time LLM inference in the critical execution path. | System Architecture Mandate | `execution.engine` | `deterministic_finite_state_machine` | Confirmed |

---

### 1.12 ICT Silver Bullet Models (`SB-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **SB-01** | **Silver Bullet 60-Minute Execution Windows:** The model operates strictly within three daily 60-minute windows: London Open (03:00–04:00 NY), NY AM Session (10:00–11:00 NY), and NY PM Session (14:00–15:00 NY). Any FVG formed outside these windows is skipped. | 2023 Mentorship [02:40, 03:02] (Said & Showed) | `strategy.silver_bullet.windows` | `London: 03:00–04:00, NY AM: 10:00–11:00, NY PM: 14:00–15:00` | Confirmed |
| **SB-02** | **Silver Bullet Entry Trigger:** Once price sweeps liquidity or reaches a draw, enter on the first Fair Value Gap (1m or 5m) created with displacement inside the 60-minute window. | 2023 Mentorship [04:30, 14:15] (Said & Showed) | `strategy.silver_bullet.entry_mode` | `first_fvg_limit` | Confirmed |
| **SB-03** | **Silver Bullet Target Objectives:** Minimum fixed target of 10–15 pips on Forex (GBPUSD/EURUSD), 10 handles on NQ/ES, and 20–30 handles on Gold (XAUUSD). | 2023 Mentorship [04:45, 12:30] (Said) | `strategy.silver_bullet.fixed_target_pips` | `15 pips (Forex) / 10 pts (Indices) / 25 pts (Gold)` | Confirmed |
| **SB-04** | **Silver Bullet Pre-Window Target Invalidation:** If the intended draw on liquidity or 10-pip/handle target is reached before price retraces into the FVG, the setup is invalidated. | 2023 Mentorship [11:15] (Said) | `strategy.silver_bullet.invalidate_if_target_hit_first` | `true` | Confirmed |

---

### 1.13 ICT Algorithmic Time Macros (`MC-`)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **MC-01** | **Algorithmic 20-Minute Time Macro Windows:** The central bank algorithm executes specific liquidity runs and FVG rebalancings during dedicated 20-minute windows: 08:50–09:10 NY, 09:50–10:10 NY, 10:50–11:10 NY, 13:50–14:10 NY, and 14:50–15:10 NY. | 2023 Mentorship Macros [05:20, 22:50] (Said & Showed) | `strategy.macros.active_windows` | `08:50-09:10, 09:50-10:10, 10:50-11:10, 13:50-14:10, 14:50-15:10` | Confirmed |
| **MC-02** | **Macro Volatility Injection:** If price has not reached its draw on liquidity by the start of a Macro, treat the window as an algorithmic impulse injection toward the draw. | 2023 Mentorship Macros [15:40] (Said) | `strategy.macros.enable_injection_tracking` | `true` | Confirmed |
| **MC-03** | **Late Morning Macro Trend Finale (10:50–11:10 NY):** The 10:50–11:10 Macro is the final algorithmic delivery window of the morning session; no new morning setups permitted after 11:10 NY. | 2023 Mentorship Macros [24:15] (Said) | `strategy.macros.morning_cutoff_time` | `11:10 America/New_York` | Confirmed |

---

### 1.14 Small Account & Cent Compounding Engine (`SA-`)

| ID | Rule Description | Purpose / Architectural Mechanism | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **SA-01** | **USD Cent (USC) Account Scaling:** For small balances ($10 to $50), automatically convert balance to Cents (1 USD = 100 USC, so $10 = 1,000 cents). Enables mathematically pure 0.5%–1.0% institutional risk without hitting broker 0.01 lot minimum. | `risk.is_cent_account` | `true (for Cent accounts)` | Confirmed |
| **SA-02** | **Micro-Account Fixed Risk Floor ($10–$50 Standard Accounts):** On standard micro accounts where balance is $10–$50, permit fixed micro-risk sizing (0.01 lot fixed = ~$1.00 risk) instead of returning 0.0 lots. | `risk.small_account_mode` | `true` | Confirmed |
| **SA-03** | **Asymmetric Small Account R:R Filter:** In Small Account Mode, strictly reject any setup offering less than 1:3R (risk $1.00 to make $3.00–$5.00) to protect small accounts against drawdowns while enabling rapid doubling. | `strategy.small_account_min_rr` | `3.0` | Confirmed |
| **SA-04** | **Milestone Geometric Compounding Tiers:** Auto-scale lot sizing as account grows: 0.01 lot for $10–$25, 0.02 lot for $26–$50, 0.03 lot for $51–$100, 0.05 lot for $101–$200. Automatically transitions to standard percentage risk above $500. | `risk.compounding_milestones` | `[[10, 0.01], [25, 0.01], [50, 0.02], [100, 0.03], [200, 0.05]]` | Confirmed |

---

### 1.15 Opening Range Gaps (`OG-`) (2024–2026 Models)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **OG-01** | **New Week Opening Gap (NWOG):** Gap formed between Friday 17:00 NY close and Sunday 18:00 NY open is retained as a permanent dynamic support/resistance grid throughout the active week. | 2024 Mentorship & NWOG Series | `strategy.gaps.track_nwog` | `true` | Confirmed |
| **OG-02** | **New Day Opening Gap (NDOG):** Price gap formed between the 16:59:59 NY close and the 18:00 NY daily reset serves as an intraday price magnet and liquidity target. | 2024 Mentorship & NDOG Series | `strategy.gaps.track_ndog` | `true` | Confirmed |
| **OG-03** | **09:30 AM Opening Range Gap (ORG):** Cash equity open gap between 09:29:59 and 09:30:00 NY is monitored for rapid repricing and liquidity runs. | 2023/2024 Opening Range Macro | `strategy.gaps.track_org` | `true` | Confirmed |
| **OG-04** | **Gap Consequent Encroachment (50% Balance Point):** The exact 50% midpoint of NWOG, NDOG, and ORG acts as primary institutional equilibrium; price often reacts to this level with high precision. | 2024/2025 Teachings | `strategy.gaps.consequent_encroachment` | `0.50 of gap range` | Confirmed |

---

### 1.16 Inversion FVGs & Balanced Price Ranges (`IV-`) (2023–2026 Models)

| ID | Rule Description | Source | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **IV-01** | **Inversion Fair Value Gap (IFVG):** When price completely violates and displaces through an existing Fair Value Gap without respecting it, that FVG flips polarity and acts as strong opposing support/resistance on the retest. | 2023/2024 Inversion Lectures | `strategy.enable_inversion_fvg` | `true` | Confirmed |
| **IV-02** | **Balanced Price Range (BPR):** When an aggressive impulse leg creates an FVG that is immediately retraced by an opposing FVG, the overlapping zone is a BPR; entries on retests of this zone offer high-speed continuation. | 2023/2024 Price Action Models | `strategy.enable_bpr` | `true` | Confirmed |

---

### 1.17 Universal Multi-Market & Adaptive Order Routing (`UM-`)

| ID | Rule Description | Purpose / Architectural Mechanism | Config Parameter | Default Value | Status |
|:---|:---|:---|:---|:---|:---:|
| **UM-01** | **Universal Cross-Asset Time & Price Engine:** The underlying state machine executes uniformly across Forex, Commodities (Gold/Silver), and Index Futures, adjusting only symbol specifications (pip size, point value, spread, and active killzones). | `strategy.asset_class` | `forex / commodity / index` | Confirmed |
| **UM-02** | **Adaptive Order Execution (Limit vs. Market):** Places resting limit orders at FVG boundaries during clean retracements; switches dynamically to real-time market execution when micro 3-candle confirmation occurs or price rapidly accelerates. | `execution.adaptive_routing` | `true (limit with market fallback)` | Confirmed |
| **UM-03** | **Close Proximity Market Fill Protection:** If a limit order at an imbalance is missed by 1 tick or 0.5 pips and displacement resumes, execute a market order within the permitted slippage tolerance. | `execution.close_proximity_tolerance_pips` | `0.5 pips (Forex) / 1.0 pt (Gold/ES)` | Confirmed |

---

## 2. Cross-Asset Specifications Matrix

How ICT 2022 Mentorship parameters adapt across **Gold (XAUUSD)**, **Forex (GBPUSD)**, and **Equity Index Futures (ES/NQ)**:

| Parameter | Gold (`XAUUSD`) | Forex (`GBPUSD`) | Equity Index Futures (`ES` / `NQ`) |
|:---|:---|:---|:---|
| **Primary Morning Killzone** | `08:30 – 11:00 NY` | `07:00 – 10:00 NY` (London: `02:00–05:00`) | `08:30 – 11:00 NY` |
| **Afternoon PM Killzone** | `13:30 – 16:00 NY` | Not recommended (low volume) | `13:30 – 16:00 NY` |
| **Minimum Sweep Buffer** | `1.50 handles ($1.50)` | `0.5 pips (5 points)` | `0.75 pts (ES) / 3.0 pts (NQ)` |
| **Minimum Stop Loss** | `10.0 handles` | `4.0 pips` | `4.0 pts (ES) / 12.0 pts (NQ)` |
| **Maximum Stop Loss** | `60.0 handles` | `25.0 pips` | `20.0 pts (ES) / 60.0 pts (NQ)` |
| **Base Stop Buffer** | `1.50 handles` | `1.0 pip` | `1.0 pt (ES) / 2.0 pts (NQ)` |
| **Low-Hanging Fruit TP** | `20.0 to 30.0 handles` | `15.0 to 20.0 pips` | `5.0 pts (ES) / 20.0 pts (NQ)` |
| **Point Multiplier** | `100.0 (1 lot = $100/pt)` | `100,000 (1 lot = $10/pip)` | `$50/pt (ES) / $5/pt (MES)` |
| **SMT Correlation Pair** | Silver (`XAGUSD`) or DXY | `EURUSD` or `DXY` (inverse) | `ES` vs `NQ` vs `YM` |
| **Execution Timeframe** | `5m / 1m` | `5m / 1m` | `5m / 2m / 1m` |

---

## 3. Ambiguities & Trader Decisions Checklist

The following 10 architectural items represent places where Michael Huddleston taught nuanced or discretionary concepts, or where two valid implementation options exist. Review these options before Phase 2 implementation:

### Decision 1: Market Structure Shift (MSS) Trigger
- **Option A (Recommended):** Candle body **close** beyond the swing extreme on the execution timeframe (more conservative, eliminates wick fakeouts).
- **Option B:** Candle **wick** penetration beyond the swing extreme (more aggressive, captures faster entries).

### Decision 2: Fair Value Gap Entry Price
- **Option A (Recommended):** Limit order at the **near boundary** of the FVG (maximizes fill probability).
- **Option B:** Limit order at the **Consequent Encroachment (50% midpoint)** of the FVG (tighter stop, higher R:R, but risks missing shallow fills).

### Decision 3: FVG Confirmation Requirement
- **Option A (Recommended):** Direct limit order entry upon price tapping the FVG.
- **Option B (Ep 31 Rule):** Require a confirming **3-candle swing pattern** to form inside/tapping the FVG before entering (conservative).

### Decision 4: Stop Loss Placement Anchor
- **Option A (Recommended):** Beyond the **sweep extreme swing high/low** plus a buffer (strict ICT invalidation).
- **Option B (Ep 02 / Ep 40 Rule):** Beyond **Candle 1 of the FVG formation** (tighter stop when sweep extreme is far).

### Decision 5: Stop Loss Trimming & Breakeven Rule
- **Option A (Recommended - Ep 41):** Trim stop loss risk distance by 25% when price reaches 50% of the target distance; move to Breakeven when price reaches 75% of target distance.
- **Option B:** Move stop directly to Breakeven upon taking the first 50% partial profit at TP1.

### Decision 6: Partial Scaling Allocation
- **Option A (Recommended):** Close 50% of position at TP1 (first liquidity pool / 5 pts ES / 15 pips Forex), leave 50% runner to final target.
- **Option B (Ep 40 London Close):** Close 80% of position during the 10:00–11:00 NY London close window, leave 20% runner.

### Decision 7: Order of Liquidity Purging Filter (Ep 25)
- **Option A (Recommended):** Strict filter enabled. For shorts, price must take BSL first; if SSL was taken earlier in the session, the short setup is cancelled.
- **Option B:** Permissive. Price may take SSL first if higher timeframe bias is strongly bearish.

### Decision 8: Close Proximity Entry Tolerance (Ep 29)
- **Option A (Recommended):** Strict limit order only. If price misses the FVG boundary by even 0.1 pip/tick, do not enter.
- **Option B:** Close proximity market entry allowed if price comes within 1.0 pip (Forex) / 1.0 pt (ES) of the FVG and starts displacing.

### Decision 9: NFP Week Trading Policy (Ep 36 & 37)
- **Option A (Recommended):** Strict ICT rule: Cease all trading for the week by Wednesday 12:00 NY; completely flat Thursday and Friday.
- **Option B:** Trade Thursday morning normally, blackout only Friday NFP release.

### Decision 10: Dynamic Risk Reduction on Consecutive Losses (Ep 41)
- **Option A (Recommended):** Full Ep 41 schedule: 1.0% base -> 0.5% after 1 loss -> 0.25% after 2 losses. Recover to 1.0% once 50% of lost equity is made back.
- **Option B:** Fixed prop-firm sizing: Flat 0.5% risk on all trades with hard daily 2% and weekly 4% loss cutoffs.
