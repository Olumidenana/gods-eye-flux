"""The app says the same thing the engine does about what is a model.

A MODEL is a complete trade recipe that the adviser's judgement matrix rules on (PULL THE TRIGGER / SIZE DOWN /
STAND DOWN). Everything else (direction, filter, zone, target, management, stop) is a building block: a part, never
listed as a model on the live surfaces, and tested in the Research lab as "ICT 2022 + the part". These tests read the
front end (web/template.html and the pages built from it) and hold it to ict_trader/models.py.
"""
import re
import unittest
from pathlib import Path

from ict_trader import advisor
from ict_trader.models import BUILDING_BLOCKS, MODELS, TRADE_MODELS, kind_of

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("web/template.html", "index.html", "web/index.html")
ENTRY = re.compile(r"^  (\w+): \{ label: '((?:[^'\\]|\\.)*)', icon: '((?:[^'\\]|\\.)*)', kind: '(\w+)'", re.M)
STRING = r"'((?:[^'\\]|\\.)*)'"


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def models_ui(html):
    """MODELS_UI parsed out of the page: {key: {label, icon, kind, about, when}} (regex over the entries)."""
    start = html.index("const MODELS_UI = {")
    body = html[start:html.index("\n};", start)]
    marks = list(ENTRY.finditer(body))
    out = {}
    for i, m in enumerate(marks):
        chunk = body[m.start():marks[i + 1].start() if i + 1 < len(marks) else len(body)]
        text = lambda field: (re.search(field + r": " + STRING, chunk) or [None, ""])[1].replace("\\'", "'")  # noqa: E731
        out[m.group(1)] = {"label": m.group(2).replace("\\'", "'"), "icon": m.group(3), "kind": m.group(4),
                           "about": text("about"), "when": text("when")}
    return out


class UiKindsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read("web/template.html")
        cls.ui = models_ui(cls.html)

    def test_every_python_name_has_a_ui_entry_and_there_are_no_extras(self):
        self.assertEqual(len(self.ui), len(MODELS), "an entry was not parsed, or the count drifted")
        self.assertEqual(set(self.ui), set(MODELS))

    def test_the_ui_kind_is_the_engine_kind_for_every_key(self):
        for k, v in self.ui.items():
            self.assertEqual(v["kind"], kind_of(k), f"{k} is a {kind_of(k)} in ict_trader/models.py")

    def test_seventeen_trade_models_and_the_rest_are_parts(self):
        models = {k for k, v in self.ui.items() if v["kind"] == "model"}
        self.assertEqual(models, set(TRADE_MODELS))
        self.assertEqual(len(models), 17)
        self.assertEqual({k for k, v in self.ui.items() if v["kind"] != "model"}, set(BUILDING_BLOCKS))
        self.assertTrue({v["kind"] for v in self.ui.values()} <= {"model", "direction", "filter", "zone", "target", "management", "stop"})

    def test_a_building_block_is_never_called_a_model_in_its_own_copy(self):
        for k in BUILDING_BLOCKS:
            v = self.ui[k]
            for field in ("label", "about", "when"):
                self.assertIsNone(re.search(r"\bmodels?\b", v[field], re.I), f"{k} {field} calls a building block a model: {v[field]!r}")

    def test_the_pages_built_from_the_template_carry_the_same_list(self):
        for name in PAGES[1:]:
            self.assertEqual(models_ui(read(name)), self.ui, f"{name} is out of date: run python3 scripts/build_web.py")

    def test_live_surfaces_list_trade_models_only(self):
        # No live surface walks every MODELS_UI entry: only the two definitions of TRADE_UI / BLOCK_UI do.
        for n, line in enumerate(self.html.splitlines(), 1):
            if "Object.entries(MODELS_UI)" in line:
                self.assertTrue(re.match(r"const (TRADE_UI|BLOCK_UI) = ", line), f"template.html:{n} lists every MODELS_UI entry: {line[:120]}")
        for target in ("#homeModels", "#sigModels", "#deskModels"):
            line = next(ln for ln in self.html.splitlines() if f"$('{target}').innerHTML" in ln)
            self.assertIn("TRADE_UI", line, target)
            self.assertNotIn("BLOCK_UI", line, target)
        board = self.html[self.html.index("function renderModelBoard()"):]
        self.assertIn("TRADE_UI.map(", board[:600])
        # the agreement chips and the chooser count trade models only
        fit = self.html[self.html.index("function fitHtml()"):self.html.index("function renderHome()")]
        self.assertIn("isTradeModel", fit)
        # the models on a scan market are read through the trade-model filter
        for fn in ("function allState(", "function sameIn(", "function modelStages(", "function allModelSignals(", "function renderForming("):
            body = self.html[self.html.index(fn):][:900]
            self.assertIn("liveModels(m)", body, fn)

    def test_the_research_lab_has_two_labelled_groups(self):
        for text in ("Parts a model uses. A run here tests the ICT 2022 model with this part switched on, to show what it adds.",
                     ">Models <", ">Building blocks <", "KIND_NAMES", "BASE_SHORT} + ${MODELS_UI[k].label}"):
            self.assertIn(text, self.html)
        names = re.search(r"const KIND_NAMES = \{([^}]*)\}", self.html).group(1)
        for kind in ("Direction", "Filter", "Zone", "Target", "Management", "Stop"):
            self.assertIn(f"'{kind}'", names)
        picker = self.html[self.html.index("function rsChips()"):]
        picker = picker[:picker.index("function rsSave()")]
        self.assertIn("TRADE_UI.map(mchip)", picker)
        self.assertIn("BLOCK_UI.filter(([, v]) => v.kind === kind)", picker)
        # a run of everything ticks both groups
        self.assertIn("TRADE_UI.map(([k]) => k)", self.html)
        self.assertIn("BLOCK_UI.map(([k]) => k)", self.html)

    def test_the_verdict_is_said_loudly(self):
        for verdict, call in advisor.CALL.items():
            self.assertIn(f"{verdict}: {{ text: '{call}'", self.html)
        self.assertIn("judged on fewer rows", self.html.lower())
        self.assertIn("a.partial", self.html)          # the flag is read
        # the headline of the matrix card is the call, and the old words stay in the tooltip
        card = self.html[self.html.index("function adviceHtml("):self.html.index("function storyHtml(")]
        self.assertIn('class="adv-call', card)
        self.assertNotIn("Take it", card)
        self.assertIn("callTitle", self.html)
        # a trade row, a desk row and a signal row show it
        self.assertIn("${gradePill(s.quality)} ${advicePill(s.advice)}", self.html)     # trow
        self.assertIn("${callRow(s.advice)}", self.html)                                # desk tables
        self.assertIn("${gradePill(s.quality)}${advicePill(s.advice)}", self.html)      # signal row

    def test_a_what_is_a_model_note_sits_where_models_are_chosen(self):
        self.assertEqual(len(re.findall(r"<div[^>]*data-model-help", self.html)), 4)   # Home, Signals, Desk, Research lab
        self.assertIn("A model is a full trade recipe", self.html)
        self.assertIn("building blocks", self.html.split("const MODEL_HELP = ")[1].split("\n")[0])


if __name__ == "__main__":
    unittest.main()
