import os
import sys
import unittest

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from security import mask_secret, strip_query_secrets, scan_text_for_secrets  # noqa: E402


class TestSecurity(unittest.TestCase):
    def test_mask_secret_hides_middle(self):
        masked = mask_secret("sk_live_abcdef123456")
        self.assertNotIn("abcdef123456", masked)
        self.assertTrue(masked.startswith("sk"))

    def test_mask_secret_handles_short_values(self):
        self.assertEqual(mask_secret("abc"), "***")

    def test_mask_secret_handles_empty(self):
        self.assertEqual(mask_secret(None), "(unset)")
        self.assertEqual(mask_secret(""), "(unset)")

    def test_strip_query_secrets_removes_api_key(self):
        url = "https://api.example.com/data?api_key=SUPERSECRET123&from=2026-01-01"
        cleaned = strip_query_secrets(url)
        self.assertNotIn("SUPERSECRET123", cleaned)
        self.assertIn("from=2026-01-01", cleaned)

    def test_strip_query_secrets_handles_token_and_apikey_variants(self):
        for param in ("token", "apikey", "secret", "key"):
            url = f"https://x.com/y?{param}=VALUE123"
            self.assertNotIn("VALUE123", strip_query_secrets(url))

    def test_strip_query_secrets_noop_on_clean_url(self):
        url = "https://x.com/y?from=2026-01-01&to=2026-02-01"
        self.assertEqual(strip_query_secrets(url), url)

    def test_scan_text_for_secrets_finds_known_value(self):
        secret = "abcd1234efgh5678"
        text = f"debug: using key {secret} for request"
        hits = scan_text_for_secrets(text, known_secrets=[secret])
        self.assertTrue(any(reason == "known_secret_value" for _, reason in hits))

    def test_scan_text_for_secrets_finds_pattern(self):
        text = 'API_KEY = "abcdefghijklmnop1234"'
        hits = scan_text_for_secrets(text)
        self.assertTrue(any(reason == "secret_like_pattern" for _, reason in hits))

    def test_scan_text_for_secrets_clean_text_no_hits(self):
        text = "this is a normal comment about the weather"
        self.assertEqual(scan_text_for_secrets(text), [])


if __name__ == "__main__":
    unittest.main()
