"""Offline / airgap / loopback policy for Mythos standalone inference."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
