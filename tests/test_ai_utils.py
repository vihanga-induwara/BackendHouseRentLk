import unittest
import sys
import os
import json

# Add Backend to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from utils.ai.safety_scorer import calculate_safety_score
    from utils.ai.spam_detector import detect_spam
    from utils.ai.market_intelligence import generate_price_comparison
    from utils.ai.nlp_search import parse_nlp_query
except ImportError:
    # Fallback if running from root
    sys.path.append(os.path.join(os.getcwd(), 'Backend'))
    from utils.ai.safety_scorer import calculate_safety_score
    from utils.ai.spam_detector import detect_spam
    from utils.ai.market_intelligence import generate_price_comparison
    from utils.ai.nlp_search import parse_nlp_query

class TestAIUtils(unittest.TestCase):
    # Phase 1 Tests
    def test_safety_scorer_unsafe_word(self):
        """Test that 'unsafe' does not trigger positive sentiment for 'safe'."""
        print("\nTesting Safety Scorer Substring Bug...")
        data = {
            "reviews": [
                {"comment": "This area is very unsafe at night."}
            ]
        }
        result = calculate_safety_score("UnknownTown", data)
        self.assertEqual(result['basedOn']['positiveSignals'], 0, "Should not detect 'safe' inside 'unsafe'")
        self.assertEqual(result['basedOn']['negativeSignals'], 1, "Should detect 'unsafe'")

    def test_spam_detector_free_context(self):
        """Test that 'free' is detected intelligently (e.g. ignoring 'smoke free')."""
        print("\nTesting Spam Detector Context...")
        data = {
            "title": "Nice Room",
            "description": "This is a smoke free environment.",
            "price": 50_000,
            "town": "Colombo"
        }
        result = detect_spam(data)
        flags = [f['type'] for f in result['flags']]
        self.assertNotIn('price_suspicious', flags, "Should not flag 'smoke free' as suspicious price")

    def test_spam_detector_actual_spam(self):
        """Test that actual spam patterns are still detected."""
        print("\nTesting Spam Detector Positive Case...")
        data = {
            "title": "FREE MONEY",
            "description": "Call me at 0771234567 for free money.",
            "price": 0,
            "town": "Colombo"
        }
        result = detect_spam(data)
        flags = [f['type'] for f in result['flags']]
        self.assertIn('price_suspicious', flags)
    
    def test_spam_detector_caps_abuse(self):
        """Test CAPS abuse detection."""
        print("\nTesting Spam Detector CAPS Abuse...")
        data = {
            "title": "NICE APARTMENT",
            "description": "THIS IS A VERY GOOD PLACE TO STAY WITH LOTS OF AMENITIES AND FACILITIES",
            "price": 50000,
            "town": "Colombo"
        }
        result = detect_spam(data)
        flags = [f['type'] for f in result['flags']]
        self.assertIn('caps_abuse', flags)

    # Phase 2 Tests
    def test_nlp_search_high_price(self):
        """Test parsing of high prices with commas (e.g. 1,200,000)."""
        print("\nTesting NLP Search High Price...")
        query = "Luxury house under 1,200,000"
        result = parse_nlp_query(query)
        self.assertEqual(result['parsed_filters'].get('maxPrice'), 1200000, "Should handle million values with commas")

    def test_nlp_search_town_partial_match(self):
        """Test that town matching uses word boundaries."""
        print("\nTesting NLP Search Town Matching...")
        # 'Matara' should not be found in 'Mataramba' (if Mataramba was a word, but let's use a fake suffix)
        # Using a constrained real example: 'Fort' should match 'Fort', but maybe not 'Comfort' if it was a town?
        # Better: SL_TOWNS contains 'Col' (no) 'Galle'.
        # Let's try "Galle" vs "Gallery" (if "Gallery" was in query)
        query = "Looking for art gallery space"
        # Since 'galle' is in SL_TOWNS, it might match 'gallery' if substring matching is used
        result = parse_nlp_query(query)
        # We expect 'Galle' NOT to be found
        self.assertNotEqual(result['parsed_filters'].get('town'), 'Galle', "Should not match 'Galle' in 'gallery'")

    def test_nlp_search_town_exact_match(self):
        """Test that town matching finds exact towns."""
        print("\nTesting NLP Search Exact Town...")
        query = "House in Galle"
        result = parse_nlp_query(query)
        self.assertEqual(result['parsed_filters'].get('town'), 'Galle')

if __name__ == '__main__':
    with open('test_results.log', 'w', encoding='utf-8') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)
