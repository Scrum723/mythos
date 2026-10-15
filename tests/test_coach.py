import json
import tempfile
import unittest
from pathlib import Path

from engine.coach import TargetError, resolve_target, scan


class CoachTests(unittest.TestCase):
    def test_refuses_home(self):
        with self.assertRaises(TargetError):
            resolve_target(str(Path.home()))

    def test_rejects_placeholder(self):
        with self.assertRaises(TargetError) as ctx:
            resolve_target("/path/to/other-agent")
        self.assertIn("placeholder", str(ctx.exception))

    def test_scan_fixture_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "sample-agent"
            root.mkdir()
            (root / "README.md").write_text("# sample\nrun python3 agent.py\n", encoding="utf-8")
            (root / "agent.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "CONSTITUTION.md").write_text("be honest\n", encoding="utf-8")
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            (root / ".env.example").write_text("XAI_API_KEY=\n", encoding="utf-8")
            (root / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_ok.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            report = scan(root)
            ids = {c["id"]: c["ok"] for c in report["checks"]}
            self.assertTrue(ids["readme"])
            self.assertTrue(ids["tests"])
            self.assertTrue(ids["gitignore_env"])
            self.assertTrue(ids["independent"])
            self.assertEqual(report["fails"], 0)

    def test_flags_hardcoded_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "leaky"
            root.mkdir()
            leaky = "API" + "_KEY = " + repr("sk-demo-not-real")
            (root / "agent.py").write_text(leaky + "\n", encoding="utf-8")
            report = scan(root)
            secret = next(c for c in report["checks"] if c["id"] == "no_hardcoded_secrets")
            self.assertFalse(secret["ok"])


class CliImproveTests(unittest.TestCase):
    def test_improve_scan_cli(self):
        import io
        from contextlib import redirect_stdout

        from engine.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "other"
            root.mkdir()
            (root / "README.md").write_text("x\n", encoding="utf-8")
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["improve", str(root)])
            data = json.loads(buf.getvalue())
            self.assertEqual(data["name"], "other")
            self.assertIn("checks", data)
            self.assertIn(code, {0, 1})


if __name__ == "__main__":
    unittest.main()
