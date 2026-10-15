import unittest
from pathlib import Path

from engine.config import Settings
from engine.prefs import load as load_prefs
from engine.prompt_build import build_system, _prefs_cached


class TeachingTests(unittest.TestCase):
    def test_prefs_include_efficient_method_and_anti_patterns(self):
        text = load_prefs()
        lower = text.lower()
        self.assertIn("efficient method", lower)
        self.assertIn("tutorial", lower)
        self.assertIn("api.docweatherai.com", lower)
        self.assertIn("write the files", lower)
        self.assertIn("nws", lower)

    def test_build_system_includes_teaching(self):
        _prefs_cached.cache_clear()
        settings = Settings.load(root=Path(__file__).resolve().parents[1], autonomy=3)
        prompt = build_system(settings, mode="code")
        lower = prompt.lower()
        self.assertIn("tutorial", lower)
        self.assertTrue(
            "api.docweatherai.com" in lower or "fake" in lower,
            "prompt must warn against invented/fake APIs",
        )
        self.assertTrue(
            "efficient method" in lower or "write files" in lower or "write the files" in lower,
            "prompt must include efficient work method",
        )
        self.assertIn("no charges", lower)


if __name__ == "__main__":
    unittest.main()
