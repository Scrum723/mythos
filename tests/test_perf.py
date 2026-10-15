import json
import tempfile
import time
import unittest
from pathlib import Path

from engine import prefs
from engine.config import Settings
from engine.index import build_index, retrieve
from engine.prompt_build import build_system, prompt_stats
from engine.tools import tool_schemas


class PerfTests(unittest.TestCase):
    def test_slim_prompt_beats_old_dump(self):
        settings = Settings.load(root=str(Path(__file__).resolve().parents[1]), autonomy=3)
        stats = prompt_stats(settings, mode="chat")
        self.assertLess(stats["slim_chars"], stats["old_chars"])
        self.assertGreaterEqual(stats["reduction_pct"], 40.0)
        slim = build_system(settings, mode="chat")
        self.assertIn("NO CHARGES", slim)
        self.assertNotIn("Never leave a feature half-built", slim)

    def test_chat_tools_are_lean(self):
        chat = {t["function"]["name"] for t in tool_schemas(mode="chat")}
        self.assertIn("retrieve", chat)
        self.assertIn("batch_read", chat)
        self.assertNotIn("spawn_agent", chat)
        self.assertNotIn("run_shell", chat)

    def test_prefs_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest import mock

            path = Path(tmp) / "preferences.md"
            with mock.patch.object(prefs, "prefs_path", return_value=path):
                prefs.prefs_path().write_text("# Mythos preferences\n", encoding="utf-8")
                prefs.append("prefer short answers")
                text = prefs.load()
            self.assertIn("prefer short answers", text)

    def test_index_retrieve_faster_than_cold_rebuild(self):
        root = Path(__file__).resolve().parents[1]
        t0 = time.perf_counter()
        build_index(root)
        cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        hits = retrieve(root, "Settings autonomy tool_schemas", limit=5)
        warm = time.perf_counter() - t1
        self.assertTrue(hits)
        self.assertLess(warm, cold)


if __name__ == "__main__":
    unittest.main()
