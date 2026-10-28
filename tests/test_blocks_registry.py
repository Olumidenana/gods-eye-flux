"""The block models are registered everywhere a model must be, and stay out of the live scan until reviewed."""
import os
import unittest
from dataclasses import replace

from ict_trader.config import load_config
from ict_trader.models import LIVE_MODELS, MODEL_INFO, MODELS, PREVIEW_MODELS, make_strategy

CFG = load_config("examples/config.example.toml")


class BlockRegistryTest(unittest.TestCase):
    def test_every_block_model_is_registered_and_builds(self):
        for k in PREVIEW_MODELS:
            self.assertIn(k, MODELS)
            self.assertIn(k, MODEL_INFO)
            self.assertTrue(MODEL_INFO[k]["about"])
            make_strategy(replace(CFG.strategy, model=k), CFG.instrument)

    @unittest.skipIf(os.environ.get("SCAN_MODELS", "all").strip().lower() not in ("", "all"), "SCAN_MODELS narrows the scan")
    def test_preview_models_are_not_in_the_live_scan_by_default(self):
        self.assertEqual([k for k in PREVIEW_MODELS if k in LIVE_MODELS], [])


if __name__ == "__main__":
    unittest.main()
