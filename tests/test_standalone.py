"""Mythos must operate at standalone stage with zero model dependency."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from engine.agent import run_task
from engine.brain_status import brain_status
from engine.cli import main
from engine.config import Settings
from engine.standalone import is_standalone_ready, run_standalone


def _settings(root: Path) -> Settings:
    return Settings(
        root=root,
        autonomy=3,
        provider="local",
        model="none",
        api_key="",
        api_base="http://127.0.0.1:11434/v1",
        host="127.0.0.1",
        port=8790,
        max_steps=8,
        shell_timeout=10,
        allow_secrets=False,
        airgap=True,
        network_mode="airgap",
    )


class ModelIndependentTests(unittest.TestCase):
    def test_standalone_ready_without_any_model(self):
        self.assertTrue(is_standalone_ready())

    def test_brain_status_marks_model_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp))
            with mock.patch("engine.brain_status.local_reachable", return_value=False):
                with mock.patch("engine.brain_status.llama_cpp_available", return_value=False):
                    with mock.patch("engine.brain_status.resolve_gguf", return_value=None):
                        status = brain_status(settings)
        self.assertTrue(status["standalone_ready"])
        self.assertFalse(status["model_required"])
        self.assertEqual(status["runner"], "standalone")
        self.assertTrue(status["offline_ready"])

    def test_run_task_succeeds_without_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
            settings = _settings(root)
            with mock.patch("engine.llm.local_reachable", return_value=False):
                with mock.patch("engine.gguf_infer.can_run_gguf", return_value=False):
                    result = run_task("summarize this project", settings=settings, mode="chat")
        self.assertTrue(result.ok)
        self.assertFalse(result.used_llm)
        self.assertIn("standalone", result.report.lower())
        self.assertTrue(any(e.get("type") == "standalone" for e in result.events))

    def test_create_mode_works_without_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp))
            with mock.patch("engine.llm.local_reachable", return_value=False):
                with mock.patch("engine.gguf_infer.can_run_gguf", return_value=False):
                    result = run_task("write a short myth about rivers", settings=settings, mode="create")
        self.assertTrue(result.ok)
        self.assertFalse(result.used_llm)
        self.assertTrue(len(result.report) > 40)

    def test_code_mode_explores_without_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("x = 1\n", encoding="utf-8")
            settings = _settings(root)
            with mock.patch("engine.llm.local_reachable", return_value=False):
                with mock.patch("engine.gguf_infer.can_run_gguf", return_value=False):
                    result = run_task("explore the repo structure", settings=settings, mode="code")
        self.assertTrue(result.ok)
        self.assertFalse(result.used_llm)
        self.assertIn("main.py", result.report)

    def test_health_reports_model_not_required(self):
        env_buf = StringIO()
        with mock.patch("engine.brain_status.local_reachable", return_value=False):
            with mock.patch("engine.brain_status.llama_cpp_available", return_value=False):
                with mock.patch("engine.brain_status.resolve_gguf", return_value=None):
                    with redirect_stdout(env_buf):
                        code = main(["-r", str(Path(__file__).resolve().parents[1]), "health"])
        self.assertEqual(code, 0)
        data = json.loads(env_buf.getvalue())
        self.assertTrue(data["standalone_ready"])
        self.assertFalse(data["model_required"])
        self.assertEqual(data["runner"], "standalone")
        self.assertTrue(data["offline_ready"])

    def test_standalone_never_calls_remote(self):
        opened: list[str] = []

        def fake_urlopen(req, timeout=0):
            url = req if isinstance(req, str) else getattr(req, "full_url", str(req))
            opened.append(str(url))
            raise OSError("blocked")

        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp))
            with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                out = run_standalone("ping", settings=settings, mode="chat")
        self.assertTrue(out["ok"])
        self.assertEqual(opened, [])


if __name__ == "__main__":
    unittest.main()
