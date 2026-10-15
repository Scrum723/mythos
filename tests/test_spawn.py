import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from engine.spawn import spawn


class SpawnTests(unittest.TestCase):
    def test_spawn_writes_standalone_local_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "demo-agent"
            result = spawn(
                name="demo-agent",
                role="Test role",
                prompt="Do the work.",
                tools="list_dir,read_file",
                constraints="Stay in root.",
                dest=dest,
            )
            self.assertEqual(result["name"], "demo-agent")
            self.assertTrue((dest / "agent.py").is_file())
            self.assertTrue((dest / "engine" / "cli.py").is_file())
            self.assertTrue((dest / "engine" / "config.py").is_file())
            self.assertTrue((dest / "web" / "index.html").is_file())
            self.assertTrue((dest / "Dockerfile").is_file())
            self.assertTrue((dest / "manifest.json").is_file())

            env_example = (dest / ".env.example").read_text(encoding="utf-8")
            self.assertIn("CODING_PROVIDER=local", env_example)
            self.assertIn("11434", env_example)
            self.assertIn("NO CHARGES", env_example)
            self.assertNotIn("CODING_MODEL=grok", env_example)

            readme = (dest / "README.md").read_text(encoding="utf-8")
            self.assertIn("local Ollama", readme)
            self.assertNotIn("add XAI_API_KEY for the LLM loop", readme)

            dockerfile = (dest / "Dockerfile").read_text(encoding="utf-8")
            self.assertIn("CODING_PROVIDER=local", dockerfile)

            agent_py = (dest / "agent.py").read_text(encoding="utf-8")
            self.assertIn('"setup"', agent_py)
            self.assertIn('"bench"', agent_py)

            env = os.environ.copy()
            env.pop("CODING_PROVIDER", None)
            env.pop("XAI_API_KEY", None)
            env["CODING_ALLOW_XAI"] = ""
            proc = subprocess.run(
                ["python3", str(dest / "agent.py"), "health"],
                cwd=str(dest),
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["provider"], "local")
            self.assertFalse(data["bills_xai"])
            self.assertTrue(data.get("service"))


if __name__ == "__main__":
    unittest.main()
