import sys
import json

def analyze_demand(town_data):
    """
    Analyze real estate demand by town.
    Calculates supply/demand metrics from listing data and search trends.
    """
    results = []

    for town in town_data:
        name = town.get('name', 'Unknown')
        listing_count = town.get('listings', 0)
        total_views = town.get('totalViews', 0)
        avg_price = town.get('avgPrice', 0)
        search_count = town.get('searchCount', 0)
        inquiry_count = town.get('inquiryCount', 0)

        # Demand score factors
        demand_score = 0

        # Views per listing (high = more demand)
        views_per_listing = total_views / max(listing_count, 1)
        if views_per_listing > 100:
            demand_score += 30
        elif views_per_listing > 50:
            demand_score += 20
        elif views_per_listing > 20:
            demand_score += 10

        # Search to listing ratio (high = undersupplied)
        if listing_count > 0:
            sl_ratio = search_count / listing_count
            if sl_ratio > 5:
                demand_score += 30
            elif sl_ratio > 2:
                demand_score += 20
            elif sl_ratio > 1:
                demand_score += 10

        # Inquiry intensity
        inquiry_per_listing = inquiry_count / max(listing_count, 1)
        if inquiry_per_listing > 5:
            demand_score += 20
        elif inquiry_per_listing > 2:
            demand_score += 15
        elif inquiry_per_listing > 1:
            demand_score += 5

        # Supply level
        if listing_count > 50:
            supply_level = 'high'
        elif listing_count > 20:
            supply_level = 'medium'
        elif listing_count > 5:
            supply_level = 'low'
        else:
            supply_level = 'very_low'

        # Demand level
        demand_score = min(100, demand_score)
        if demand_score >= 70:
            demand_level = 'hot'
            label = '🔥 Hot Market'
            tip = 'High demand, low supply. Landlords can price competitively.'
        elif demand_score >= 50:
            demand_level = 'warm'
            label = '🌤️ Active Market'
            tip = 'Good demand. Properties rent within 2-3 weeks.'
        elif demand_score >= 30:
            demand_level = 'moderate'
            label = '🌥️ Moderate'
            tip = 'Balanced market. Competitive pricing recommended.'
        else:
            demand_level = 'cool'
            label = '❄️ Cool Market'
            tip = 'Lower demand. Consider adjusting pricing or adding amenities.'

        results.append({
            'town': name,
            'demandScore': demand_score,
            'demandLevel': demand_level,
            'supplyLevel': supply_level,
            'label': label,
            'tip': tip,
            'stats': {
                'listings': listing_count,
                'totalViews': total_views,
                'viewsPerListing': round(views_per_listing),
                'avgPrice': round(avg_price),
                'inquiries': inquiry_count,
                'searches': search_count
            }
        })

    # Sort by demand score (hottest first)
    results.sort(key=lambda x: x['demandScore'], reverse=True)

    return {
        'towns': results,
        'hottestMarket': results[0]['town'] if results else None,
        'coolestMarket': results[-1]['town'] if results else None,
        'totalTowns': len(results)
    }

if __name__ == '__main__':
    input_data = json.loads(sys.stdin.read())
    towns = input_data.get('towns', [])
    result = analyze_demand(towns)
    print(json.dumps(result))
