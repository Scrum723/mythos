"""Mythos Extreme: council swarm, evolution, local watchdog."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from engine.agency import AgencyStore, self_prompt
from engine.cli import main
from engine.config import Settings
from engine.council import SEATS, run_council
from engine.evolution import evolve_once, evolution_status
from engine.extreme import run_extreme, extreme_status
from engine.watchdog import watch_once, watch_status, compare_snapshots


def _settings(root: Path) -> Settings:
    return Settings(
        root=root,
        autonomy=3,
        provider="local",
        model="qwen2.5-coder:7b",
        api_key="",
        api_base="http://127.0.0.1:11434/v1",
        host="127.0.0.1",
        port=8790,
        max_steps=4,
        shell_timeout=10,
        allow_secrets=False,
        airgap=False,
        network_mode="local",
    )


class CouncilTests(unittest.TestCase):
    def test_seats_include_specialists(self):
        ids = {s["id"] for s in SEATS}
        for need in ("coder", "creator", "defender", "critic", "synthesizer"):
            self.assertIn(need, ids)

    def test_run_council_without_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            settings = _settings(root)
            with mock.patch("engine.llm.local_reachable", return_value=False):
                with mock.patch("engine.gguf_infer.can_run_gguf", return_value=False):
                    result = run_council("harden local defense", settings=settings)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["seats"]), 5)
        self.assertIn("synthesis", result)
        self.assertTrue(len(result["synthesis"]) > 20)
        self.assertFalse(result.get("bills_xai", True))


class ExtremeTests(unittest.TestCase):
    def test_run_extreme_logs_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = _settings(root)
            with mock.patch("engine.llm.local_reachable", return_value=False):
                with mock.patch("engine.gguf_infer.can_run_gguf", return_value=False):
                    out = run_extreme("summarize Mythos strengths", settings=settings, enqueue_followup=True)
        self.assertTrue(out["ok"])
        self.assertIn("council", out)
        self.assertIn("report", out)

    def test_extreme_cli(self):
        with mock.patch("engine.llm.local_reachable", return_value=False):
            with mock.patch("engine.gguf_infer.can_run_gguf", return_value=False):
                buf = StringIO()
                with redirect_stdout(buf):
                    code = main(
                        ["-r", str(Path(__file__).resolve().parents[1]), "extreme", "quick council check"]
                    )
        self.assertEqual(code, 0)
        text = buf.getvalue().lower()
        self.assertTrue("council" in text or "synthesis" in text or "defender" in text)


class EvolutionTests(unittest.TestCase):
    def test_evolve_once_consumes_agency_and_writes_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            agency = AgencyStore(Path(tmp) / "agenda.jsonl")
            ledger = Path(tmp) / "cycles.jsonl"
            self_prompt("run extreme on knowledge gaps", store=agency)
            settings = _settings(Path(tmp))
            with mock.patch("engine.llm.local_reachable", return_value=False):
                with mock.patch("engine.gguf_infer.can_run_gguf", return_value=False):
                    with mock.patch("engine.evolution.default_agency_store", return_value=agency):
                        with mock.patch("engine.evolution.ledger_path", return_value=ledger):
                            cycle = evolve_once(settings=settings)
            self.assertTrue(cycle["ok"])
            self.assertTrue(ledger.is_file())
            status = evolution_status(ledger=ledger, agency=agency)
            self.assertGreaterEqual(status["cycles"], 1)


class WatchdogTests(unittest.TestCase):
    def test_watch_once_records_network_and_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_path = Path(tmp) / "snapshots.jsonl"
            settings = _settings(Path(tmp))
            with mock.patch("engine.watchdog.snapshot_path", return_value=snap_path):
                snap = watch_once(settings=settings)
            self.assertIn("network", snap)
            self.assertIn("device", snap)
            self.assertIn("devices", snap)
            self.assertTrue(snap_path.is_file())
            st = watch_status(path=snap_path)
            self.assertGreaterEqual(st["snapshots"], 1)

    def test_compare_snapshots_detects_change(self):
        a = {"network": {"loopback_llm": True}, "device": {"hostname": "a"}, "devices": []}
        b = {"network": {"loopback_llm": False}, "device": {"hostname": "a"}, "devices": [{"name": "x"}]}
        diff = compare_snapshots(a, b)
        self.assertTrue(any("loopback" in d.lower() or "network" in d.lower() for d in diff["changes"]))
        self.assertTrue(len(diff["changes"]) >= 1)


if __name__ == "__main__":
    unittest.main()
