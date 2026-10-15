import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from engine.config import Settings
from engine.llm import _parse_text_tools


class ProviderTests(unittest.TestCase):
    def test_xai_provider_forced_local_without_allow_flag(self):
        env = os.environ.copy()
        os.environ["CODING_PROVIDER"] = "xai"
        os.environ["XAI_API_KEY"] = "blocked-" + "test-key-not-used"
        os.environ["CODING_ALLOW_XAI"] = "1"
        try:
            settings = Settings.load(root=".", autonomy=3)
        finally:
            os.environ.clear()
            os.environ.update(env)
        self.assertEqual(settings.provider, "local")
        self.assertFalse(settings.uses_xai)
        self.assertEqual(settings.api_key, "")
        self.assertIn("11434", settings.api_base)
        self.assertNotIn("api.x.ai", settings.api_base)

    def test_default_is_local_not_xai(self):
        env = os.environ.copy()
        os.environ.pop("XAI_API_KEY", None)
        os.environ.pop("CODING_PROVIDER", None)
        os.environ.pop("CODING_MODEL", None)
        try:
            settings = Settings.load(root=".", autonomy=3)
        finally:
            os.environ.clear()
            os.environ.update(env)
        self.assertEqual(settings.provider, "local")
        self.assertFalse(settings.uses_xai)
        self.assertIn("11434", settings.api_base)

    def test_brains_catalog_is_git(self):
        from engine.setup_local import BRAINS

        spec = BRAINS["qwen2.5-coder:7b"]
        self.assertTrue(spec["git"].startswith("https://huggingface.co/"))
        self.assertTrue(spec["file"].endswith(".gguf"))

    def test_parse_text_tool_calls(self):
        raw = json.dumps({"tool_calls": [{"name": "list_dir", "arguments": {"path": "."}}]})
        parsed = _parse_text_tools(raw)
        self.assertEqual(parsed[0]["name"], "list_dir")

    def test_health_reports_not_billing_xai(self):
        from engine.cli import main

        env = os.environ.copy()
        os.environ.pop("XAI_API_KEY", None)
        buf = StringIO()
        try:
            with redirect_stdout(buf):
                code = main(["-r", str(Path(__file__).resolve().parents[1]), "health"])
        finally:
            os.environ.clear()
            os.environ.update(env)
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["provider"], "local")
        self.assertFalse(data["bills_xai"])

    def test_llm_chat_refuses_xai_path(self):
        from engine.config import Settings
        from engine.llm import LLMClient, LLMError

        unused = "blocked-" + "test-key-not-used"
        settings = Settings(
            root=Path("."),
            autonomy=3,
            provider="xai",
            model="grok-4.6",
            api_key=unused,
            api_base="https://api.x.ai/v1",
            host="127.0.0.1",
            port=8790,
            max_steps=8,
            shell_timeout=30,
            allow_secrets=False,
        )
        client = LLMClient(settings)
        with self.assertRaises(LLMError) as ctx:
            client.chat([{"role": "user", "content": "hi"}])
        self.assertIn("NO CHARGES", str(ctx.exception))

    def test_env_example_defaults_local(self):
        text = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
        self.assertIn("CODING_PROVIDER=local", text)
        self.assertIn("NO CHARGES", text)
        self.assertNotRegex(text, r"(?m)^XAI_API_KEY=.+")


if __name__ == "__main__":
    unittest.main()
