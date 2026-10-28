"""Adversarial review of the real-time entry path: no plan entered twice, no order armed from a stale scan, no money math
that quietly changes the plan, no bad plan that starves the others."""
import importlib.util
import inspect
import io
import json
import os
import random
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from cryptography.fernet import Fernet

from ict_trader import autotrade as at
from ict_trader import entryguard as eg

UTC = timezone.utc
NOW = datetime(2026, 10, 7, 14, 2, 30, tzinfo=UTC)      # a Wednesday, 10:02 in New York, 2.5 minutes after the 13:55... 14:00 close
SCAN = NOW - timedelta(seconds=80)                        # the scan that ran at 14:01:10, after the 14:00 close
DEMO = [{"id": "VRTC1", "type": "demo", "currency": "USD", "balance": 10000}]
PLAN = {"direction": "long", "entry": 100.0, "stop": 99.0, "target": 103.0, "tp1": 101.5}   # 1R = 1, 3R to the target


class ClockStore(at.MemoryStore):
    """A MemoryStore whose rows are stamped by the test's clock, not the real one."""

    def add_log(self, row):
        super().add_log({**row, "created_at": row.get("created_at") or NOW.isoformat()})


class Trader:
    def __init__(self, spot=100.0, balance=10000.0, open_n=0, fail=()):
        self._spot, self.bal, self.open_n, self.fail = spot, balance, open_n, set(fail)
        self.placed, self.currency, self.closed = [], "USD", False

    def balance(self):
        return self.bal

    def open_positions(self):
        return self.open_n

    def spot(self, sym):
        if isinstance(self._spot, Exception):
            raise self._spot
        return self._spot

    def place(self, s, risk, spot=None):
        if s["id"] in self.fail:
            raise RuntimeError("Deriv said no")
        self.placed.append((s["id"], round(risk, 2), spot))
        return {**at.sizing(s, risk, [10, 20, 50, 100], 1, spot), "contract_id": 7}

    def close(self):
        self.closed = True

    def open_contracts(self):
        return []


class NoSpotTrader(Trader):
    """An older trader: no spot(), and place() takes no spot."""
    spot = None

    def place(self, s, risk):
        self.placed.append((s["id"], round(risk, 2), None))
        return {**at.sizing(s, risk, [10, 20, 50, 100], 1), "contract_id": 8}


def fill(sid="EU-1", mss=111, verdict="TAKE", minutes_ago=2, **kw):
    return {"id": sid, "market": "EU", "label": "EUR/USD", "broker_symbol": "frxEURUSD", "direction": "long", "entry": 100.0, "stop": 99.0,
            "target": 103.0, "rr": 3.0, "quality": {"grade": "A"}, "advice": {"verdict": verdict, "score": 80},
            "time": (NOW - timedelta(minutes=minutes_ago)).isoformat(), "timeframe_minutes": 5, "outcome": {"status": "open"},
            "setup": {"tp1": None, "mss_time": mss}, **kw}


def order(placed=111, left=6, verdict="TAKE", **kw):
    return {"direction": "long", "entry": 100.0, "stop": 99.0, "tp1": None, "tp2": 103.0, "rr": 3.0, "placed": placed, "candles_left": left,
            "quality": {"grade": "A"}, "advice": {"verdict": verdict, "score": 80}, **kw}


def report(signals=(), orders=(), key="EU", generated=SCAN, stale=0, **market):
    return {"generated_at": generated.isoformat(), "timeframe_minutes": 5,
            "markets": [{"ok": True, "key": key, "label": "EUR/USD", "cls": "forex", "broker_symbol": "frxEURUSD", "model": "ict2022",
                         "timeframe_minutes": 5, "stale_minutes": stale, "today": {"signals": list(signals)},
                         "models": {"ict2022": {"orders": list(orders), "signals": []}}, **market}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AUTOTRADE_KEY": Fernet.generate_key().decode()})
        self.env.start()
        self.store = ClockStore()
        self.uid = self.enroll()

    def tearDown(self):
        self.env.stop()

    def enroll(self, store=None, **kw):
        body = {"token": "tok-123456789", "account_id": "VRTC1", "accept_terms": True, "terms_version": at.TERMS_VERSION, "classes": ["forex"], **kw}
        return at.enroll(store or self.store, body, accounts=lambda t: DEMO, now=NOW)["id"]

    def go(self, rep, t=None, only_armed=False, store=None, **kw):
        t = t or Trader()
        out = at.run(store or self.store, rep, trader=lambda u, tok: t, now=NOW, only_armed=only_armed, **kw)
        return out, t

    def rows(self, kind=None):
        return [x for x in self.store.log if kind is None or x["kind"] == kind]


# ------------------------------------------------------------------------------------------------ 0. the class itself
class TraderClassTest(unittest.TestCase):
    def test_there_is_one_deriv_trader_and_it_reads_prices_from_the_public_feed(self):
        src = inspect.getsource(at)
        self.assertEqual(src.count("\nclass DerivTrader"), 1)          # a stub copy used to shadow the real one (or the other way round)
        self.assertNotIn("ticks_history\": 1", src)                    # the symbol is the value of ticks_history, never 1
        t = object.__new__(at.DerivTrader)
        t.ws = mock.Mock()
        with mock.patch.object(at.entryguard, "PublicFeed") as feed:
            feed.return_value.price.return_value = 1.2345
            self.assertEqual(t.spot("frxEURUSD"), 1.2345)
            feed.return_value.price.assert_called_once_with("frxEURUSD")
            t.close()
            feed.return_value.close.assert_called_once()
        self.assertTrue(t.ws.close.called)

    def test_place_sends_the_stop_and_target_levels_measured_from_the_live_price(self):
        sent = []

        class WS:
            def send(self, data):
                self.req = json.loads(data)
                sent.append(self.req)

            def recv(self):
                r, rid = self.req, self.req["req_id"]
                if "contracts_for" in r:
                    return json.dumps({"req_id": rid, "contracts_for": {"available": [{"contract_type": "MULTUP", "multiplier_range": [100, 200, 500, 1000], "min_stake": 1}]}})
                if "proposal" in r:
                    return json.dumps({"req_id": rid, "proposal": {"id": "P1"}})
                return json.dumps({"req_id": rid, "buy": {"contract_id": 55, "buy_price": r["price"]}})
        with mock.patch.object(at, "_http", return_value={"data": {"url": "wss://x"}}):
            t = at.DerivTrader("tok", "VRTC1", "demo", connect=lambda u: WS())
        sig = {"label": "EUR/USD", "broker_symbol": "frxEURUSD", "direction": "long", "entry": 1.1, "stop": 1.099, "target": 1.103}
        r = t.place(sig, 100.0, spot=1.1005)
        prop = next(x for x in sent if "proposal" in x)
        self.assertEqual(prop["limit_order"], {"stop_loss": 100.0, "take_profit": r["take_profit"]})
        self.assertAlmostEqual(r["take_profit"], 100 * (1.103 - 1.1005) / (1.1005 - 1.099), places=1)    # the target LEVEL, 1.67R from here
        self.assertEqual(r["multiplier"], 500.0)
        self.assertEqual(next(x for x in sent if "buy" in x)["price"], r["stake"])
        with self.assertRaises(RuntimeError):                      # a direction that is neither never becomes a short by accident
            t.place({**sig, "direction": "Long"}, 100.0, spot=1.1005)


# ------------------------------------------------------------------------------------------------ 1. double entry
class DoubleEntryTest(Base):
    def test_a_fill_and_its_resting_limit_in_one_report_are_one_trade(self):
        out, t = self.go(report(signals=[fill(mss=111)], orders=[order(placed=111)]))
        self.assertEqual((out["placed"], [p[0] for p in t.placed]), (1, ["EU-1"]))

    def test_the_same_order_listed_twice_is_entered_once(self):
        out, t = self.go(report(orders=[order(), order()]), Trader(99.95), only_armed=True)
        self.assertEqual((out["placed"], len(t.placed)), (1, 1))

    def test_two_runs_that_both_read_the_log_before_either_wrote_still_enter_once(self):
        class Racy(ClockStore):
            def logged_signal(self, user_id, signal_id):   # both runs looked, neither had written yet
                return False
        store = Racy()
        self.enroll(store)
        rep = report(orders=[order()])
        out1, t1 = self.go(rep, Trader(99.95), only_armed=True, store=store)
        out2, t2 = self.go(rep, Trader(99.95), only_armed=True, store=store)
        self.assertEqual((len(t1.placed), len(t2.placed)), (1, 0))
        self.assertEqual(out2["placed"], 0)

    def test_two_runs_that_claim_at_the_same_instant_both_stand_down(self):
        class Rival(ClockStore):
            def add_log(self, row):
                super().add_log(row)
                if row["kind"] == "claimed" and not getattr(self, "rival", False):
                    self.rival = True
                    super().add_log({**row, "message": "the other run's claim"})
        store = Rival()
        self.enroll(store)
        out, t = self.go(report(orders=[order()]), Trader(99.95), only_armed=True, store=store)
        self.assertEqual(t.placed, [])                             # a missed trade, never a double one
        out, t = self.go(report(orders=[order()]), Trader(99.95), only_armed=True, store=store)
        self.assertEqual(t.placed, [])                             # and it is not retried by the next run

    def test_a_run_that_dies_after_placing_and_before_logging_does_not_let_the_next_run_enter_again(self):
        class Dies(ClockStore):
            dead = True

            def add_log(self, row):
                if row["kind"] == "placed" and self.dead:
                    raise OSError("database went away")
                super().add_log(row)
        store = Dies()
        self.enroll(store)
        rep = report(signals=[fill()])
        out, t = self.go(rep, store=store)                          # the order went to Deriv, the log row did not make it
        self.assertEqual(len(t.placed), 1)
        store.dead = False
        out, t2 = self.go(rep, store=store)
        self.assertEqual(t2.placed, [])
        out, t3 = self.go(report(orders=[order()]), Trader(99.95), only_armed=True, store=store)   # nor as the resting limit it came from
        self.assertEqual(t3.placed, [])

    def test_a_fill_entered_first_blocks_its_resting_limit_in_a_later_snapshot_too(self):
        self.go(report(signals=[fill(mss=111)]))
        out, t = self.go(report(orders=[order(placed=111)]), Trader(99.95), only_armed=True)
        self.assertEqual(t.placed, [])

    def test_claims_are_bookkeeping_not_activity(self):
        self.go(report(signals=[fill()]))
        self.assertTrue(any(x["kind"] == "claimed" for x in self.store.log))
        self.assertTrue(all(x["kind"] != "claimed" for x in self.store.logs(self.uid)))      # the page's activity list never shows them
        self.assertTrue(self.store.logged_signal(self.uid, "armed:EU:111"))                  # but they count as logged
        self.assertEqual(self.store.count_claims(self.uid, "armed:EU:111"), 1)

    def test_with_a_unique_index_the_second_claim_is_refused_by_the_database_and_exactly_one_wins(self):
        class Unique(ClockStore):
            def add_log(self, row):
                if row["kind"] == "claimed" and any(x["kind"] == "claimed" and x["signal_id"] == row["signal_id"] for x in self.log):
                    raise RuntimeError('Database error 409: 23505 duplicate key value violates unique constraint "autotrade_log_claim".')
                super().add_log(row)

            def logged_signal(self, user_id, signal_id):             # both runs read before either wrote
                return False
        store = Unique()
        self.enroll(store)
        rep = report(orders=[order()])
        out1, t1 = self.go(rep, Trader(99.95), only_armed=True, store=store)
        out2, t2 = self.go(rep, Trader(99.95), only_armed=True, store=store)
        self.assertEqual((len(t1.placed), len(t2.placed), out2["errors"]), (1, 0, 0))      # a lost race is a skip, not an error

    def test_a_store_that_cannot_write_the_claim_means_no_trade(self):
        class NoClaim(ClockStore):
            def add_log(self, row):
                if row["kind"] == "claimed":
                    raise OSError("write failed")
                super().add_log(row)
        store = NoClaim()
        self.enroll(store)
        out, t = self.go(report(signals=[fill()]), store=store)
        self.assertEqual((t.placed, out["placed"]), ([], 0))
        self.assertTrue(t.closed)


# ------------------------------------------------------------------------------------------------ 2. stale orders
class StaleOrderTest(Base):
    def test_the_rule_is_a_scan_that_has_seen_the_latest_candle_close(self):
        rep = report(orders=[order()], generated=datetime(2026, 10, 7, 13, 56, 20, tzinfo=UTC))
        just_after_close = datetime(2026, 10, 7, 14, 0, 40, tzinfo=UTC)
        self.assertEqual(eg.armed_orders(rep, just_after_close), [])                      # the 14:00 close is not in that scan yet
        self.assertEqual(len(eg.armed_orders(rep, datetime(2026, 10, 7, 13, 59, 59, tzinfo=UTC))), 1)   # still before it: fine
        fresh = report(orders=[order()], generated=datetime(2026, 10, 7, 14, 1, 5, tzinfo=UTC))
        self.assertEqual(len(eg.armed_orders(fresh, just_after_close + timedelta(minutes=2))), 1)
        self.assertEqual(eg.armed_orders(fresh, datetime(2026, 10, 7, 14, 5, 40, tzinfo=UTC)), [])      # and stale again after the 14:05 close

    def test_a_close_is_counted_only_after_its_instant(self):
        self.assertEqual(eg.last_close_before(datetime(2026, 10, 7, 14, 0, 0, tzinfo=UTC), 5), datetime(2026, 10, 7, 13, 55, tzinfo=UTC))
        self.assertEqual(eg.last_close_before(datetime(2026, 10, 7, 14, 0, 1, tzinfo=UTC), 5), datetime(2026, 10, 7, 14, 0, tzinfo=UTC))
        self.assertEqual(eg.last_close_before(datetime(2026, 10, 7, 14, 59, 59, tzinfo=UTC), 15), datetime(2026, 10, 7, 14, 45, tzinfo=UTC))

    def test_a_market_whose_data_lags_a_candle_behind_the_scan_is_not_armed(self):
        self.assertEqual(len(eg.armed_orders(report(orders=[order()], stale=1), NOW)), 1)
        self.assertEqual(eg.armed_orders(report(orders=[order()], stale=6), NOW), [])        # its last candle was a whole candle old

    def test_a_stale_snapshot_enters_nothing_and_opens_no_connection(self):
        rep = report(orders=[order()], generated=datetime(2026, 10, 7, 13, 56, 20, tzinfo=UTC))
        calls = []
        out = at.run(self.store, rep, trader=lambda u, tok: calls.append(1) or Trader(99.9), now=NOW, only_armed=True, prices=lambda s: 99.9)
        self.assertEqual((calls, out["placed"], len(self.store.log)), ([], 0, 1))           # only the enrollment row

    def test_bad_timestamps_never_raise(self):
        for g in ("garbage", None, "2026-10-07T14:01:10", "2026-10-07T14:01:10Z"):
            rep = report(orders=[order()])
            rep["generated_at"] = g
            eg.armed_orders(rep, NOW)
        naive = report(orders=[order()])
        naive["generated_at"] = "2026-10-07T14:01:10"
        self.assertEqual(len(eg.armed_orders(naive, NOW)), 1)
        self.assertEqual(eg.armed_orders(naive, datetime(2026, 10, 7, 14, 2, 30)), eg.armed_orders(naive, NOW))   # a naive "now" is UTC too

    def test_orders_without_an_id_or_with_broken_fields_are_dropped_and_do_not_hide_the_others(self):
        rep = report(orders=[order(placed=None), order(placed=1, entry="abc"), order(placed=2, entry=float("nan")), order(placed=3, direction="buy"),
                             {"direction": "long"}, "junk", None, order(placed=4)])
        rep["markets"][1:1] = [None, "junk", {"ok": True, "broker_symbol": "x", "models": ["not a dict"]},
                               {"ok": True, "broker_symbol": "y", "label": "Y", "models": {"ict2022": {"orders": {"a": 1}}}}]
        self.assertEqual([p["id"] for p in eg.armed_orders(rep, NOW)], ["armed:EU:4"])

    def test_the_orders_of_the_main_model_only_and_their_strictness(self):
        plans = eg.armed_orders(report(orders=[order()], key="EURUSD"), NOW)
        self.assertTrue(plans[0]["strict"])                       # Wednesday 10:02 New York, A grade, 3R on a market ICT trades
        self.assertFalse(eg.armed_orders(report(orders=[order()], key="EU"), NOW)[0]["strict"])


# ------------------------------------------------------------------------------------------------ 3. money math
class SizingTest(unittest.TestCase):
    M = [10, 20, 50, 100, 200, 500, 1000]

    def test_target_and_stop_are_levels_from_the_live_price(self):
        long = {"direction": "long", "entry": 1.1, "stop": 1.099, "target": 1.103}
        p = at.sizing(long, 100.0, self.M, 1, spot=1.1005)
        self.assertEqual(p["stop_loss"], 100.0)
        self.assertAlmostEqual(p["stop_loss"] * (1.103 - 1.1005) / (1.1005 - 1.099), p["take_profit"], delta=0.01)
        loss_at_stop = p["stake"] * p["multiplier"] * (1.1005 - 1.099) / 1.1005
        self.assertAlmostEqual(loss_at_stop, 100.0, delta=0.5)
        short = {"direction": "short", "entry": 1.1, "stop": 1.101, "target": 1.097}
        q = at.sizing(short, 100.0, self.M, 1, spot=1.0995)
        self.assertAlmostEqual(q["take_profit"], 100 * (1.0995 - 1.097) / (1.101 - 1.0995), delta=0.02)

    def test_a_minimum_stake_lowers_the_multiplier_so_the_stop_stays_where_the_plan_put_it(self):
        sig = {"direction": "long", "entry": 1.1, "stop": 1.099, "target": 1.103}
        p = at.sizing(sig, 0.5, [100, 200, 300, 500, 1000], 1)         # $0.50 of risk, $1 minimum stake
        self.assertEqual((p["multiplier"], p["stop_loss"]), (500.0, 0.5))
        self.assertAlmostEqual(p["stake"] * p["multiplier"] * 0.001 / 1.1, 0.5, delta=0.01)    # the loss at the plan's stop is the risk, no more
        self.assertAlmostEqual(p["stop_reach"], 1.0, places=2)

    def test_a_trade_the_minimum_stake_would_distort_is_refused_not_entered_with_a_different_stop(self):
        sig = {"direction": "long", "entry": 100.0, "stop": 99.0, "target": 103.0}
        with self.assertRaises(RuntimeError) as cm:                  # $0.50 on a 1% stop at x100 minimum: the stop-loss would fire at half the distance
            at.sizing(sig, 0.5, [100, 200], 1)
        self.assertIn("refused", str(cm.exception))
        wide = {"direction": "long", "entry": 100.0, "stop": 96.0, "target": 112.0}     # a 4% stop, but the smallest multiplier is x50: stopped at 50% of it
        with self.assertRaises(RuntimeError):
            at.sizing(wide, 100.0, [50, 100], 1)
        with mock.patch.dict(os.environ, {"AUTOTRADE_MIN_STOP_FRACTION": "0.4"}):   # the owner may accept a tighter stop knowingly
            self.assertEqual(at.sizing(wide, 100.0, [50, 100], 1)["multiplier"], 50.0)

    def test_the_contract_never_risks_more_than_intended(self):
        rng = random.Random(7)
        for _ in range(3000):
            entry = rng.uniform(0.5, 5000)
            dist = entry * rng.uniform(0.0002, 0.06)
            risk = round(rng.uniform(0.1, 500), 2)
            sig = {"direction": "long", "entry": entry, "stop": entry - dist, "target": entry + dist * rng.uniform(1.5, 8)}
            try:
                p = at.sizing(sig, risk, self.M, rng.choice([0.35, 1, 5]), spot=entry + dist * rng.uniform(-0.7, 0.2))
            except RuntimeError:
                continue                                              # refused: nothing was entered
            self.assertLessEqual(p["stop_loss"], risk + 0.005)        # never more than the intended risk
            self.assertLessEqual(p["stop_loss"], p["stake"] + 0.005)  # Deriv: the stop-loss cannot exceed the stake
            self.assertGreaterEqual(p["stop_reach"], 0.89)            # and the stop sits (about) where the plan's does
            self.assertGreater(p["take_profit"], 0)

    def test_distances_prices_and_numbers_that_cannot_be_traded_are_refused(self):
        ok = {"direction": "long", "entry": 100.0, "stop": 99.0, "target": 103.0}
        bad = [({**ok, "stop": 100.0}, None), ({**ok, "stop": 101.0}, None),                # no distance; stop above a long's entry
               (ok, 98.9), (ok, 103.0), (ok, 104.0),                                         # spot through the stop; at and past the target
               ({**ok, "target": 99.5}, None),                                               # target behind the entry
               ({**ok, "stop": float("nan")}, None), ({**ok, "target": float("inf")}, None), ({**ok, "stop": "abc"}, None),
               ({**ok, "entry": None}, None), ({**ok, "direction": "Long"}, None), ({**ok, "direction": "buy"}, None),
               (ok, float("nan")), (ok, -5.0)]
        for sig, spot in bad:
            with self.subTest(sig=sig, spot=spot), self.assertRaises(RuntimeError):
                at.sizing(sig, 100.0, self.M, 1, spot=spot)
        for risk in (0, -1, float("nan"), None, 0.001):
            with self.subTest(risk=risk), self.assertRaises(RuntimeError):
                at.sizing(ok, risk, self.M, 1)
        with self.assertRaises(RuntimeError):
            at.sizing(ok, 100.0, [], 1)
        with self.assertRaises(RuntimeError):
            at.sizing(ok, 100.0, [0, float("nan")], 1)
        short_wrong = {"direction": "short", "entry": 100.0, "stop": 101.0, "target": 97.0}
        with self.assertRaises(RuntimeError):
            at.sizing(short_wrong, 100.0, self.M, 1, spot=101.5)     # a spot above a short's stop
        self.assertEqual(at.sizing({"entry": 100.0, "stop": 99.0, "target": 103.0}, 100.0, self.M, 1)["stop_loss"], 100.0)   # no direction: as before

    def test_a_string_price_from_json_is_a_number(self):
        p = at.sizing({"direction": "long", "entry": "100", "stop": "99", "target": "103"}, 100.0, self.M, 1)
        self.assertEqual(p["take_profit"], 300.0)


# ------------------------------------------------------------------------------------------------ 4. check / touched
class GuardEdgeTest(unittest.TestCase):
    def test_equality_is_never_a_trade(self):
        self.assertIn("through the stop", eg.check(PLAN, 99.0).reason)
        self.assertIn("already at the target", eg.check({**PLAN, "tp1": None}, 103.0).reason)
        self.assertIn("first target", eg.check(PLAN, 101.5).reason)
        self.assertTrue(eg.touched(PLAN, 100.0))                  # a limit at exactly its price is reached

    def test_tp1_is_optional_and_must_make_sense(self):
        self.assertTrue(eg.check({**PLAN, "tp1": None}, 100.0).ok)
        behind_entry = {**PLAN, "tp1": 99.5}                      # a "first target" behind the entry is no target
        self.assertTrue(eg.check(behind_entry, 100.0).ok)
        beyond = {**PLAN, "tp1": 104.0}                           # ... nor one past the final target
        self.assertTrue(eg.check(beyond, 100.0).ok)
        self.assertIsNone(eg.first_target(beyond))
        self.assertIsNone(eg.first_target(behind_entry))
        self.assertEqual(eg.first_target(PLAN), 101.5)

    def test_the_first_target_of_a_fill_is_read_from_its_setup(self):
        f = {**PLAN, "tp1": None, "setup": {"tp1": 100.1}}        # a fill carries tp1 in setup, not at the top
        self.assertIn("first target", eg.check(f, 100.2, min_rr=0.1).reason)

    def test_a_tiny_stop_is_not_a_plan(self):
        self.assertIn("closer than a tick", eg.check({**PLAN, "stop": 99.9999999}, 100.0).reason)
        self.assertFalse(eg.check({**PLAN, "stop": 100.0}, 100.0).ok)

    def test_nothing_in_the_plan_or_the_price_can_raise(self):
        for bad in (float("nan"), float("inf"), -float("inf"), "abc", None, True, [], {}):
            for spot in (bad, 100.0):
                for field in ("entry", "stop", "target", "tp1"):
                    plan = {**PLAN, field: bad}
                    c = eg.check(plan, spot)
                    self.assertIsInstance(c.ok, bool)
                    eg.touched(plan, spot)
            self.assertFalse(eg.check(PLAN, bad).ok)
            self.assertFalse(eg.touched(PLAN, bad))
        for plan in ({}, {"direction": "long"}, {"direction": "long", "entry": 1}, None, "x", {"direction": "Long", "entry": 1, "stop": 0.5, "target": 3},
                     {"direction": "buy", "entry": 1, "stop": 0.5, "target": 3}):
            self.assertFalse(eg.check(plan, 1.0).ok)
        for plan in ({}, {"direction": "long"}, None, "x", {"direction": "Long", "entry": 1}, {"direction": "buy", "entry": 1}):
            self.assertFalse(eg.touched(plan, 1.0))
        self.assertFalse(eg.check(PLAN, 100.0, min_rr="x").ok is False)     # an unreadable minimum falls back to 1.5R
        self.assertFalse(eg.touched(PLAN, 0.0))                              # a price of zero is not a price

    def test_nan_used_to_pass_every_comparison_and_enter(self):
        self.assertFalse(eg.check(PLAN, float("nan")).ok)
        self.assertFalse(eg.check({**PLAN, "target": float("nan")}, 100.0).ok)
        self.assertFalse(eg.check({**PLAN, "stop": float("nan")}, 100.0).ok)

    def test_a_stop_or_target_on_the_wrong_side_of_the_entry_is_refused(self):
        self.assertIn("wrong side", eg.check({**PLAN, "stop": 101.0}, 100.0).reason)
        self.assertIn("wrong side", eg.check({**PLAN, "target": 99.5}, 100.0).reason)

    def test_the_verdict_gate_survives_a_malformed_adviser(self):
        for advice in (None, "TAKE", ["TAKE"], {}, {"verdict": None}):
            self.assertFalse(eg.verdict_ok({"advice": advice}))
        self.assertTrue(eg.verdict_ok({"advice": {"verdict": "TAKE"}}))
        self.assertFalse(eg.verdict_ok({"advice": {"verdict": "CAUTION"}}))
        self.assertTrue(eg.verdict_ok({"advice": {"verdict": "CAUTION"}}, "CAUTION"))


class FeedTest(unittest.TestCase):
    class WS:
        def __init__(self, reply):
            self.reply, self.sent, self.closed = reply, [], False

        def send(self, data):
            self.sent.append(json.loads(data))

        def recv(self):
            r = self.reply(self.sent[-1]) if callable(self.reply) else self.reply
            return json.dumps(r if "req_id" in r or not self.sent else {**r, "req_id": self.sent[-1]["req_id"]})

        def close(self):
            self.closed = True

    def feed(self, history, clock=1000.0, **kw):
        ws = self.WS({"history": history})
        return eg.PublicFeed(lambda u: ws, clock=lambda: clock, **kw), ws

    def test_a_stale_tick_is_not_a_live_price(self):
        f, ws = self.feed({"prices": [1.2], "times": [1000 - 600]})
        with self.assertRaises(RuntimeError) as cm:
            f.price("frxEURUSD")
        self.assertIn("old", str(cm.exception))
        self.assertFalse(ws.closed)                                # Deriv answered, so the connection stays for the next market
        f, _ = self.feed({"prices": [1.2], "times": [995]})
        self.assertEqual(f.price("frxEURUSD"), 1.2)
        f, _ = self.feed({"prices": [1.2]})                        # no timestamps: nothing to judge by
        self.assertEqual(f.price("x"), 1.2)

    def test_a_price_that_is_not_a_positive_number_is_refused(self):
        for p in (0, -1, "nan", "abc", None, float("inf")):
            f, _ = self.feed({"prices": [p]})
            with self.subTest(p=p), self.assertRaises(RuntimeError):
                f.price("x")

    def test_an_answer_that_never_comes_ends(self):
        ws = self.WS(lambda req: {"req_id": 999})
        f = eg.PublicFeed(lambda u: ws, timeout=0.05)
        with self.assertRaises(TimeoutError):
            f.price("x")
        self.assertTrue(ws.closed)


# ------------------------------------------------------------------------------------------------ 5. run()
class RunTest(Base):
    def test_one_bad_plan_does_not_starve_the_others(self):
        broken = fill("EU-0", mss=1, entry="abc")
        no_fields = {"id": "EU-9", "label": "X", "cls": "forex", "broker_symbol": "x", "direction": "long", "rr": 3, "advice": {"verdict": "TAKE"},
                     "quality": {"grade": "A"}, "time": (NOW - timedelta(minutes=1)).isoformat(), "outcome": {"status": "open"}}
        weird = fill("EU-8", mss=8, rr="abc", quality={"grade": None}, advice="TAKE")
        garbage = {"id": "G", "time": "nonsense", "broker_symbol": "x", "outcome": {"status": "open"}}
        rep = report(signals=[broken, no_fields, weird, garbage, fill("EU-1", mss=111)])
        rep["markets"].append(None)
        rep["markets"].append({"ok": True, "today": None})
        out, t = self.go(rep)
        self.assertEqual([p[0] for p in t.placed], ["EU-1"])
        self.assertEqual(out["placed"], 1)
        self.assertTrue(t.closed)
        self.assertTrue(any("not a number" in x["message"] for x in self.rows("skipped")))

    def test_an_order_the_broker_rejects_does_not_stop_the_next_one_and_the_connection_closes(self):
        out, t = self.go(report(signals=[fill("EU-1", mss=1), fill("EU-2", mss=2)]), Trader(fail=["EU-1"]))
        self.assertEqual([p[0] for p in t.placed], ["EU-2"])
        self.assertEqual((out["placed"], out["errors"]), (1, 1))
        self.assertTrue(t.closed)

    def test_a_plan_that_makes_the_trader_raise_unexpectedly_is_contained(self):
        class Boom(Trader):
            def place(self, s, risk, spot=None):
                if s["id"] == "EU-1":
                    raise ZeroDivisionError("bug")
                return super().place(s, risk, spot)
        out, t = self.go(report(signals=[fill("EU-1", mss=1), fill("EU-2", mss=2)]), Boom())
        self.assertEqual([p[0] for p in t.placed], ["EU-2"])
        out, t = self.go(report(signals=[fill("EU-1", mss=1), fill("EU-2", mss=2)]), Boom())   # and the failed one is not retried
        self.assertEqual(t.placed, [])

    def test_one_users_database_failure_does_not_starve_the_next_user(self):
        class Flaky(ClockStore):
            def logged_signal(self, user_id, signal_id):
                if user_id == self.first:
                    raise OSError("database hiccup")
                return super().logged_signal(user_id, signal_id)
        store = Flaky()
        a, b = self.enroll(store), self.enroll(store)
        store.first = a
        traders = {a: Trader(), b: Trader()}
        out = at.run(store, report(signals=[fill()]), trader=lambda u, tok: traders[u["id"]], now=NOW)
        self.assertEqual((len(traders[b].placed), out["errors"]), (1, 1))

    def test_the_daily_trade_limit_applies_to_resting_limits(self):
        store = ClockStore()
        self.enroll(store, max_trades_day=1)
        rep = report(orders=[order(placed=1), order(placed=2)])
        out, t = self.go(rep, Trader(99.95), only_armed=True, store=store)
        self.assertEqual((out["placed"], out["skipped"], len(t.placed)), (1, 1, 1))
        self.assertEqual(sum("Daily trade limit" in x["message"] for x in store.log), 1)
        out, t = self.go(rep, Trader(99.95), only_armed=True, store=store)               # next minute: nothing new, nothing logged again
        self.assertEqual((t.placed, out["placed"], out["skipped"]), ([], 0, 0))
        self.assertEqual(sum("Daily trade limit" in x["message"] for x in store.log), 1)

    def test_the_limit_counts_trades_even_when_the_log_is_full_of_other_rows(self):
        store = ClockStore()
        uid = self.enroll(store, max_trades_day=1)
        store.add_log({"user_id": uid, "kind": "placed", "message": "Buy EUR/USD TP · SL 100 / x", "signal_id": "EU-0", "contract_id": "1"})
        for i in range(450):                                                            # a day of "no price" lines, skips, errors
            store.add_log({"user_id": uid, "kind": "error", "message": f"noise {i}"})
        out, t = self.go(report(orders=[order()]), Trader(99.95), only_armed=True, store=store)
        self.assertEqual((t.placed, out["skipped"]), ([], 1))

    def test_max_open_applies_to_resting_limits_and_counts_both_legs(self):
        store = ClockStore()
        self.enroll(store, max_open=1)
        out, t = self.go(report(orders=[order()]), Trader(99.95, open_n=1), only_armed=True, store=store)
        self.assertEqual((t.placed, out["skipped"]), ([], 1))
        store2 = ClockStore()
        self.enroll(store2, max_open=2, max_trades_day=5)
        two_legs = order(placed=1, tp1=101.5, management={"partial": 0.5})
        rep = report(orders=[two_legs, order(placed=2, tp1=101.5, management={"partial": 0.5})])
        out, t = self.go(rep, Trader(99.95, open_n=0), only_armed=True, store=store2)
        self.assertEqual([p[0] for p in t.placed], ["armed:EU:1", "armed:EU:1"])         # 2 contracts of the first trade fill the 2 open: the second is not entered
        self.assertEqual(out["skipped"], 1)

    def test_the_daily_loss_pause_applies_to_resting_limits(self):
        self.go(report(), Trader(10000))                                                  # the day's first balance
        out, t = self.go(report(orders=[order()]), Trader(99.95, balance=9790), only_armed=True)
        self.assertEqual(t.placed, [])
        self.assertEqual(self.store.get_user(self.uid)["paused_reason"], "Daily loss limit reached")
        out, t = self.go(report(orders=[order(placed=2)]), Trader(99.95, balance=9790), only_armed=True)
        self.assertEqual(t.placed, [])
        # with the public feed the touch is known before connecting, so the skip is logged, once
        for _ in range(3):
            out, t = self.go(report(orders=[order(placed=3)]), Trader(balance=9790), only_armed=True, prices=lambda s: 99.95)
            self.assertEqual(t.placed, [])
        self.assertEqual(sum("Daily loss limit" in x["message"] and x["signal_id"] == "armed:EU:3" for x in self.store.log), 1)

    def test_a_loss_limit_reached_on_the_first_run_of_a_new_day_is_recorded(self):
        out, t = self.go(report(orders=[order()]), Trader(99.95, balance=10000), only_armed=True)   # opens the day (balance 10000) and enters
        self.assertEqual(len(t.placed), 1)
        u = self.store.get_user(self.uid)
        self.store.update_user(self.uid, {"day_start_balance": 10500})                     # the day began higher: now at -4.8%
        out, t = self.go(report(orders=[order(placed=2)]), Trader(99.95, balance=10000), only_armed=True)
        self.assertEqual(t.placed, [])
        self.assertEqual(u["day"], "2026-10-07")

    def test_a_guard_skip_is_logged_once_not_every_minute(self):
        rep = report(orders=[order()])
        for _ in range(4):
            self.go(rep, Trader(99.1), only_armed=True)                                   # touched, but 0.9R through the entry
        self.assertEqual(sum("failing" in x["message"] for x in self.store.log), 1)

    def test_a_last_look_at_the_price_before_the_order_goes_out(self):
        seen = iter([99.95, 100.6])                                # touched when decided; by the time the account is open, it has run away
        out, t = self.go(report(orders=[order()]), Trader(99.95), only_armed=True, prices=lambda s: next(seen))
        self.assertEqual((t.placed, out["skipped"]), ([], 1))
        self.assertTrue(any("not chasing" in x["message"] for x in self.store.log))
        seen = iter([99.95, 99.97])                                # still there: sized from the newest price
        out, t = self.go(report(orders=[order(placed=2)]), Trader(99.95), only_armed=True, prices=lambda s: next(seen))
        self.assertEqual([p[2] for p in t.placed], [99.97])

    def test_a_missing_price_does_not_poison_the_order_and_is_said_once(self):
        rep = report(orders=[order()])
        for _ in range(3):
            out, t = self.go(rep, Trader(RuntimeError("feed down")), only_armed=True)
            self.assertEqual(t.placed, [])
        self.assertEqual(sum("No live price" in x["message"] for x in self.store.log), 1)
        out, t = self.go(rep, Trader(99.95), only_armed=True)                              # the price is back: the order is still there
        self.assertEqual(len(t.placed), 1)

    def test_a_fill_is_not_entered_blind_when_its_price_cannot_be_read(self):
        out, t = self.go(report(signals=[fill()]), Trader(RuntimeError("feed down")))
        self.assertEqual((t.placed, out["placed"]), ([], 0))
        out, t = self.go(report(signals=[fill()]), Trader(100.0))                           # a fill is only skipped for a run, not poisoned
        self.assertEqual(len(t.placed), 1)

    def test_a_trader_with_no_spot_enters_fills_at_the_plan_as_before_and_never_arms(self):
        out, t = self.go(report(signals=[fill()], orders=[order(placed=5)]), NoSpotTrader())
        self.assertEqual([(p[0], p[2]) for p in t.placed], [("EU-1", None)])

    def test_no_connection_is_opened_unless_something_can_happen(self):
        calls = []

        def factory(u, tok):
            calls.append(1)
            return Trader(99.95)
        rep = report(orders=[order()])
        at.run(self.store, rep, trader=factory, now=NOW, only_armed=True, prices=lambda s: 100.4)     # not touched
        at.run(self.store, rep, trader=factory, now=NOW, only_armed=True, prices=lambda s: 100.4)
        self.assertEqual(calls, [])
        at.run(self.store, report(), trader=factory, now=NOW, only_armed=True, prices=lambda s: 99.95)  # nothing resting
        self.assertEqual(calls, [])
        at.run(self.store, rep, trader=factory, now=NOW, only_armed=True, prices=lambda s: 99.95)      # touched
        self.assertEqual(calls, [1])

    def test_with_nothing_resting_a_minute_run_does_not_even_read_the_database(self):
        class Untouchable(ClockStore):
            def enabled_users(self):
                raise AssertionError("the database was read for nothing")
        out = at.run(Untouchable(), report(), trader=lambda u, tok: Trader(), now=NOW, only_armed=True)
        self.assertEqual(out["users"], 0)

    def test_a_full_run_with_an_untouched_order_and_a_known_day_does_not_connect(self):
        self.store.update_user(self.uid, {"day": "2026-10-07"})
        calls = []
        at.run(self.store, report(orders=[order()]), trader=lambda u, tok: calls.append(1) or Trader(), now=NOW, prices=lambda s: 100.4)
        self.assertEqual(calls, [])

    def test_one_price_per_market_serves_every_user(self):
        for _ in range(2):
            self.enroll()
        asked = []
        traders = []

        def factory(u, tok):
            traders.append(Trader(99.95))
            return traders[-1]
        out = at.run(self.store, report(orders=[order()]), trader=factory, now=NOW, only_armed=True, prices=lambda s: asked.append(s) or 99.95)
        self.assertEqual(out["placed"], 3)
        self.assertEqual(len(asked), 1 + 3)        # one shared read to decide for all three users, then one last look before each order goes out

    def test_the_prices_come_from_the_default_public_feed_when_no_trader_is_given(self):
        feeds = []

        class Feed:
            def __init__(self):
                feeds.append(self)
                self.closed = False

            def price(self, sym):
                return 99.95

            def close(self):
                self.closed = True
        made = []
        with mock.patch.object(at.entryguard, "PublicFeed", Feed), mock.patch.object(at, "DerivTrader", side_effect=lambda *a, **k: made.append(Trader(99.95)) or made[-1]):
            out = at.run(self.store, report(orders=[order()]), now=NOW, only_armed=True)
        self.assertEqual((out["placed"], len(feeds), feeds[0].closed), (1, 1, True))

    def test_the_budget_stops_new_work_but_not_the_run(self):
        self.enroll()
        calls, clock = [], [0.0]

        class Slow(Trader):
            def place(self, s, risk, spot=None):
                clock[0] = 100.0                                         # entering the first user's trade used up the budget
                return super().place(s, risk, spot)
        with mock.patch.object(at.time, "monotonic", side_effect=lambda: clock[0]):
            out = at.run(self.store, report(orders=[order()]), trader=lambda u, tok: calls.append(1) or Slow(99.95), now=NOW, only_armed=True,
                         prices=lambda s: 99.95, budget_s=15)
        self.assertEqual(calls, [1])                                     # the first user is served, the second is left for the next run
        self.assertEqual(out["deferred"], 1)

    def test_only_a_pull_the_trigger_verdict_is_armed(self):
        rep = report(orders=[order(verdict="CAUTION"), order(placed=2, advice="TAKE"), order(placed=3, advice=None)])
        out, t = self.go(rep, Trader(99.95), only_armed=True)
        self.assertEqual(t.placed, [])
        with mock.patch.dict(os.environ, {"AUTOTRADE_MIN_VERDICT": "CAUTION"}):
            out, t = self.go(rep, Trader(99.95), only_armed=True)
            self.assertEqual([p[0] for p in t.placed], ["armed:EU:111"])

    def test_strict_only_users_get_armed_entries_only_when_the_order_is_strict(self):
        store = ClockStore()
        self.enroll(store, classes=["forex", "strict"])
        out, t = self.go(report(orders=[order()], key="EU"), Trader(99.95), only_armed=True, store=store)    # a market ICT does not trade
        self.assertEqual(t.placed, [])
        out, t = self.go(report(orders=[order()], key="EURUSD"), Trader(99.95), only_armed=True, store=store)
        self.assertEqual([p[0] for p in t.placed], ["armed:EURUSD:111"])
        out, t = self.go(report(signals=[fill("EU-5", mss=5)]), Trader(100.0), store=store)                   # and a non-strict fill is not entered
        self.assertEqual(t.placed, [])

    def test_a_connection_that_fails_is_said_once(self):
        def bad(u, tok):
            raise OSError("no route")
        for _ in range(3):
            out = at.run(self.store, report(signals=[fill()]), trader=bad, now=NOW)
        self.assertEqual(sum("Could not connect" in x["message"] for x in self.store.log), 1)

    def test_a_balance_that_is_missing_enters_nothing_and_does_not_poison_the_day(self):
        out, t = self.go(report(signals=[fill()]), Trader(100.0, balance=0))
        self.assertEqual(t.placed, [])
        self.assertIsNone(self.store.get_user(self.uid)["day"])
        out, t = self.go(report(signals=[fill()]), Trader(100.0))
        self.assertEqual(len(t.placed), 1)

    def test_tp1_leg_and_runner_both_measure_from_the_live_price(self):
        s = fill(management={"partial": 0.5})
        s["setup"] = {"tp1": 101.5, "mss_time": 111}
        out, t = self.go(report(signals=[s]), Trader(100.1))
        self.assertEqual([(p[0], p[1], p[2]) for p in t.placed], [("EU-1", 50.0, 100.1), ("EU-1", 50.0, 100.1)])
        # a TP1 that price has already passed is not traded at all (the fill carries it in setup)
        out, t = self.go(report(signals=[{**fill("EU-2", mss=2), "setup": {"tp1": 100.05, "mss_time": 2}}]), Trader(100.1))
        self.assertEqual(t.placed, [])


# ------------------------------------------------------------------------------------------------ 6. api/scan.py
class ScanApiTest(unittest.TestCase):
    def mod(self):
        spec = importlib.util.spec_from_file_location("scan_api_review", "api/scan.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def call(self, mod, path, headers=None):
        h = mod.handler.__new__(mod.handler)
        h.path, h.headers, h.wfile = path, headers or {}, io.BytesIO()
        h.send_response = lambda code: setattr(h, "code", code)
        h.send_header = lambda k, v: None
        h.end_headers = lambda: None
        h.do_GET()
        return h

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"CRON_SECRET": "s3cret", "AUTOTRADE_ENABLED": "1"})
        self.env.start()
        self.mod_ = self.mod()
        self.auth = {"Authorization": "Bearer s3cret"}

    def tearDown(self):
        self.env.stop()

    def test_the_minute_run_needs_the_cron_secret(self):
        with mock.patch.object(self.mod_, "scan_due", return_value=False), mock.patch("ict_trader.autotrade.run") as run:
            self.assertEqual(self.call(self.mod_, "/api/scan?notify=1").code, 401)
            self.assertEqual(self.call(self.mod_, "/api/scan?notify=1", {"Authorization": "Bearer nope"}).code, 401)
            run.assert_not_called()

    def test_between_closes_it_arms_from_a_fresh_snapshot_within_a_time_budget(self):
        saved = json.dumps({"generated_at": "x", "markets": []})
        with mock.patch.object(self.mod_, "scan_due", return_value=False), mock.patch.object(self.mod_.snapshot, "load", return_value=saved) as load, \
                mock.patch("ict_trader.autotrade.store_from_env", return_value="STORE"), mock.patch("ict_trader.autotrade.run", return_value={"placed": 0}) as run:
            h = self.call(self.mod_, "/api/scan?notify=1", self.auth)
        self.assertEqual(h.code, 200)
        load.assert_called_once_with("scan-5", self.mod_.FRESH_S)
        self.assertLessEqual(self.mod_.FRESH_S, 7 * 60)
        args, kw = run.call_args
        self.assertTrue(kw["only_armed"])
        self.assertLessEqual(kw["budget_s"], 45)
        self.assertEqual(json.loads(h.wfile.getvalue())["autotrade"], {"placed": 0})

    def test_it_does_nothing_when_auto_trading_is_off_or_the_snapshot_is_old(self):
        with mock.patch.object(self.mod_, "scan_due", return_value=False), mock.patch.object(self.mod_.snapshot, "load", return_value=None), \
                mock.patch("ict_trader.autotrade.run") as run:
            self.assertEqual(self.call(self.mod_, "/api/scan?notify=1", self.auth).code, 200)       # no fresh snapshot
            with mock.patch.dict(os.environ, {"AUTOTRADE_ENABLED": "0"}):
                self.assertEqual(self.call(self.mod_, "/api/scan?notify=1", self.auth).code, 200)
            run.assert_not_called()

    def test_it_never_raises(self):
        for failure in (lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")), None):
            with mock.patch.object(self.mod_, "scan_due", return_value=False), mock.patch.object(self.mod_.snapshot, "load", return_value="{not json"), \
                    mock.patch("ict_trader.autotrade.store_from_env", side_effect=failure), mock.patch("ict_trader.autotrade.run", side_effect=failure):
                h = self.call(self.mod_, "/api/scan?notify=1", self.auth)
                self.assertEqual(h.code, 200)
                self.assertIn("error", json.loads(h.wfile.getvalue())["autotrade"])


if __name__ == "__main__":
    unittest.main()
