# For any AI tool or contributor working in this repository

Read `docs/ENGINE.md`, section **Changing the engine (read this first)**, before touching `ict_trader/`.

Short version:

- The engine must be **selective**. `python -m unittest tests.test_noise_canary` must pass: on random prices the story models take (almost) no trades. If you loosen a rule and it fails, show a measured edge on real candles, out of sample, instead of raising the limit.
- Rules come from `rules/` (the extracted ICT episodes). Cite the episode and rule for every change. If ICT did not say it, it is a lab model, off by default.
- Nothing may re-tune rules at run time, and nothing may call a hand-weighted score a probability.
- Full test run: `python -m unittest discover -s tests -t .` (it must be green before you push). After editing `web/template.html` run `python scripts/build_web.py`.
- Never push to a branch whose pull request has been merged; start a new branch from the latest `main`.
- Bots stay on demo accounts. Never commit secrets.
