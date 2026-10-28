# ICT Time-and-Price trading system

A transparent, rules-based implementation of the proposal's single strategy:

1. **Killzone**: look for setups only inside fixed New York-time windows.
2. **Time and Price**: inside the window, wait for price to sweep a reference level
   (prior-day or Asia-range high/low), then close back inside it. Enter on the next bar.
3. **Fundamentals filter**: no entries around high-impact news, and flatten before it.
4. **Hard risk limits**: fixed % risk per trade, daily/weekly loss floors, a
   consecutive-loss halt and trade-count caps. Nothing can override them.

Deterministic, no machine learning: every signal carries the rule IDs that produced it
([RULES.md](RULES.md)). The backtester and the live runner call the *same* strategy and
risk code, so what you validate is exactly what trades.

The core is pure Python 3.11+ standard library. Live trading works with **MetaTrader 5**
(optional `MetaTrader5` package) or **MetaTrader 4** (the included `ICTBridge` EA).

## Quick start

```bash
python -m unittest discover -s tests -t .          # test suite
python -m ict_trader demo --report demo.html       # whole pipeline on synthetic data
```

`demo` uses a random walk that has no edge by construction, so it **should** lose a
little to costs. If a configuration looks profitable on it, that configuration is overfit.

## Validation pipeline (proposal §3)

Export M5 history from MT5 (or any source) to CSV with `time,open,high,low,close[,volume]`
columns, and an economic calendar to CSV (see `examples/calendar.example.csv`).

```bash
# 1. Backtest, with an HTML report showing every trade and the rule behind it
python -m ict_trader --config examples/config.example.toml backtest \
    --data data/EURUSD_M5.csv --tz UTC --news data/calendar.csv --report reports/eurusd.html

# 2. Walk-forward: tune on 6 months, test on the next unseen month, roll forward
python -m ict_trader --config examples/config.example.toml walkforward \
    --data data/EURUSD_M5.csv --news data/calendar.csv --grid examples/grid.example.json

# 3. Demo account, dry run (logs what it would do, sends nothing)
python -m ict_trader --config my.toml live --news data/calendar.csv

# 4. Demo account, sending orders
python -m ict_trader --config my.toml live --news data/calendar.csv --execute
```

Only the **out-of-sample** walk-forward numbers count. The report and CLI print a
warning unless there are at least 30 trades and mean R is more than about two
standard errors above zero.

> **Timezones matter.** MT5 CSV exports are in broker server time, often UTC+2/+3.
> Pass `--tz` (e.g. `--tz Europe/Athens`, or the IANA zone matching your broker) or
> every killzone will be shifted by hours.

## Going live (MT4 or MT5)

Both run on Windows next to the MetaTrader terminal, normally a Windows VPS so it
trades while your PC is off. Install Python 3.11+ there and copy this repository over.

### MetaTrader 5 (official Python API)

```powershell
pip install MetaTrader5
$env:MT5_LOGIN="..."; $env:MT5_PASSWORD="..."; $env:MT5_SERVER="..."
python -m ict_trader --config my.toml live --platform mt5 --news calendar.csv            # dry run
python -m ict_trader --config my.toml live --platform mt5 --news calendar.csv --execute  # trades
```

### MetaTrader 4 (ICTBridge Expert Advisor)

MT4 has no Python API, so a small EA (`mql4/ICTBridge.mq4`) publishes prices and
account data and executes the orders the engine sends. It makes no decisions itself.

1. In MT4: **File → Open Data Folder**, copy `ICTBridge.mq4` into `MQL4/Experts/`, then
   in MetaEditor open it and press **Compile**.
2. Open one chart of the traded symbol on the strategy timeframe (M5 by default),
   drag **ICTBridge** onto it, tick **Allow live trading**, and turn **AutoTrading** on.
   Keep `MagicNumber` equal to `live.magic` in your config.
3. Set `bridge_dir` in the `[live]` section of your config to the shared folder
   `C:\Users\<you>\AppData\Roaming\MetaQuotes\Terminal\Common\Files`.
4. Run:

```powershell
python -m ict_trader --config my.toml live --platform mt4 --news calendar.csv            # dry run
python -m ict_trader --config my.toml live --platform mt4 --news calendar.csv --execute  # trades
```

The engine refuses to start if the EA's heartbeat is stale, the chart timeframe is wrong,
or AutoTrading is off. If a broker rejects stops on market orders (common on ECN), the EA
opens the trade and attaches stops right after, and **closes it at once if the stop cannot
be attached**. It never leaves an unprotected position.

### Trading gold and GBPUSD together

Run one copy per instrument, each with its own config (`examples/xauusd.toml`,
`examples/gbpusd.toml`). They use different magic numbers and journals, so they never
touch each other's trades. On MT4, attach ICTBridge to one chart of each symbol, and set
each EA's `MagicNumber` to match its config.

```powershell
python -m ict_trader --config examples/xauusd.toml live --news calendar.csv --execute
python -m ict_trader --config examples/gbpusd.toml live --news calendar.csv --execute   # second window
```

Both read the same account equity, so the daily and weekly loss floors act on the whole
account: if the account drops 2% in a day, both stop. Risk per trade applies to each, so
with both in a trade at once you are risking 2 x `risk_per_trade_pct`. One `STOP` file in
the shared folder stops both. Check every value marked CHECK against your broker's symbol
specification. Gold in particular differs between brokers (symbol name, lot size, spread).

### Server time

Set `live.server_timezone` to your broker's server clock. The default `NY+7` (UTC+2 winter /
UTC+3 summer) fits most FX brokers. Check it against the time shown in Market Watch.

### Safeguards

- Dry run unless `--execute`; refuses a real-money account unless `--allow-real-account`.
- Refuses to start without a news calendar while the news filter is enabled.
- Historical bars only warm up levels. Signals older than `live.max_signal_age_seconds` are ignored.
- Reward:risk is re-checked at the live price before every order.
- Create a file named `STOP` (configurable) to flatten all positions and stop.
- Every decision, entry and exit is written to `journal.sqlite`.

The news calendar must be refreshed (e.g. weekly) from your calendar provider.

## Web app

`index.html` (deployed to Vercel) and `web/index.html` (Netlify) are a static trading desk:
live New York killzone clock, sample setups, position-size calculator, pre-trade checklist
and the full rule playbook. They are generated from `web/template.html` and `RULES.md`, so
after editing either, rebuild with:

```bash
python scripts/build_web.py
```

### Live signals and alerts

`api/scan.py` is a Vercel serverless function. On each call it downloads recent 5-minute
bars (Yahoo Finance: GC, ES and NQ futures, and GBPUSD/EURUSD quotes), replays them through
the same strategy and backtester, and returns today's signals with outcomes, the decision
log and a track record (`ict_trader/scanner.py`). The site's Signals tab reads it.

`/api/scan?notify=1` also pushes new signals and trade results to the ntfy topic
`ictflux-signals-x7q4m2` (override with the `NTFY_TOPIC` env var) and to Telegram if
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set. ntfy's message history is used to
avoid duplicates, so the endpoint can be called as often as you like.
**Data feeds:** by default the scanner reads real-time 5-minute candles for ~60 markets
(forex majors, crosses and exotics, metals, global indices, crypto) from Deriv's public
public WebSocket (`wss://api.derivws.com/trading/v1/options/ws/public`): no account, app id
or token needed, available in Nigeria. The legacy endpoint is a fallback
(`DERIV_LEGACY_APP_ID`, default 1089). A registered Deriv app id is only needed later for
OAuth login and trading.
Markets Deriv doesn't list fall back to delayed Yahoo data. Alternatives: set
`OANDA_API_TOKEN` to use OANDA, or `DATA_SOURCE=yahoo` for the delayed 5 core markets only.
Markets without a hand-tuned config in `examples/` scale their thresholds to their own recent
5-minute range. `/api/history` serves the 30-day track record, cached for 30 minutes.
For alerts within a minute of each candle closing, have a free scheduler such as
cron-job.org call `/api/scan?notify=1` every minute.
`.github/workflows/scan.yml` is a slower fallback that calls it every 10 minutes in trading hours; set the
`SCAN_URL` repository variable to the production URL. Optional: set `CRON_SECRET` in
Vercel (and as a repo secret) so only the scheduler can trigger pushes.

**Timeframes:** `/api/scan?tf=1|2|3|5|15` and `/api/history?tf=…` run every market on that
execution timeframe. 5-minute uses the hand-tuned configs in `examples/`; other timeframes
scale each market's thresholds to its own range on that timeframe. Push alerts follow the
`tf` of the cron URL (default 5); add another cron with `&tf=1` for 1-minute alerts.

**Trader styles:** scalp (1/2/3m), intraday (5/15m), swing (1h: any hour, prior-day
levels, held until stop or target) and long-term (4h: prior-week levels, `level_period =
"week"`). `tf=60` and `tf=240` select swing and long-term in every API.

**Plans:** Free = signals, alerts, sessions, chart, calculator, track record. Pro =
plain-English "why this signal" lessons, replays, research lab, playbook, checklist and the
bot. Pro is a client-side preview until accounts and payments exist.

**Signal model:** the main live model is the full ICT 2022 model (`ict_trader/ict2022.py`):
killzone -> liquidity sweep -> displacement market-structure shift -> fair value gap in
premium/discount -> limit order in the gap -> stop beyond the sweep -> target at opposing
liquidity (min 1.5R). Pending limits are shown as staged orders. `SIGNAL_MODEL=sweep`
makes the original sweep-and-reclaim engine (Turtle Soup) the main model instead. Deriv
Volatility indices run the same price model with no time filter.

**Models and building blocks:** the scan runs every *trade model* side by side (the ICT 2022
model, Silver Bullet, OTE, Turtle Soup and the rest). A model is a complete trade recipe
whose trade the adviser's judgement matrix rules on: a score out of 100 and a call of
PULL THE TRIGGER, SIZE DOWN or STAND DOWN. The parts a model is built from (direction,
filters, entry zones, targets, trade management, stops) are *building blocks*: the Research
lab and the custom builder use them, but they are not in the default scan, never alert and
never count as "a model agrees". See [docs/MODELS.md](docs/MODELS.md).

### Research lab

`/api/research?symbol=R_75&tf=5&mode=ict` backtests the engine on months of real Deriv
candles for any symbol and execution timeframe (1, 2, 3, 5 or 15 minutes), in two time
modes: `ict` (killzones) and `allday` (price rules at any hour). It reports setups per day,
win rate, expectancy, drawdown and whether the edge is distinguishable from luck
(`ict_trader/research.py`). The site's Research lab page runs a grid of these. `&model=`
takes a trade model, a single building block (to see what it adds to the ICT 2022 model) or
a `custom:entry=...;stop=...;target=...;filter=...;mgmt=...` build; see
[docs/MODELS.md](docs/MODELS.md).

## Layout

| Path | Purpose |
|------|---------|
| `ict_trader/config.py` | All tunable rules (TOML-loadable) |
| `ict_trader/sessions.py` | NY session clock, DST-safe killzones, look-ahead-free reference levels |
| `ict_trader/strategy.py` | Sweep-and-reverse state machine with an audit log (the Turtle Soup model) |
| `ict_trader/models.py` | The model registry: which names are trade models and which are building blocks, and how each is built |
| `ict_trader/advisor.py` | The judgement matrix: scores a trade out of 100 and says PULL THE TRIGGER, SIZE DOWN or STAND DOWN (see `docs/MODELS.md`) |
| `ict_trader/news.py` | Economic-calendar blackout filter |
| `ict_trader/risk.py` | Hard limits and lot sizing |
| `ict_trader/backtest.py` | Conservative bar-by-bar simulator (spread, commission, stop-first) |
| `ict_trader/walkforward.py` | Rolling out-of-sample validation |
| `ict_trader/report.py` | HTML performance dashboard |
| `ict_trader/live.py` | Live/demo runner shared by both platforms |
| `ict_trader/broker/mt5.py` | MetaTrader 5 adapter |
| `ict_trader/broker/mt4.py`, `mql4/ICTBridge.mq4` | MetaTrader 4 file bridge and its Expert Advisor |

## Not yet built

- **Rule extraction from the trader's YouTube content** (proposal §3, step 1). Defaults
  in `RULES.md` are generic ICT conventions until confirmed with the trader.
- Comparing the engine against the trader's own trade journal.
- Live monitoring dashboard over `journal.sqlite`. Backtests already produce an HTML report.
- Additional confirmation types (market-structure shift, FVG) if the trader uses them.

## Expectations

No system can guarantee profit, and most retail FX/CFD accounts lose money. What this
code guarantees is that the rules are explicit, the tests are honest, and nothing reaches
live capital without passing walk-forward and demo stages first.
