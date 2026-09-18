import unittest
import io
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.whatsapp_parser import (
    parse_whatsapp_text,
    parse_whatsapp_file,
    convert_to_fine_tuning
)

class TestWhatsAppParser(unittest.TestCase):
    def test_ios_format(self):
        sample_ios = """
\u200e[12/03/24, 14:15:20] I messaggi e le chiamate sono crittografati end-to-end.
\u200e[12/03/24, 14:16:00] Alberto Robazza: Ciao Eugenio, hai visto cosa dicono di WhatsApp?
\u200e[12/03/24, 14:16:30] Eugenio: Sì, che tolgono la crittografia per fare fine tuning.
Ma tanto noi lo facciamo in locale con Mimo.
\u200e[12/03/24, 14:17:00] Alberto Robazza: Esatto, piano perfetto!
\u200e[12/03/24, 14:17:15] Eugenio: <allegato: audio.opus omesso>
"""
        turns, stats = parse_whatsapp_text(sample_ios)
        self.assertEqual(len(turns), 3)
        self.assertIn("Alberto Robazza", stats)
        self.assertIn("Eugenio", stats)
        # Verifica multi-line
        self.assertIn("Ma tanto noi lo facciamo in locale", turns[1]["text"])

    def test_android_format(self):
        sample_android = """
12/03/2024, 14:15 - I messaggi e le chiamate sono crittografati end-to-end.
12/03/2024, 14:16 - Mario: Ci vediamo alle 15 per la riunione?
12/03/2024, 14:18 - Eugenio: Arrivo tra dieci minuti, sto finendo di compilare l'app.
12/03/2024, 14:19 - Mario: Perfetto, a dopo.
"""
        turns, stats = parse_whatsapp_text(sample_android)
        self.assertEqual(len(turns), 3)
        self.assertEqual(turns[0]["speaker"], "Mario")
        self.assertEqual(turns[1]["speaker"], "Eugenio")
        self.assertEqual(turns[2]["speaker"], "Mario")

    def test_ampm_format(self):
        sample_ampm = """
[1/15/24, 2:30:15 PM] Alice: Hey there!
[1/15/24, 2:31:00 PM] Bob: Hi Alice, testing 12-hour format.
"""
        turns, stats = parse_whatsapp_text(sample_ampm)
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0]["speaker"], "Alice")
        self.assertEqual(turns[1]["speaker"], "Bob")

    def test_zip_support(self):
        # Crea un file ZIP finto in memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("_chat.txt", "[10/05/24, 10:00:00] Marco: Test zip export\n[10/05/24, 10:01:00] Eugenio: Funziona alla perfezione!")
        zip_buffer.seek(0)

        tmp_zip = ROOT / "data" / "test_export.zip"
        tmp_zip.write_bytes(zip_buffer.getvalue())

        try:
            turns, stats = parse_whatsapp_file(tmp_zip)
            self.assertEqual(len(turns), 2)
            self.assertEqual(turns[0]["speaker"], "Marco")
            self.assertEqual(turns[1]["speaker"], "Eugenio")
        finally:
            if tmp_zip.exists():
                tmp_zip.unlink()

    def test_convert_to_fine_tuning(self):
        turns = [
            {"speaker": "Alberto", "text": "Domanda 1"},
            {"speaker": "Eugenio", "text": "Risposta 1"},
            {"speaker": "Alberto", "text": "Domanda 2"},
            {"speaker": "Eugenio", "text": "Risposta 2"}
        ]
        samples = convert_to_fine_tuning(turns, "Eugenio")
        self.assertEqual(len(samples), 2)
        self.assertEqual(samples[0]["messages"][-1]["content"], "Risposta 1")
        self.assertEqual(samples[1]["messages"][-1]["content"], "Risposta 2")

if __name__ == "__main__":
    unittest.main()
