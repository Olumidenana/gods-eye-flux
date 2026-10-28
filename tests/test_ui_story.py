"""The page tells ICT's story the way the engine writes it, draws the research funnel, and its copy is true.

Three kinds of check, all on web/template.html and the pages built from it:
  * the story (analysis.story from ict_trader/narrative.py) is shown as ICT's four questions, on Home in short and in the
    Desk / market read in full, with the stand-aside as a clear state;
  * the Research lab's funnel (result.funnel from ict_trader/research.py) is drawn above the trade list, and the verdict
    card is never cut short;
  * the words (the ICT 2022 Model, the Research lab, the Bot tab, About) say what the engine now does.
The helpers are also run for real in node (skipped where node is not installed).
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ict_trader import narrative, research
from ict_trader.models import BUILDING_BLOCKS

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("web/template.html", "index.html", "web/index.html")


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


class StoryShownTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read("web/template.html")

    def test_the_pages_built_from_the_template_carry_it(self):
        for name in PAGES[1:]:
            page = read(name)
            for needle in ("function storyCardHtml(", "function funnelHtml(", 'id="homeStory"', "Why so few trades?"):
                self.assertIn(needle, page, f"{name} is out of date: run python3 scripts/build_web.py")

    def test_the_fields_the_page_reads_are_the_fields_the_engine_writes(self):
        written = set(narrative.Narrative(0, "none", "", "", "", None, None, ()).to_json())
        self.assertEqual(written, {"bias", "conviction", "came_from", "going_to", "location", "draw", "stand_aside", "lines", "profile"})
        card = between(self.html, "function storyCardHtml(", "// Home: markets that have a story first")
        for field in ("came_from", "going_to", "location", "stand_aside", "conviction", "bias"):
            self.assertIn(f"s.{field}", card, field)
        self.assertIn("s.draw", self.html[self.html.index("const storyDraw"):][:200])
        for word in ("bullish", "neutral"):                      # the page asks for a bullish story and for neutral (no story); anything else is the bearish one
            self.assertIn(f"'{word}'", between(self.html, "const storyOf", "const CONVICTION"))
        conv = re.search(r"const CONVICTION = \{([^}]*)\}", self.html).group(1)
        for level in ("strong", "moderate", "weak"):             # ... and the three convictions that carry a story
            self.assertIn(level + ":", conv)

    def test_it_is_icts_four_questions_in_plain_words(self):
        card = between(self.html, "function storyCardHtml(", "// Home: markets that have a story first")
        for q in ("Where is price coming from?", "Where is it going?", "The draw on liquidity", "Where is it now?", "Premium or discount",
                  "Is there a story to trade?", "STAND ASIDE"):
            self.assertIn(q, card)
        self.assertIn("ICT builds the story first; a model only takes a raid that fits it.", self.html)
        self.assertIn("the strategy trades on", card)             # it says the trades use this very story

    def test_the_story_is_on_home_in_short_and_in_the_market_reads_in_full(self):
        home = self.html[self.html.index('<section class="view" id="v-home">'):self.html.index('<section class="view" id="v-edge">')]
        self.assertLess(home.index('id="homeStory"'), home.index('id="homeModels"'))   # the story before the models
        self.assertIn("renderHomeStory();", between(self.html, "function renderHome()", "const markStart"))
        self.assertIn("show all", between(self.html, "function homeStoryHtml()", "function renderHomeStory()").lower())
        self.assertIn("STORY_SHOW", self.html)
        lc = between(self.html, "function renderLcRead(", "$('#lcMarket').onchange")
        self.assertIn("storyCardHtml(a.story", lc)               # the Desk, above the checklist
        self.assertLess(lc.index("storyCardHtml(a.story"), lc.index('<div class="why-grid">'))   # ... and the checklist is in the grid below
        read_card = between(self.html, "function readCard(m)", "let readAll")
        self.assertIn("storyCardHtml(a.story", read_card)        # 'What the engine saw today'
        self.assertLess(read_card.index("storyCardHtml(a.story"), read_card.index('<div class="read-body">'))

    def test_the_live_read_table_says_stand_aside_where_a_market_is_only_watching(self):
        table = between(self.html, "function renderReadTable(", "$('#readToggle').onclick")
        self.assertIn("storyAside(sa)", table)
        self.assertIn("Stand aside: ${sa.stand_aside", table)

    def test_the_state_classes_do_not_collide_with_the_colour_helpers(self):
        # .bull / .bear colour all the text inside them: the cards use is-up / is-down / is-aside
        self.assertNotRegex(self.html, r'class="nv(?:-row)? (?:bull|bear)')
        self.assertIn("nv is-${kind}", self.html)
        self.assertIn("nv-row is-${k}", self.html)


class FunnelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read("web/template.html")

    def test_every_stage_the_engine_counts_has_a_plain_words_line(self):
        hints = re.search(r"const FUNNEL_HINT = \{(.*?)\n\};", self.html, re.S).group(1)
        labels = {m for m in re.findall(r"^  '([^']+)':", hints, re.M)}
        self.assertEqual(labels, {label for label, _rules, _total in research._FUNNEL}, "FUNNEL_HINT drifted from research._FUNNEL")

    def test_the_funnel_card_sits_above_the_trade_list_and_the_verdict_is_whole(self):
        detail = between(self.html, "$('#rsDetail').innerHTML = `", "const rsTick")
        self.assertIn("${funnelHtml(d)}", detail)
        self.assertLess(detail.index("${funnelHtml(d)}"), detail.index('<div id="rsTrades">'))
        self.assertIn("${verdictCardHtml(d)}", detail)
        self.assertLess(detail.index("${verdictCardHtml(d)}"), detail.index("${funnelHtml(d)}"))
        self.assertNotIn("esc(d.verdict.text)", detail)           # the old one-line paragraph is gone: the card carries it
        card = between(self.html, "function verdictCardHtml(", "// Why so few trades")
        self.assertIn("esc(v.text)", card)
        self.assertNotRegex(self.html[self.html.index(".vcard{"):self.html.index(".fn{")], r"line-clamp|ellipsis|max-height|overflow:hidden")

    def test_it_says_what_to_do_below_thirty_trades(self):
        funnel = between(self.html, "function funnelHtml(", "function rsRender()")
        for needle in ("Why so few trades?", "Thirty trades is the least before a verdict means anything", "pool more markets", "longer window", "faster timeframe", "All day",
                       "scaled to the largest", "d.funnel"):
            self.assertIn(needle, funnel)

    def test_the_pooled_verdict_is_written_out_under_the_combined_table(self):
        matrix = between(self.html, "function rsMatrix()", "document.addEventListener('click', e => { const b = e.target.closest('[data-rstier]')")
        self.assertIn("everything.verdict.text", matrix)
        self.assertIn('class="vcard', matrix)


class WordsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read("web/template.html")

    def test_the_ict_2022_model_says_it_reads_the_story_and_is_ruled_by_the_matrix(self):
        entry = between(self.html, "  ict2022: {", "  silver_bullet: {")
        for needle in ("story", "stand aside", "SIZE DOWN", "draw"):
            self.assertIn(needle, entry)

    def test_the_control_is_a_direction_building_block_and_the_models_built_on_the_story_say_so(self):
        self.assertIn("nonarrative: { label: 'No narrative (control)', icon: '∅', kind: 'direction'", self.html)
        self.assertIn("nonarrative", BUILDING_BLOCKS)
        for key in ("silver_bullet", "judas_swing", "ote", "unicorn", "full", "osok"):
            body = between(self.html, f"  {key}: {{", "\n  " if key != "full" else "\n};")
            self.assertRegex(body, r"story|ICT 2022", key)

    def test_the_research_lab_and_the_chooser_say_the_story_comes_first(self):
        lab = between(self.html, '<section class="view" id="v-research">', 'id="rsModelBox"')
        self.assertIn("reads the story first", lab)
        self.assertIn("applies in both", lab)                    # the story is price-only: both modes
        self.assertIn("read the story first and only take a raid that fits it", self.html.split("const MODEL_HELP = ")[1].split("\n")[0])
        self.assertIn("read the story first and only take a raid that fits it", between(self.html, "function rsChips()", "function rsSave()"))

    def test_the_bot_tab_says_what_the_bots_do_now(self):
        bot = self.html[self.html.index('<section class="view" id="v-bot">'):self.html.index('<section class="view" id="v-setups">')]
        for needle in ("PULL THE TRIGGER", "the moment price touches", "does not chase", "live price", "SIZE DOWN and STAND DOWN plans are not traded"):
            self.assertIn(needle, bot)
        for old in ("enters at market as soon as a signal fires", "exactly as the backtest assumes", "every new signal from the engine is placed within a minute"):
            self.assertNotIn(old, bot)
        # the two limits named in the words are the two the guard uses (mirror of ict_trader/entryguard.py)
        eg = re.search(r"const EG = \{ chase: ([\d.]+), deep: ([\d.]+)[^}]*\}", self.html)
        self.assertIn(f"more than {eg.group(1)}R from the entry", bot)
        self.assertIn(f"more than {eg.group(2)}R through the entry", bot)

    def test_about_and_the_playbook_start_from_the_story(self):
        about = self.html[self.html.index('<section class="view" id="v-about">'):self.html.index("</main>")]
        self.assertIn("Build the story first", about)
        self.assertLess(about.index("Build the story first"), about.index("Wait for the window"))
        for needle in ("A raid that fits the story", "The matrix rules on it", "Entered while the plan holds", "Target the draw"):
            self.assertIn(needle, about)
        self.assertEqual(about.count('<div class="card step"><h3>'), 9 + 3)   # the nine steps of a trade and the three on prices
        self.assertEqual(self.html.count("They work on top of the story"), 2)    # the static line and the one set from the rule count

    def test_the_signal_trail_explains_the_story_rule(self):
        self.assertIn("'NR-01':", self.html)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class RunInNodeTest(unittest.TestCase):
    """Run the helpers for real: the story cards, the Home list and the funnel, on the shapes the engine writes."""

    @classmethod
    def setUpClass(cls):
        html = read("web/template.html")
        story = between(html, "const STORY_LINE", "const STAGE_TXT")
        funnel = between(html, "// The verdict, in full", "function rsRender()")
        lv = re.search(r"const LV_LABEL = \{[^\n]*\};", html).group(0)
        cls.lib = ("const document = { addEventListener() {} };\nconst esc = s => String(s).replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));\n"
                   "let scanData = null; const verdictPill = v => `<pill>${v.code}</pill>`;\n" + lv + "\n" + story + "\n" + funnel)

    def run_js(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
            f.write(self.lib + "\n" + body)
        r = subprocess.run([shutil.which("node"), f.name], capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[:800])
        return json.loads(r.stdout)

    def test_a_story_is_four_questions_and_a_stand_aside_is_a_clear_state(self):
        out = self.run_js("""
          const bull = { bias: 'bullish', conviction: 'strong', came_from: "Weekly: last week closed 1.0850 above the prior week's high 1.0830. Daily: yesterday closed 1.0872 above the prior day's high 1.0861. Sell-side liquidity was taken first today.",
            going_to: 'The buy-side draw is PDH at 1.0912, 45 pips away.', location: "In the discount of yesterday's range (50% at 1.0868).", draw: { name: 'PDH', price: 1.0912 }, stand_aside: null, lines: [] };
          const aside = { bias: 'neutral', conviction: 'none', came_from: 'Daily: inside or two-sided day: no clear daily draw.', going_to: 'No draw to aim at: stand aside.', location: "In the premium of yesterday's range (50% at 101.0).", draw: null, stand_aside: 'no clear daily draw (an inside or two-sided day): nothing to lean on', lines: [] };
          const done = { ...bull, conviction: 'none', draw: null, going_to: 'The buy-side draw is already fulfilled.', stand_aside: "the day's draw is already fulfilled: no unpurged pool is left in that direction" };
          const evil = { ...aside, stand_aside: '<img src=x onerror=alert(1)>' };
          console.log(JSON.stringify({ bull: storyCardHtml(bull), aside: storyCardHtml(aside), done: storyCardHtml(done), evil: storyCardHtml(evil), none: storyCardHtml(null),
            labels: ['PDH', 'PWL', 'IPDA20_H', 'IPDA60_L', 'NDOG 10-14 CE', 'NWOG 10-12 H', 'CBDR+2SD', 'EQH 1.0842', 'SWL 1.01', 'ASIA_H', 'MYSTERY'].map(drawLabel) }));""")
        self.assertIn("is-up", out["bull"])
        self.assertIn("Bullish story", out["bull"])
        self.assertIn("Strong conviction", out["bull"])
        self.assertEqual(out["bull"].count("<dt>"), 4)
        self.assertIn("the prior-day high at 1.0912", out["bull"])           # the engine's code, in words
        self.assertNotIn("PDH", out["bull"])
        self.assertIn("Draw · Prior-day high 1.0912", out["bull"])
        self.assertIn("<p>Weekly:", out["bull"])                              # one sentence a line
        self.assertIn('class="pd-discount"', out["bull"])
        self.assertNotIn("STAND ASIDE", out["bull"])
        self.assertIn("is-aside", out["aside"])
        self.assertIn("STAND ASIDE.</span> No clear daily draw", out["aside"])
        self.assertIn('class="pd-premium"', out["aside"])
        self.assertNotIn("conviction", out["aside"])
        self.assertIn("The daily draw leans bullish", out["done"])            # a draw already reached still says which way it leans
        self.assertIn("STAND ASIDE", out["done"])
        self.assertNotIn("<img", out["evil"])                                 # the engine's words are text, never markup
        self.assertEqual(out["none"], "")
        self.assertEqual(out["labels"], ["Prior-day high", "Prior-week low", "20-day high", "60-day low", "New-day opening gap 10-14 midpoint",
                                         "New-week opening gap 10-12 high", "CBDR +2 SD", "Equal highs", "Swing low", "Asia high", "MYSTERY"])

    def test_home_lists_stories_first_then_stand_asides_and_limits_itself(self):
        out = self.run_js("""
          const mk = (label, bias, conviction, stand) => ({ ok: true, label, broker_symbol: 'frx' + label, analysis: { story: { bias, conviction, came_from: 'Daily: x.', going_to: '', location: "In the discount of yesterday's range (50% at 1).",
            draw: bias === 'neutral' ? null : { name: 'PDH', price: 1.1 }, stand_aside: stand, lines: [] } } });
          const ms = [];
          for (let i = 0; i < 9; i++) ms.push(mk('A' + i, 'neutral', 'none', 'no clear daily draw'));
          for (let i = 0; i < 7; i++) ms.push(mk('S' + i, i % 2 ? 'bearish' : 'bullish', ['weak', 'strong', 'moderate'][i % 3], null));
          ms.push({ ok: true, label: 'OLD', analysis: {} });                   // an older scan: no story field
          ms.push({ ok: false, label: 'DOWN' });
          scanData = { markets: ms, generated_ny: 'Mon 05 Oct 12:00' };
          const short = homeStoryHtml(); storyAll = true; const all = homeStoryHtml(); scanData = { markets: [{ ok: true, label: 'X', analysis: {} }] };
          const count = (h, re) => (h.match(re) || []).length;
          const firstStrong = short.indexOf('strong'), firstAside = short.indexOf('Stand aside:');
          console.log(JSON.stringify({ shortStories: count(short, /nv-row is-(up|down)/g), shortAsides: count(short, /nv-row is-aside/g), allStories: count(all, /nv-row is-(up|down)/g), allAsides: count(all, /nv-row is-aside/g),
            showAll: /Show all 16 markets/.test(short), fewer: /Show fewer/.test(all), storyBeforeAside: short.indexOf('is-up') < firstAside && firstStrong < firstAside, empty: homeStoryHtml(),
            explainer: short.includes('ICT builds the story first; a model only takes a raid that fits it.'), rankedStrongFirst: /nv-row is-(up|down)[^]*?strong/.test(short.split('Stand aside')[0]) }));""")
        self.assertEqual((out["shortStories"], out["shortAsides"]), (4, 4))
        self.assertEqual((out["allStories"], out["allAsides"]), (7, 9))
        self.assertTrue(out["showAll"])
        self.assertTrue(out["fewer"])
        self.assertTrue(out["storyBeforeAside"])
        self.assertEqual(out["empty"], "")                                    # no market with a story field: no card
        self.assertTrue(out["explainer"])

    def test_the_funnel_scales_its_bars_and_the_card_changes_with_the_trade_count(self):
        out = self.run_js("""
          const f = [{ label: 'Raids on a pool inside a window', count: 200, reasons: [] },
            { label: 'Ignored: no story, or against it', count: 100, reasons: [['sweep ignored: stand aside, no clear daily draw (an inside or two-sided day): nothing to lean on', 60], ['EQH # sweep ignored: against the story', 40]] },
            { label: 'Cancelled before they filled', count: 25, reasons: [['PDH limit cancelled: not filled within # candles', 25]] },
            { label: 'Trades taken', count: 0, reasons: [] }, { label: 'A stage from a newer engine <b>', count: 5, reasons: [] }];
          const few = funnelHtml({ funnel: f, stats: { trades: 8 } }), many = funnelHtml({ funnel: f, stats: { trades: 52 } });
          const widths = [...few.matchAll(/style="width:([\\d.]+)%/g)].map(m => +m[1]);
          console.log(JSON.stringify({ few, many, widths, none: funnelHtml({ stats: { trades: 3 } }), bad: funnelHtml({ funnel: 'x', stats: { trades: 3 } }),
            verdict: verdictCardHtml({ verdict: { code: 'not enough setups', text: 'Only 8 trades. So far -0.47R, luck alone could put it from -1.08R to +0.14R.' }, stats: { trades: 8 } }) }));""")
        self.assertEqual(out["widths"], [100.0, 50.0, 12.5, 0.0, 2.5])         # scaled to the largest count; nothing is drawn for zero
        self.assertIn("Why so few trades?", out["few"])
        self.assertIn("Thirty trades is the least before a verdict means anything, and this test has 8.", out["few"])
        self.assertIn("Where the raids went", out["many"])
        self.assertNotIn("Why so few trades?", out["many"])
        self.assertIn("52 trades is enough for a verdict", out["many"])
        self.assertIn("<span>Stand aside, no clear daily draw (an inside or two-sided day): nothing to lean on</span>", out["few"])   # the log prefix is gone
        self.assertIn("Limit on Prior-day high cancelled: not filled within … candles", out["few"])
        self.assertNotIn("<b>", out["few"].split("A stage from a newer engine")[1].split("</span>")[0])    # a label is text
        self.assertEqual(out["none"], "")
        self.assertEqual(out["bad"], "")
        self.assertIn("luck alone could put it from -1.08R to +0.14R.", out["verdict"])                   # the whole sentence
        self.assertIn("vcard info", out["verdict"])


if __name__ == "__main__":
    unittest.main()



class TradesTakenWiringTests(unittest.TestCase):
    """One ledger feeds Home, Daily results and Trades taken, and the sign-up wall is up from the first paint."""

    def setUp(self):
        self.html = open("web/template.html", encoding="utf-8").read()

    def test_one_ledger_feeds_every_figure(self):
        for needle in ("function ledger()", "function ledgerStats(", "const recent = ledger();", "const ls = ledgerStats(err ? [] : ledger()", "function renderTaken()", 'id="v-taken"'):
            self.assertIn(needle, self.html, needle)

    def test_the_app_opens_on_the_trades_taken(self):
        self.assertIn("store.get('startView', 'taken')", self.html)
        self.assertIn("{ v: 'taken', label: 'Trades taken', main: true", self.html)

    def test_the_wall_is_up_from_the_first_paint_with_no_way_around_it(self):
        self.assertIn('<body class="gated">', self.html)
        self.assertNotIn("Look around first", self.html)
        self.assertIn("async function bootAccess()", self.html)
        self.assertNotIn("store.get('welcomed'", self.html)


class InstallButtonTests(unittest.TestCase):
    """The install button is always findable while the app is not installed: sign-up page, Home, Trades taken and the top bar."""

    def test_install_is_offered_everywhere_and_the_help_sheet_clears_the_wall(self):
        html = open("web/template.html", encoding="utf-8").read()
        self.assertGreaterEqual(html.count('class="card newsbar js-install"'), 2)          # Home and Trades taken
        self.assertIn('data-install hidden style="max-width:400px', html)                  # the sign-up page
        self.assertIn("#iosSheet{z-index:120}", html)                                      # above the wall (z-index 95)
        self.assertIn("async function installApp()", html)
        self.assertNotIn("if (!standalone) $('#installBtn').hidden = false", html)         # no longer waits for the browser's event


class NotificationPromptTests(unittest.TestCase):
    """Alerts are asked for at the top of the pages people land on, and the start-page picker knows the landing page."""

    def test_the_prompt_is_at_the_top_and_the_picker_lists_trades_taken(self):
        html = open("web/template.html", encoding="utf-8").read()
        self.assertGreaterEqual(html.count('class="card newsbar js-push"'), 2)                 # Home and Trades taken
        self.assertIn("if (v === 'taken' || v === 'home') renderPush();", html)              # worked out on every landing, not only on Home
        self.assertIn('data-push="on">Turn on notifications</button>', html)
        self.assertIn('<button data-start="taken">Trades taken</button>', html)


class LivePriceTests(unittest.TestCase):
    """The page listens to Deriv for the markets with a trade open, one result feeds every figure, and polling pauses in the background."""

    def setUp(self):
        self.html = open("web/template.html", encoding="utf-8").read()

    def test_open_trades_use_the_live_price_everywhere(self):
        for needle in ("const marketOf = s => liveMkt(", "function rNow(s)", "const r = s => rNow(s),", "data-live-r=", "data-live-adv=", "data-live-kpi", "function liveSync()", "liveSync();\n}\nasync function loadHistory"):
            self.assertIn(needle, self.html, needle)

    def test_a_banked_partial_or_a_zero_price_never_overrides_the_scan(self):
        self.assertIn("if (L && L[0].status !== 'open') return r;", self.html)
        self.assertIn("if (isFinite(q) && q > 0)", self.html)

    def test_polling_pauses_while_the_app_is_in_the_background_except_for_the_armed_bot(self):
        for needle in ("const botLive = () => botCfg.auto && bot.broker && bot.broker.ws;", "if (!document.hidden || botLive()) loadSignals();", "if (!document.hidden) loadHistory();", "function liveWanted() {", "if (document.hidden) return [];"):
            self.assertIn(needle, self.html, needle)


class ActNowTests(unittest.TestCase):
    """One page says what to do in plain words: set a limit, buy or sell now, take profit, move the stop, close, wait."""

    def setUp(self):
        self.html = open("web/template.html", encoding="utf-8").read()

    def test_the_page_is_in_the_menu_and_reachable_from_home(self):
        self.assertIn("{ v: 'act', label: 'Act now', main: true", self.html)
        self.assertIn('id="v-act"', self.html)
        self.assertIn("if (v === 'act') renderAct();", self.html)
        self.assertIn("if (viewOn('act')) renderAct();", self.html)
        self.assertIn('<button data-start="act">Act now</button>', self.html)
        self.assertIn('<a href="#act"><b>Act now →</b></a>', self.html)    # the "What to take now" card points at it

    def test_every_instruction_is_spelled_out(self):
        for needle in ("SET A ${actDir(o.direction)} LIMIT on", "DON'T TAKE:", "TAKE PROFIT: close it all", "TAKE PROFIT: close part, stop to entry", "MOVE YOUR STOP to the entry",
                       "CLOSE IT NOW: the stop is hit", "${actDir(s.direction)} NOW at market", "DON'T ENTER", "GET READY", "Take profit 1", "Take profit 2", "Stop loss", "Cancel it if it has not filled in"):
            self.assertIn(needle, self.html, needle)

    def test_a_stand_down_verdict_is_never_shown_as_an_order_to_place(self):
        self.assertIn("const place = orders.filter(x => rank((x.o.advice || {}).verdict) < 2), skip = orders.filter(x => rank((x.o.advice || {}).verdict) === 2);", self.html)
        self.assertIn("v === 'SKIP' ? { cls: 'bad', t: \"DON'T ENTER: ICT would stand down on this one\" }", self.html)

    def test_the_reasons_and_the_second_try_are_shown_in_words(self):
        for needle in ("function actWhy(a, story)", "<b>Why:</b>", "more checks (", "const REENTRY_NOTE", "a.reentry ? `<span class=\"call-fr\"", "2nd try", "(a false breakout); that close is the entry."):
            self.assertIn(needle, self.html, needle)


class BootResilienceTests(unittest.TestCase):
    """The page never sits on "Loading ICT Flux" because one server call never answered."""

    def setUp(self):
        self.html = open("web/template.html", encoding="utf-8").read()

    def test_the_boot_calls_give_up_and_the_history_loader_asks_again_while_it_is_being_built(self):
        for needle in ("function fetchT(url, opts = {}, ms = 8000)", "await fetchT('/api/account?op=config')", "fetchT('/api/account?op=me', { headers: { Authorization: 'Bearer ' + t } }, 12000)",
                       "const accessReady = fetchT('/api/access?op=status')", "setTimeout(() => c.abort(), 45000)", "histData && histData.warming"):
            self.assertIn(needle.replace("await fetchT", "fetchT") if needle.startswith("await") else needle, self.html, needle)
