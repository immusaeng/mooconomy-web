import os
import sys
import unittest

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from translate_ko import translate_title, apply_ko_titles, is_already_korean, load_glossary  # noqa: E402


class TestTranslateKo(unittest.TestCase):
    def test_glossary_lookup_hit(self):
        gloss = {"Consumer Price Index": "소비자물가지수(CPI)"}
        titleKo, ok = translate_title("Consumer Price Index", "FRED", gloss)
        self.assertEqual(titleKo, "소비자물가지수(CPI)")
        self.assertTrue(ok)

    def test_glossary_miss_falls_back_to_original_not_blank(self):
        titleKo, ok = translate_title("Some Unknown Series", "FRED", {})
        self.assertEqual(titleKo, "Some Unknown Series")
        self.assertFalse(ok)

    def test_already_korean_source_bypasses_glossary(self):
        titleKo, ok = translate_title("2026년 기업경영분석", "BOK", {})
        self.assertEqual(titleKo, "2026년 기업경영분석")
        self.assertTrue(ok)

    def test_is_already_korean(self):
        self.assertTrue(is_already_korean("소비자물가지수"))
        self.assertFalse(is_already_korean("Consumer Price Index"))

    def test_apply_ko_titles_never_blanks_a_title(self):
        events = [
            {"originalTitle": "Consumer Price Index", "sourceName": "FRED"},
            {"originalTitle": "Totally Unknown Thing", "sourceName": "FRED"},
        ]
        gloss = {"Consumer Price Index": "소비자물가지수(CPI)"}
        stats = apply_ko_titles(events, glossary=gloss)
        self.assertEqual(events[0]["titleKo"], "소비자물가지수(CPI)")
        self.assertEqual(events[1]["titleKo"], "Totally Unknown Thing")
        self.assertEqual(stats["translated_count"], 1)
        self.assertEqual(stats["untranslated_count"], 1)

    def test_real_glossary_file_loads_and_is_nonempty(self):
        gloss = load_glossary()
        self.assertGreater(len(gloss), 100)
        self.assertIn("Consumer Price Index", gloss)


if __name__ == "__main__":
    unittest.main()
