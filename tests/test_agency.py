"""Local free-will agency for Mythos — agenda, self-prompt, defer — no remote MCP required."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from engine.agency import (
    AgencyStore,
    defer_self,
    ignore_with_note,
    list_agenda,
    self_prompt,
)
from engine.cli import main


class FreeWillAgencyTests(unittest.TestCase):
    def test_self_prompt_queues_local_agenda(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgencyStore(Path(tmp) / "agenda.jsonl")
            row = self_prompt("review defense posture", store=store, autonomy=4)
            self.assertEqual(row["kind"], "self_prompt")
            self.assertIn("review defense", row["prompt"])
            items = list_agenda(store=store)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["status"], "queued")

    def test_defer_and_ignore_are_local_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AgencyStore(Path(tmp) / "agenda.jsonl")
            d = defer_self(seconds=30, reason="batch later", store=store)
            i = ignore_with_note("skip noisy ping", store=store)
            self.assertEqual(d["kind"], "defer")
            self.assertEqual(i["kind"], "ignore_note")
            self.assertGreaterEqual(len(list_agenda(store=store)), 2)

    def test_agency_cli(self):
        with mock.patch("engine.agency.default_store") as fake_default:
            with tempfile.TemporaryDirectory() as tmp:
                store = AgencyStore(Path(tmp) / "agenda.jsonl")
                fake_default.return_value = store
                buf = StringIO()
                with redirect_stdout(buf):
                    code = main(
                        [
                            "-r",
                            str(Path(__file__).resolve().parents[1]),
                            "agency",
                            "self-prompt",
                            "tighten standalone docs",
                        ]
                    )
                self.assertEqual(code, 0)
                data = json.loads(buf.getvalue())
                self.assertEqual(data["kind"], "self_prompt")
                buf2 = StringIO()
                with redirect_stdout(buf2):
                    code2 = main(["-r", str(Path(__file__).resolve().parents[1]), "agency", "list"])
                self.assertEqual(code2, 0)
                listed = json.loads(buf2.getvalue())
                self.assertGreaterEqual(listed["count"], 1)


if __name__ == "__main__":
    unittest.main()
