import unittest
import sys
import os
import json

# Add Backend to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.ai.market_intelligence import generate_report, generate_price_comparison, detect_hot_areas

class TestMarketIntelligence(unittest.TestCase):
    def test_generate_report_basic(self):
        """Test basic report generation with valid data."""
        data = {
            "scrapedByArea": [{"town": "Colombo", "count": 10, "avgPrice": 50000, "sources": ["ikman"]}],
            "localByArea": [{"town": "Colombo", "count": 5, "avgPrice": 45000}],
            "scrapedBySource": [{"source": "ikman", "count": 10, "avgPrice": 50000}],
            "totalScraped": 10,
            "totalLocal": 5
        }
        report = generate_report(data)
        self.assertIn("priceComparison", report)
        self.assertIn("hotAreas", report)
        self.assertEqual(report["supplyAnalysis"]["totalExternal"], 10)

    def test_price_comparison_logic(self):
        """Test calculation of price difference percentage."""
        scraped = [{"town": "A", "count": 10, "avgPrice": 11500}]
        local = [{"town": "A", "count": 10, "avgPrice": 10000}]
        
        result = generate_price_comparison(scraped, local)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['priceDiffPercent'], 15.0)
        self.assertIn("Competitor prices are 15.0% higher", result[0]['insight'])

    def test_hot_areas_empty(self):
        """Test hot areas with empty input."""
        self.assertEqual(detect_hot_areas([]), [])

    def test_hot_areas_detection(self):
        """Test detection of spiked usage."""
        # Avg count = 10, Avg price = 100
        scraped = [
            {"town": "A", "count": 10, "avgPrice": 100}, 
            {"town": "B", "count": 10, "avgPrice": 100},
            {"town": "HotTown", "count": 20, "avgPrice": 100} # 2x avg count
        ]
        # Recalculated Avg Count = 40/3 = 13.33
        # HotTown count 20 > 13.33 * 1.5 (20) -> Edge case, let's make it bigger
        
        scraped = [
            {"town": "A", "count": 5, "avgPrice": 100}, 
            {"town": "B", "count": 5, "avgPrice": 100},
            {"town": "HotTown", "count": 50, "avgPrice": 100}
        ]
        # Avg count = 20. 
        # HotTown 50 > 20 * 1.5 (30). Should be hot.
        
        hot = detect_hot_areas(scraped)
        self.assertTrue(len(hot) > 0)
        self.assertEqual(hot[0]['town'], "HotTown")
        self.assertIn("Supply spike", hot[0]['reasons'][0])

if __name__ == '__main__':
    unittest.main()
