import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from engine.cli import main
from engine.languages import detect


class DetectTests(unittest.TestCase):
    def test_detect_nested_python_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "install.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
            eng = root / "engine"
            eng.mkdir()
            (eng / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (eng / "util.py").write_text("x = 1\n", encoding="utf-8")
            result = detect(root)
            self.assertEqual(result["primary"], "python")
            self.assertIn("python", result["scores"])
            self.assertIn("supported", result)
            self.assertIn("idiom", result)
            self.assertIsInstance(result["supported"], list)

    def test_detect_cli_structured(self):
        root = Path(__file__).resolve().parents[1]
        buf = StringIO()
        with redirect_stdout(buf):
            code = main(["-r", str(root), "detect"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["primary"], "python")
        self.assertIn("scores", data)
        self.assertIn("idiom", data)
        self.assertIn("python", data["supported"])


if __name__ == "__main__":
    unittest.main()
