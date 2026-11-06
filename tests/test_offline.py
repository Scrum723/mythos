"""Offline / airgap / loopback policy for Mythos standalone inference."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from engine.brain_status import brain_status
from engine.cli import main
from engine.config import Settings
from engine.llm import LLMClient, LLMError
from engine.network_policy import airgap_enabled, assert_local_llm_base, is_loopback_url


def _settings(api_base: str) -> Settings:
    kwargs = dict(
        root=Path(".").resolve(),
        autonomy=3,
        provider="local",
        model="qwen2.5-coder:7b",
        api_key="",
        api_base=api_base,
        host="127.0.0.1",
        port=8790,
        max_steps=8,
        shell_timeout=10,
        allow_secrets=False,
    )
    # Prefer new fields when present (after Task 2 implementation).
    try:
        return Settings(**kwargs, airgap=False, network_mode="local")
    except TypeError:
        return Settings(**kwargs)


class NetworkPolicyTests(unittest.TestCase):
    def test_is_loopback_accepts_localhost_and_rejects_remote(self):
        self.assertTrue(is_loopback_url("http://127.0.0.1:11434/v1"))
        self.assertTrue(is_loopback_url("http://localhost:11434/v1"))
        self.assertTrue(is_loopback_url("http://[::1]:11434/v1"))
        self.assertFalse(is_loopback_url("https://api.x.ai/v1"))
        self.assertFalse(is_loopback_url("http://8.8.8.8:11434/v1"))
        self.assertFalse(is_loopback_url("https://example.com/v1"))

    def test_assert_local_llm_base_rejects_remote(self):
        with self.assertRaises((LLMError, ValueError)) as ctx:
            assert_local_llm_base("https://example.com/v1")
        msg = str(ctx.exception).lower()
        self.assertTrue("loopback" in msg or "local" in msg or "airgap" in msg)

    def test_llm_chat_refuses_non_loopback_base(self):
        client = LLMClient(_settings("https://example.com/v1"))
        with self.assertRaises(LLMError) as ctx:
            client.chat([{"role": "user", "content": "hi"}])
        msg = str(ctx.exception).lower()
        self.assertTrue(
            "loopback" in msg or "local-only" in msg or "local only" in msg or "airgap" in msg or "not allowed" in msg
        )

    def test_airgap_enabled_from_env(self):
        env = os.environ.copy()
        try:
            os.environ["MYTHOS_AIRGAP"] = "1"
            os.environ.pop("CODING_AIRGAP", None)
            self.assertTrue(airgap_enabled())
            settings = Settings.load(root=".", autonomy=3)
            self.assertTrue(settings.airgap)
            self.assertEqual(settings.network_mode, "airgap")
        finally:
            os.environ.clear()
            os.environ.update(env)


class GgufInferTests(unittest.TestCase):
    def test_llm_uses_gguf_when_ollama_down(self):
        import sys
        import types

        from engine import gguf_infer, llm as llm_mod
        from engine.llm import LLMClient

        calls: list[str] = []

        class FakeLlama:
            def __init__(self, *args, **kwargs):
                calls.append("init")

            def create_chat_completion(self, messages=None, **kwargs):
                calls.append("chat")
                return {
                    "choices": [
                        {
                            "message": {"content": "mythos-offline-ok", "role": "assistant"},
                            "finish_reason": "stop",
                        }
                    ]
                }

        fake = types.ModuleType("llama_cpp")
        fake.Llama = FakeLlama
        with tempfile.TemporaryDirectory() as tmp:
            gguf = Path(tmp) / "brain.gguf"
            gguf.write_bytes(b"0" * 1_000_001)
            settings = _settings("http://127.0.0.1:11434/v1")
            client = LLMClient(settings)
            with mock.patch.dict(sys.modules, {"llama_cpp": fake}):
                with mock.patch.object(llm_mod, "local_reachable", return_value=False):
                    with mock.patch("engine.gguf_infer.resolve_gguf", return_value=gguf):
                        with mock.patch("engine.brain_status.resolve_gguf", return_value=gguf):
                            with mock.patch("engine.brain_status.local_reachable", return_value=False):
                                self.assertTrue(gguf_infer.llama_cpp_available())
                                self.assertTrue(client.available)
                                result = client.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(result.get("content"), "mythos-offline-ok")
        self.assertIn("chat", calls)
        self.assertEqual(result.get("tool_calls"), [])


class BrainStatusTests(unittest.TestCase):
    def test_brain_status_reports_missing_gguf(self):
        with tempfile.TemporaryDirectory() as tmp:
            models = Path(tmp) / "models"
            models.mkdir()
            settings = _settings("http://127.0.0.1:11434/v1")
            with mock.patch("engine.brain_status.models_dir", return_value=models):
                with mock.patch("engine.brain_status.local_reachable", return_value=False):
                    with mock.patch("engine.brain_status.llama_cpp_available", return_value=False):
                        status = brain_status(settings)
        self.assertFalse(status["gguf_present"])
        self.assertIsNone(status["gguf_path"])
        self.assertEqual(status["runner"], "none")
        self.assertFalse(status["offline_ready"])
        self.assertIn(status["network_mode"], {"local", "airgap"})
        self.assertIn("airgap", status)

    def test_health_includes_offline_fields(self):
        env = os.environ.copy()
        buf = StringIO()
        try:
            os.environ.pop("XAI_API_KEY", None)
            with redirect_stdout(buf):
                code = main(["-r", str(Path(__file__).resolve().parents[1]), "health"])
        finally:
            os.environ.clear()
            os.environ.update(env)
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        for key in ("offline_ready", "gguf_present", "network_mode", "runner", "airgap"):
            self.assertIn(key, data)
        self.assertEqual(data["provider"], "local")
        self.assertFalse(data["bills_xai"])
        self.assertIn(data["network_mode"], {"local", "airgap"})
        self.assertIn(data["runner"], {"ollama", "llama_cpp", "none"})


if __name__ == "__main__":
    unittest.main()
