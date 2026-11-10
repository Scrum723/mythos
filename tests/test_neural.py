"""Mythos neural pattern graph + playbooks."""

from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from engine.cli import main
from engine.knowledge import knowledge_snapshot
from engine.neural import neural_snapshot, playbooks, train_from_neural


class NeuralIngestTests(unittest.TestCase):
    def test_neural_graph_has_ingested_sources(self):
        snap = neural_snapshot()
        self.assertGreaterEqual(snap["source_count"], 25)
        self.assertGreaterEqual(snap["ingested_readmes"], 20)
        self.assertTrue(snap["no_charges"])
        ids = {p["id"] for p in snap["playbooks"]}
        self.assertIn("poteto-ops", ids)
        self.assertIn("creator-flywheel", ids)

    def test_knowledge_includes_neural(self):
        snap = knowledge_snapshot()
        self.assertIn("neural", snap)
        self.assertGreaterEqual(snap["neural"]["source_count"], 25)

    def test_playbooks_exist_on_disk(self):
        rows = playbooks()
        self.assertGreaterEqual(len(rows), 2)
        for row in rows:
            path = Path(__file__).resolve().parents[1] / row["path"]
            self.assertTrue(path.is_file(), msg=row["path"])

    def test_neural_cli_status(self):
        buf = StringIO()
        with redirect_stdout(buf):
            code = main(["-r", str(Path(__file__).resolve().parents[1]), "neural", "status"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertGreaterEqual(data["ingested_readmes"], 20)

    def test_train_from_neural_enqueues_followup(self):
        out = train_from_neural(note="unit-test neural train")
        self.assertTrue(out["ok"])
        self.assertIn("improvement", out)
        self.assertEqual(out["followup"]["kind"], "self_prompt")


if __name__ == "__main__":
    unittest.main()
