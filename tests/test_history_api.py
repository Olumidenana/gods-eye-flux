"""/api/history never makes a request wait for a rebuild when a copy exists, and runs one rebuild at a time (it once did the whole rebuild inside
every request after the saved record was renamed, which left the site stuck on "Loading")."""
import json
import unittest
from unittest import mock

from api import history as api


class Store:
    """A stand-in for the saved-record table: name -> (body, age in seconds)."""

    def __init__(self, **rows):
        self.rows, self.saved = dict(rows), []

    def load(self, name, max_age_s):
        row = self.rows.get(name)
        return row[0] if row and row[1] <= max_age_s else None

    def save(self, name, report):
        self.saved.append(name)
        self.rows[name] = (json.dumps(report), 0)
        return True


KEY = "history-5-discipline-v5"
GOOD = json.dumps({"ok": True, "markets": [{"key": "EURUSD"}]})


class HistoryApiTest(unittest.TestCase):
    def setUp(self):
        api._BUILDING.clear()
        self.calls = []
        self.p = [mock.patch.object(api, "universe", lambda: ()),
                  mock.patch.object(api, "history", lambda tf, markets: (self.calls.append(tf), {"ok": True, "markets": [{"key": "NEW"}]})[1])]
        for p in self.p:
            p.start()
            self.addCleanup(p.stop)

    def run_with(self, store, force=False):
        with mock.patch.object(api.snapshot, "load", store.load), mock.patch.object(api.snapshot, "save", store.save):
            status, body, cache = api.serve(5, force)
        return status, json.loads(body), cache

    def test_a_fresh_copy_is_served_without_any_rebuild(self):
        status, body, _ = self.run_with(Store(**{KEY: (GOOD, 60)}))
        self.assertEqual((status, body["markets"][0]["key"], self.calls), (200, "EURUSD", []))

    def test_an_old_copy_is_served_while_another_request_is_rebuilding(self):
        api._BUILDING[5] = __import__("time").time()
        status, body, _ = self.run_with(Store(**{KEY: (GOOD, 3 * 3600)}))
        self.assertEqual((status, body["markets"][0]["key"], self.calls), (200, "EURUSD", []))

    def test_with_nothing_saved_one_request_rebuilds_and_the_next_is_told_to_wait(self):
        store = Store()
        status, body, _ = self.run_with(store)
        self.assertEqual((status, body["markets"][0]["key"], self.calls, KEY in store.saved), (200, "NEW", [5], True))
        api._BUILDING[5] = __import__("time").time()                       # a rebuild is running now
        status, body, cache = self.run_with(Store())
        self.assertEqual((status, body.get("warming"), body["markets"], cache, self.calls), (200, True, [], "no-store", [5]))

    def test_the_shared_lock_counts_too(self):
        status, body, _ = self.run_with(Store(**{"history-5-lock": ("{}", 10)}))
        self.assertTrue(body.get("warming"))
        self.assertEqual(self.calls, [])

    def test_force_cannot_rebuild_a_record_that_is_only_minutes_old_nor_loop(self):
        status, body, _ = self.run_with(Store(**{KEY: (GOOD, 120)}), force=True)
        self.assertEqual((body["markets"][0]["key"], self.calls), ("EURUSD", []))
        status, body, _ = self.run_with(Store(**{KEY: (GOOD, 20 * 60)}), force=True)      # old enough: one rebuild is allowed
        self.assertEqual((body["markets"][0]["key"], self.calls), ("NEW", [5]))

    def test_a_failed_rebuild_serves_the_old_copy_or_a_clear_error_and_never_saves_it(self):
        def boom(tf, markets):
            raise RuntimeError("deriv down")
        with mock.patch.object(api, "history", boom):
            store = Store(**{KEY: (GOOD, 3 * 3600)})
            status, body, _ = self.run_with(store)
            self.assertEqual((status, body["markets"][0]["key"], store.saved), (200, "EURUSD", ["history-5-lock"]))
            api._BUILDING.clear()
            status, body, _ = self.run_with(Store())
            self.assertEqual(status, 502)
            self.assertIn("track record unavailable", body["error"])
        self.assertEqual(api._BUILDING, {})                                  # the lock is released either way


if __name__ == "__main__":
    unittest.main()
