import tempfile
import unittest
from pathlib import Path

from engine.config import Settings
from engine.tools import ToolBox


def _settings(root: Path, autonomy: int = 3) -> Settings:
    return Settings(
        root=root,
        autonomy=autonomy,
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


class ToolScopeTests(unittest.TestCase):
    def test_list_dir_works_when_root_has_symlink_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            box = ToolBox(_settings(root), confirmer=lambda *a, **k: False)
            out = box.execute("list_dir", {"path": "."})
            self.assertIn("a.py", out)

    def test_read_outside_root_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            box = ToolBox(_settings(root), confirmer=lambda *a, **k: False)
            out = box.execute("read_file", {"path": "/etc/hosts"})
            self.assertTrue(out.startswith("ERROR:"))
            self.assertIn("escapes project root", out)


if __name__ == "__main__":
    unittest.main()
