import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WebSyntaxTest(unittest.TestCase):
    """A single unbalanced brace in the page script kills the whole app (a blank page), so the built
    pages must always parse. Skipped where node is not installed."""

    def test_built_page_script_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        for name in ("web/template.html", "index.html", "web/index.html"):
            html = (ROOT / name).read_text(encoding="utf-8")
            scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
            self.assertTrue(scripts, name)
            with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
                f.write(max(scripts, key=len))
            r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{name} does not parse:\n{r.stderr[:500]}")


if __name__ == "__main__":
    unittest.main()
