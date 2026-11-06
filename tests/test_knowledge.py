"""Local Mythos knowledge library: coding langs, spoken langs, defense."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from engine.cli import main
from engine.defense import local_threat_posture, scan_exterior_risks
from engine.knowledge import (
    coding_languages,
    knowledge_snapshot,
    mcp_catalog,
    spoken_language_count,
    spoken_languages,
    synthesize_capabilities,
)
from engine.languages import detect


REQUIRED_CODING = {
    "python",
    "html",
    "javascript",
    "css",
    "java",
    "c",
    "cpp",
    "cobol",
    "r",
    "matlab",
}


class CodingLanguageExpansionTests(unittest.TestCase):
    def test_supported_includes_requested_stack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print(1)\n", encoding="utf-8")
            result = detect(root)
        supported = set(result["supported"])
        missing = REQUIRED_CODING - supported
        self.assertFalse(missing, msg=f"missing coding langs: {sorted(missing)}")

    def test_detect_c_vs_cpp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.c").write_text("int main(){return 0;}\n", encoding="utf-8")
            (root / "util.c").write_text("int x;\n", encoding="utf-8")
            result = detect(root)
        self.assertEqual(result["primary"], "c")

    def test_detect_cobol_r_matlab_html_css(self):
        cases = [
            ("PROG.CBL", "       IDENTIFICATION DIVISION.\n", "cobol"),
            ("analysis.R", "x <- 1\n", "r"),
            ("sim.m", "x = 1;\n", "matlab"),
            ("index.html", "<html></html>\n", "html"),
            ("app.css", "body{color:red}\n", "css"),
        ]
        for name, body, expected in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    (root / name).write_text(body, encoding="utf-8")
                    result = detect(root)
                self.assertEqual(result["primary"], expected)

    def test_knowledge_coding_catalog_covers_required(self):
        langs = {row["id"] for row in coding_languages()}
        missing = REQUIRED_CODING - langs
        self.assertFalse(missing, msg=f"knowledge missing: {sorted(missing)}")


class SpokenLanguageLibraryTests(unittest.TestCase):
    def test_spoken_catalog_is_planet_scale(self):
        # ISO 639-1 has 180+; we require a full living catalog (>= 150 named languages).
        self.assertGreaterEqual(spoken_language_count(), 150)
        names = {row["name"].lower() for row in spoken_languages()}
        for must in ("english", "spanish", "mandarin chinese", "hindi", "arabic", "swahili", "french"):
            self.assertTrue(any(must in n for n in names), msg=must)

    def test_knowledge_snapshot_exposes_spoken_and_coding(self):
        snap = knowledge_snapshot()
        self.assertIn("coding", snap)
        self.assertIn("spoken", snap)
        self.assertIn("capabilities", snap)
        self.assertIn("defense", snap)
        self.assertGreaterEqual(snap["spoken"]["count"], 150)
        self.assertTrue(set(REQUIRED_CODING).issubset(set(snap["coding"]["ids"])))


class DefenseAndSynthesisTests(unittest.TestCase):
    def test_synthesize_capabilities_combines_domains(self):
        caps = synthesize_capabilities()
        text = json.dumps(caps).lower()
        for term in ("coding", "generative", "creative", "local", "defense", "no charges"):
            self.assertIn(term, text)

    def test_local_threat_posture_is_airgappable(self):
        posture = local_threat_posture()
        self.assertTrue(posture["local_only"])
        self.assertFalse(posture["allows_remote_llm"])
        self.assertIn("controls", posture)
        self.assertGreaterEqual(len(posture["controls"]), 5)

    def test_scan_exterior_risks_flags_remote_base(self):
        risks = scan_exterior_risks(api_base="https://evil.example/v1", airgap=True)
        self.assertTrue(any(r.get("severity") in {"high", "critical"} for r in risks))

    def test_knowledge_cli(self):
        buf = StringIO()
        with redirect_stdout(buf):
            code = main(["-r", str(Path(__file__).resolve().parents[1]), "knowledge"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertGreaterEqual(data["spoken"]["count"], 150)
        self.assertIn("python", data["coding"]["ids"])
        self.assertIn("mcp", data)
        self.assertGreaterEqual(data["mcp"]["scraped_count"], 300)

    def test_mcp_catalog_from_github_mcp_pages(self):
        cat = mcp_catalog()
        self.assertEqual(cat["source"], "https://github.com/mcp")
        self.assertGreaterEqual(cat["scraped_count"], 300)
        self.assertGreaterEqual(cat["relevant_count"], 30)
        self.assertTrue(any(s.get("page") == 1 for s in cat["servers"]))
        self.assertTrue(any(s.get("page") == 10 for s in cat["servers"]))
        policy = cat["install_policy"].lower()
        self.assertTrue("catalog" in policy and "install" in policy)


if __name__ == "__main__":
    unittest.main()
