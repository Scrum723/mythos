import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from engine.cli import main


class HealthTests(unittest.TestCase):
    def test_health_is_coding_not_other_projects(self):
        env = os.environ.copy()
        os.environ["CODING_AUTONOMY"] = "3"
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
        self.assertEqual(data["service"], "coding")
        self.assertTrue(data["service"])
        self.assertEqual(data["autonomy"], 3)
        self.assertEqual(data["provider"], "local")
        self.assertFalse(data["bills_xai"])
        self.assertNotIn("griffty", data["role"].lower())
        self.assertNotIn("wfad", data["role"].lower())


if __name__ == "__main__":
    unittest.main()
