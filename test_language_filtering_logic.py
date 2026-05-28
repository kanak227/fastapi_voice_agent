"""
Simple script to verify the language filtering logic works correctly.
This tests the core filtering logic without requiring the full app context.
"""


def filter_voices_by_language(voices, language):
    """
    Filter voices by language base code.
    
    Args:
        voices: List of voice dicts with 'locale' field
        language: Language code (e.g., 'en-US', 'hi', 'fr-FR')
    
    Returns:
        Filtered list of voices matching the language base code
    """
    if not language:
        return voices
    
    lang_base = language.split("-")[0].lower()
    filtered = [
        v for v in voices
        if v.get("locale") and v["locale"].split("-")[0].lower() == lang_base
    ]
    return filtered


def test_language_filtering():
    """Test the language filtering logic."""
    
    # Mock voice data
    voices = [
        {"name": "Rachel", "voice_id": "1", "locale": "en-US", "provider": "elevenlabs"},
        {"name": "Domi", "voice_id": "2", "locale": "en-GB", "provider": "elevenlabs"},
        {"name": "Priya", "voice_id": "3", "locale": "hi-IN", "provider": "elevenlabs"},
        {"name": "Raj", "voice_id": "4", "locale": "hi-IN", "provider": "elevenlabs"},
        {"name": "Pierre", "voice_id": "5", "locale": "fr-FR", "provider": "elevenlabs"},
        {"name": "Maria", "voice_id": "6", "locale": "es-ES", "provider": "elevenlabs"},
    ]
    
    print("Testing language filtering logic...")
    print(f"Total voices: {len(voices)}\n")
    
    # Test 1: No language filter (should return all)
    result = filter_voices_by_language(voices, None)
    assert len(result) == 6, f"Expected 6 voices, got {len(result)}"
    print("✓ Test 1 passed: No filter returns all voices")
    
    # Test 2: Filter by English (en-US)
    result = filter_voices_by_language(voices, "en-US")
    assert len(result) == 2, f"Expected 2 English voices, got {len(result)}"
    assert all(v["locale"].startswith("en") for v in result)
    print("✓ Test 2 passed: Filter by 'en-US' returns 2 English voices")
    
    # Test 3: Filter by English (en)
    result = filter_voices_by_language(voices, "en")
    assert len(result) == 2, f"Expected 2 English voices, got {len(result)}"
    print("✓ Test 3 passed: Filter by 'en' returns 2 English voices")
    
    # Test 4: Filter by Hindi
    result = filter_voices_by_language(voices, "hi")
    assert len(result) == 2, f"Expected 2 Hindi voices, got {len(result)}"
    assert all(v["locale"].startswith("hi") for v in result)
    print("✓ Test 4 passed: Filter by 'hi' returns 2 Hindi voices")
    
    # Test 5: Filter by French
    result = filter_voices_by_language(voices, "fr-FR")
    assert len(result) == 1, f"Expected 1 French voice, got {len(result)}"
    assert result[0]["name"] == "Pierre"
    print("✓ Test 5 passed: Filter by 'fr-FR' returns 1 French voice")
    
    # Test 6: Filter by Spanish
    result = filter_voices_by_language(voices, "es")
    assert len(result) == 1, f"Expected 1 Spanish voice, got {len(result)}"
    assert result[0]["name"] == "Maria"
    print("✓ Test 6 passed: Filter by 'es' returns 1 Spanish voice")
    
    # Test 7: Filter by non-existent language
    result = filter_voices_by_language(voices, "de")
    assert len(result) == 0, f"Expected 0 German voices, got {len(result)}"
    print("✓ Test 7 passed: Filter by 'de' returns 0 voices")
    
    # Test 8: Empty language string (should return all)
    result = filter_voices_by_language(voices, "")
    assert len(result) == 6, f"Expected 6 voices, got {len(result)}"
    print("✓ Test 8 passed: Empty string returns all voices")
    
    # Test 9: Voice without locale (should be filtered out)
    voices_with_missing = voices + [{"name": "NoLocale", "voice_id": "7", "provider": "test"}]
    result = filter_voices_by_language(voices_with_missing, "en")
    assert len(result) == 2, f"Expected 2 voices, got {len(result)}"
    print("✓ Test 9 passed: Voices without locale are filtered out")
    
    print("\n✅ All tests passed! Language filtering logic is correct.")


if __name__ == "__main__":
    test_language_filtering()
