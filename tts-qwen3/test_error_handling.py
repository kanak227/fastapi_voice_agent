"""Test error handling for missing packages in TTS server.

This test verifies that _romanize() and _latn_to_devanagari() fail loudly
when required packages are not installed, as per Task 5 requirements.
"""

import sys
import unittest
from unittest.mock import Mock, patch
from fastapi import HTTPException


class TestPackageErrorHandling(unittest.TestCase):
    """Test that missing packages produce clear error messages."""

    def setUp(self):
        """Set up test fixtures."""
        # Import server module
        sys.path.insert(0, '.')
        
    def test_romanize_fails_loudly_when_uroman_missing(self):
        """Test that _romanize() raises HTTPException when uroman is not installed."""
        # Mock the app.state to simulate missing uroman package
        with patch('server.app') as mock_app:
            mock_app.state.uroman = False
            
            # Import the function after mocking
            from server import _romanize
            
            # Verify it raises HTTPException with correct message
            with self.assertRaises(HTTPException) as context:
                _romanize("سلام")
            
            self.assertEqual(context.exception.status_code, 500)
            self.assertIn("uroman package required", context.exception.detail)
    
    def test_latn_to_devanagari_fails_loudly_when_package_missing(self):
        """Test that _latn_to_devanagari() raises HTTPException when indic-transliteration is not installed."""
        # Mock the import to simulate missing package
        with patch.dict('sys.modules', {'indic_transliteration': None}):
            from server import _latn_to_devanagari
            
            # Verify it raises HTTPException with correct message
            with self.assertRaises(HTTPException) as context:
                _latn_to_devanagari("namaste")
            
            self.assertEqual(context.exception.status_code, 500)
            self.assertIn("indic-transliteration package required", context.exception.detail)


if __name__ == '__main__':
    unittest.main()
