"""Test voice catalog expansion and language filtering.

This test verifies Task 8 requirements:
- VOICE_CATALOG includes language metadata for existing voices
- VOICE_CATALOG includes MMS single-speaker voices for 11 languages
- /v1/voices endpoint filters by language when requested
- /v1/voices endpoint returns all voices when no language specified (backward compatible)
"""

import sys
import unittest
from unittest.mock import Mock, patch

# Add current directory to path to import server module
sys.path.insert(0, '.')


class TestVoiceCatalog(unittest.TestCase):
    """Test voice catalog expansion and language filtering."""

    def setUp(self):
        """Set up test fixtures."""
        # Import server module
        import server
        self.server = server
        self.VOICE_CATALOG = server.VOICE_CATALOG

    def test_serena_has_language_metadata(self):
        """Test that Serena voice has languages field with 10 languages."""
        serena = next((v for v in self.VOICE_CATALOG if v["voice_id"] == "serena"), None)
        self.assertIsNotNone(serena, "Serena voice not found in catalog")
        self.assertIn("languages", serena, "Serena missing languages field")
        expected_langs = ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]
        self.assertEqual(serena["languages"], expected_langs, "Serena languages incorrect")

    def test_ethan_has_language_metadata(self):
        """Test that Ethan voice has languages field with 10 languages."""
        ethan = next((v for v in self.VOICE_CATALOG if v["voice_id"] == "ethan"), None)
        self.assertIsNotNone(ethan, "Ethan voice not found in catalog")
        self.assertIn("languages", ethan, "Ethan missing languages field")
        expected_langs = ["en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"]
        self.assertEqual(ethan["languages"], expected_langs, "Ethan languages incorrect")

    def test_mms_voices_present(self):
        """Test that all 11 MMS single-speaker voices are present."""
        expected_mms_voices = [
            ("mms-hindi", "Hindi (MMS)", "hindi", ["hi"]),
            ("mms-tamil", "Tamil (MMS)", "tamil", ["ta"]),
            ("mms-telugu", "Telugu (MMS)", "telugu", ["te"]),
            ("mms-marathi", "Marathi (MMS)", "marathi", ["mr"]),
            ("mms-bengali", "Bengali (MMS)", "bengali", ["bn"]),
            ("mms-gujarati", "Gujarati (MMS)", "gujarati", ["gu"]),
            ("mms-kannada", "Kannada (MMS)", "kannada", ["kn"]),
            ("mms-malayalam", "Malayalam (MMS)", "malayalam", ["ml"]),
            ("mms-punjabi", "Punjabi (MMS)", "punjabi", ["pa"]),
            ("mms-urdu", "Urdu (MMS)", "urdu", ["ur"]),
            ("mms-arabic", "Arabic (MMS)", "arabic", ["ar"]),
        ]

        for voice_id, name, accent, languages in expected_mms_voices:
            with self.subTest(voice_id=voice_id):
                voice = next((v for v in self.VOICE_CATALOG if v["voice_id"] == voice_id), None)
                self.assertIsNotNone(voice, f"{voice_id} not found in catalog")
                self.assertEqual(voice["name"], name, f"{voice_id} name incorrect")
                self.assertEqual(voice["labels"]["gender"], "neutral", f"{voice_id} gender incorrect")
                self.assertEqual(voice["labels"]["accent"], accent, f"{voice_id} accent incorrect")
                self.assertEqual(voice["languages"], languages, f"{voice_id} languages incorrect")

    def test_total_voice_count(self):
        """Test that catalog has exactly 13 voices (2 Qwen + 11 MMS)."""
        self.assertEqual(len(self.VOICE_CATALOG), 13, "Voice catalog should have 13 voices")

    def test_list_voices_without_language_returns_all(self):
        """Test that /v1/voices without language param returns all voices (backward compatible)."""
        from fastapi.testclient import TestClient
        from server import app

        client = TestClient(app)
        response = client.get("/v1/voices")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("voices", data)
        self.assertEqual(len(data["voices"]), 13, "Should return all 13 voices")

    def test_list_voices_filter_by_hindi(self):
        """Test that /v1/voices?language=hi returns only Hindi-supporting voices."""
        from fastapi.testclient import TestClient
        from server import app

        client = TestClient(app)
        response = client.get("/v1/voices?language=hi")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("voices", data)
        
        # Should return only mms-hindi
        self.assertEqual(len(data["voices"]), 1, "Should return 1 Hindi voice")
        self.assertEqual(data["voices"][0]["voice_id"], "mms-hindi")

    def test_list_voices_filter_by_english(self):
        """Test that /v1/voices?language=en returns English-supporting voices."""
        from fastapi.testclient import TestClient
        from server import app

        client = TestClient(app)
        response = client.get("/v1/voices?language=en")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("voices", data)
        
        # Should return Serena and Ethan (both support English)
        self.assertEqual(len(data["voices"]), 2, "Should return 2 English voices")
        voice_ids = {v["voice_id"] for v in data["voices"]}
        self.assertEqual(voice_ids, {"serena", "ethan"})

    def test_list_voices_filter_by_tamil(self):
        """Test that /v1/voices?language=ta returns only Tamil-supporting voices."""
        from fastapi.testclient import TestClient
        from server import app

        client = TestClient(app)
        response = client.get("/v1/voices?language=ta")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("voices", data)
        
        # Should return only mms-tamil
        self.assertEqual(len(data["voices"]), 1, "Should return 1 Tamil voice")
        self.assertEqual(data["voices"][0]["voice_id"], "mms-tamil")

    def test_list_voices_filter_with_region_code(self):
        """Test that /v1/voices?language=en-US filters by base code 'en'."""
        from fastapi.testclient import TestClient
        from server import app

        client = TestClient(app)
        response = client.get("/v1/voices?language=en-US")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("voices", data)
        
        # Should return Serena and Ethan (both support English)
        self.assertEqual(len(data["voices"]), 2, "Should return 2 English voices")
        voice_ids = {v["voice_id"] for v in data["voices"]}
        self.assertEqual(voice_ids, {"serena", "ethan"})

    def test_list_voices_filter_unsupported_language(self):
        """Test that /v1/voices?language=xyz returns empty list for unsupported language."""
        from fastapi.testclient import TestClient
        from server import app

        client = TestClient(app)
        response = client.get("/v1/voices?language=xyz")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("voices", data)
        self.assertEqual(len(data["voices"]), 0, "Should return empty list for unsupported language")


if __name__ == '__main__':
    unittest.main()
