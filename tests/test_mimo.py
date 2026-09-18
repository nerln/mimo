import unittest
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.extract_turns import clean_text, generate_speaker_datasets
from engine.ollama_adapter import build_modelfile, pick_few_shot_turns

class TestMimoEngine(unittest.TestCase):
    def test_clean_text(self):
        self.assertEqual(clean_text("   ciao    mondo \n\n "), "ciao mondo")

    def test_generate_speaker_datasets(self):
        mock_convs = [
            {
                "job_id": "test_conv",
                "turns": [
                    {"speaker": "Alberto", "text": "Ma secondo te Muse Spark ci copia?"},
                    {"speaker": "Eugenio", "text": "Boh, probabilmente solo se gli dai i dati in pasto."},
                    {"speaker": "Alberto", "text": "E se facessimo noi un clone?"},
                    {"speaker": "Eugenio", "text": "Allora sì, lo addestriamo su Apple Silicon e fine della storia."}
                ]
            }
        ]
        samples = generate_speaker_datasets(mock_convs, target_speaker="Eugenio")
        self.assertEqual(len(samples), 2)
        self.assertEqual(samples[0]["messages"][-1]["content"], "Boh, probabilmente solo se gli dai i dati in pasto.")
        self.assertEqual(samples[1]["messages"][-1]["content"], "Allora sì, lo addestriamo su Apple Silicon e fine della storia.")

    def test_build_modelfile(self):
        few_shots = [
            {"user": "Che ne pensi?", "assistant": "Penso sia un'ottima idea."}
        ]
        content = build_modelfile("Eugenio", "qwen3:4b-instruct-2507-q4_K_M", few_shots)
        self.assertIn("FROM qwen3:4b-instruct-2507-q4_K_M", content)
        self.assertIn("Sei Eugenio Nerelli", content)
        self.assertIn('MESSAGE user """Che ne pensi?"""', content)
        self.assertIn('MESSAGE assistant """Penso sia un\'ottima idea."""', content)

    def test_summary_exists(self):
        summary_path = ROOT / "data" / "summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                data = json.load(f)
            self.assertIn("stats", data)
            self.assertIn("prominent_speakers", data)

if __name__ == "__main__":
    unittest.main()
