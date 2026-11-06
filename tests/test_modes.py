"""Drive real prompt/mode/identity surfaces for coding vs generative/creative."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.config import Settings
from engine.constitution import identity, load_constitution, load_prompt
from engine.prompt_build import (
    CORE,
    CREATE_ADDON,
    CODE_ADDON,
    build_system,
    mode_profile,
    mode_skips_code_explore,
    resolve_mode,
)
from engine.tools import CREATE_TOOLS, tool_names_for, tool_schemas


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
        max_steps=8,
        shell_timeout=10,
        allow_secrets=False,
    )


class ModeRoutingTests(unittest.TestCase):
    def test_resolve_mode_explicit_and_cues(self):
        self.assertEqual(resolve_mode("anything", "create"), "create")
        self.assertEqual(resolve_mode("anything", "creative"), "create")
        self.assertEqual(resolve_mode("anything", "generative"), "create")
        self.assertEqual(resolve_mode("anything", "code"), "code")
        self.assertEqual(resolve_mode("write a short myth about rivers"), "create")
        self.assertEqual(resolve_mode("brainstorm product names for a weather app"), "create")
        self.assertEqual(resolve_mode("add unit tests for the CLI"), "code")
        self.assertEqual(resolve_mode("fix the health endpoint"), "code")

    def test_coding_and_create_prompts_and_tools_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            settings = _settings(root)
            code_prompt = build_system(settings, mode="code")
            create_prompt = build_system(settings, mode="create")
            chat_prompt = build_system(settings, mode="chat")

        self.assertNotEqual(code_prompt, create_prompt)
        self.assertNotEqual(code_prompt, chat_prompt)
        self.assertIn("Mode: coding", code_prompt)
        self.assertIn("Mode: generative / creative", create_prompt)
        self.assertIn("NO CHARGES", code_prompt)
        self.assertIn("NO CHARGES", create_prompt)
        self.assertIn("coding", CORE.lower())
        self.assertIn("generative", CORE.lower())
        self.assertIn("creative", CORE.lower())
        self.assertIn("explore", CODE_ADDON.lower())
        self.assertIn("do not start a code-explore", CREATE_ADDON.lower())
        self.assertIn("plan cycle", CREATE_ADDON.lower())

        code_tools = set(tool_names_for("code"))
        create_tools = set(tool_names_for("create"))
        chat_tools = set(tool_names_for("chat"))
        self.assertNotEqual(code_tools, create_tools)
        self.assertGreater(len(code_tools), len(create_tools))
        self.assertIn("retrieve", code_tools)
        self.assertIn("plan_task", code_tools)
        self.assertIn("run_tests", code_tools)
        self.assertNotIn("retrieve", create_tools)
        self.assertNotIn("plan_task", create_tools)
        self.assertNotIn("run_tests", create_tools)
        self.assertEqual(create_tools, CREATE_TOOLS)
        self.assertTrue(mode_skips_code_explore("create"))
        self.assertTrue(mode_skips_code_explore("chat"))
        self.assertFalse(mode_skips_code_explore("code"))

        code_profile = mode_profile("code")
        create_profile = mode_profile("create")
        self.assertTrue(code_profile["plans"])
        self.assertTrue(code_profile["indexes"])
        self.assertFalse(create_profile["plans"])
        self.assertFalse(create_profile["indexes"])
        self.assertTrue(create_profile["skips_code_explore"])
        self.assertNotEqual(code_profile["addon"], create_profile["addon"])
        self.assertNotEqual(set(code_profile["tools"]), set(create_profile["tools"]))

        # Schema lists stay distinct too (real tool_schemas entry point).
        code_schema_names = {t["function"]["name"] for t in tool_schemas(mode="code")}
        create_schema_names = {t["function"]["name"] for t in tool_schemas(mode="create")}
        self.assertEqual(code_schema_names, code_tools)
        self.assertEqual(create_schema_names, create_tools)
        self.assertIn("remember_preference", chat_tools)


class CreateCliEntryTests(unittest.TestCase):
    def test_agent_normalize_keeps_create_command(self):
        import agent as agent_entry

        self.assertIn("create", agent_entry.COMMANDS)
        self.assertEqual(agent_entry._normalize(["create", "write a myth"]), ["create", "write a myth"])
        self.assertEqual(agent_entry._normalize(["run", "--mode", "create", "hi"]), ["run", "--mode", "create", "hi"])

    def test_create_run_skips_forced_plan_cycle(self):
        from engine.agent import run_task

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            settings = _settings(root)
            result = run_task("write a short myth about rivers", settings=settings, mode="create")
        self.assertEqual(result.plan.get("source"), "create")
        self.assertEqual(result.plan.get("subgoals"), [])
        mode_events = [e for e in result.events if e.get("type") == "mode"]
        self.assertTrue(mode_events)
        self.assertEqual(mode_events[0]["data"]["mode"], "create")
        self.assertFalse(any(e.get("type") == "index" for e in result.events))


class IdentitySurfaceTests(unittest.TestCase):
    def test_manifest_and_docs_cover_general_objectives_and_no_charges(self):
        ident = identity()
        self.assertEqual(ident["name"], "mythos")
        role = ident["role"].lower()
        self.assertIn("coding", role)
        self.assertIn("generative", role)
        self.assertIn("creative", role)
        self.assertTrue("no charges" in role or "local" in role)
        objectives = [str(x).lower() for x in (ident.get("objective") or [])]
        for term in ("coding", "generative", "creative"):
            self.assertIn(term, objectives)
        modes = ident.get("modes") or []
        self.assertIn("code", modes)
        self.assertIn("create", modes)
        self.assertIn("chat", modes)

        constitution = load_constitution().lower()
        prompt = load_prompt().lower()
        for blob in (constitution, prompt, CORE.lower()):
            self.assertIn("coding", blob)
            self.assertTrue("generative" in blob or "creative" in blob)
            self.assertTrue("no charges" in blob or "never call api.x.ai" in blob or "local ollama" in blob)


if __name__ == "__main__":
    unittest.main()
