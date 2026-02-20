"""
Scraped Listing Analyzer — AI enrichment for individual scraped listings.
Generates: fair price estimate, quality score, scam risk, location insights, comparison.

Input (stdin JSON): {
    "listing": { title, description, price, location, beds, baths, ... },
    "localStats": { avgPrice, totalListings, avgBeds, avgBaths, priceRange }
}
Output (stdout JSON): {
    "estimatedFairPrice": N,
    "priceRating": "Below Market" | "Fair" | "Above Market",
    "qualityScore": N (0-100),
    "scamRiskScore": N (0-100),
    "locationInsights": "...",
    "comparisonToLocal": "...",
    "tags": [...],
    "marketTrend": "Rising" | "Stable" | "Declining",
    "dataCompleteness": N (0-100)
}
"""
import sys
import json
import re

# ──────────────────────────────────────────────
#   PRICE ANALYSIS
# ──────────────────────────────────────────────

def estimate_fair_price(listing, local_stats):
    """Estimate fair price based on local market data."""
    avg_price = local_stats.get('avgPrice', 0)
    listing_price = listing.get('price', 0)
    beds = listing.get('beds', 0)
    avg_beds = local_stats.get('avgBeds', 2)

    if avg_price <= 0:
        return listing_price, 'Unknown'

    # Adjust average by bed difference
    bed_factor = 1.0
    if beds > 0 and avg_beds > 0:
        bed_factor = 1 + (beds - avg_beds) * 0.15

    estimated = int(avg_price * bed_factor)

    if listing_price <= 0:
        return estimated, 'Unknown'

    diff_pct = ((listing_price - estimated) / estimated) * 100

    if diff_pct <= -15:
        rating = 'Below Market'
    elif diff_pct >= 15:
        rating = 'Above Market'
    else:
        rating = 'Fair'

    return estimated, rating


# ──────────────────────────────────────────────
#   QUALITY SCORING
# ──────────────────────────────────────────────

def calculate_quality_score(listing):
    """Score listing quality 0-100 based on completeness and content."""
    score = 0

    # Title quality (max 15)
    title = listing.get('title', '')
    if title:
        score += 5
        if len(title) > 20: score += 5
        if len(title) > 40: score += 5

    # Description quality (max 20)
    desc = listing.get('description', '')
    if desc:
        score += 5
        if len(desc) > 50: score += 5
        if len(desc) > 150: score += 5
        if len(desc) > 300: score += 5

    # Price (max 10)
    if listing.get('price', 0) > 0: score += 10

    # Location (max 15)
    loc = listing.get('location', {})
    if loc.get('town'): score += 5
    if loc.get('district'): score += 5
    if loc.get('rawAddress'): score += 5

    # Specs (max 15)
    if listing.get('beds', 0) > 0: score += 5
    if listing.get('baths', 0) > 0: score += 5
    if listing.get('size', 0) > 0: score += 5

    # Images (max 15)
    images = listing.get('images', [])
    if images:
        score += 5
        if len(images) >= 3: score += 5
        if len(images) >= 5: score += 5

    # Type/furnished (max 10)
    if listing.get('type', 'Unknown') != 'Unknown': score += 5
    if listing.get('furnished', 'Unknown') != 'Unknown': score += 5

    return min(score, 100)


# ──────────────────────────────────────────────
#   SCAM RISK DETECTION
# ──────────────────────────────────────────────

SCAM_KEYWORDS = [
    'urgent', 'too good', 'act fast', 'limited time', 'won\'t last',
    'send money', 'western union', 'wire transfer', 'deposit first',
    'overseas', 'abroad', 'can\'t show', 'sight unseen',
]

def calculate_scam_risk(listing, local_stats):
    """Score scam risk 0-100. Higher = more suspicious."""
    risk = 0
    reasons = []

    price = listing.get('price', 0)
    avg_price = local_stats.get('avgPrice', 0)

    # Suspiciously low price
    if price > 0 and avg_price > 0:
        if price < avg_price * 0.4:
            risk += 30
            reasons.append('Price is less than 40% of area average')
        elif price < avg_price * 0.6:
            risk += 15
            reasons.append('Price is significantly below average')

    # No images
    if not listing.get('images'):
        risk += 15
        reasons.append('No images provided')

    # Very short description
    desc = listing.get('description', '')
    if len(desc) < 20:
        risk += 10
        reasons.append('Very short description')

    # Scam keywords in text
    combined = f"{listing.get('title', '')} {desc}".lower()
    for keyword in SCAM_KEYWORDS:
        if keyword in combined:
            risk += 10
            reasons.append(f'Suspicious keyword: "{keyword}"')
            break  # Only count once

    # PII in listing (already processed by scraper)
    if listing.get('piiDetected'):
        risk += 5

    # No location info
    loc = listing.get('location', {})
    if not loc.get('town') and not loc.get('rawAddress'):
        risk += 10
        reasons.append('No location information')

    # Missing key specs
    if listing.get('beds', 0) == 0 and listing.get('baths', 0) == 0:
        risk += 5
        reasons.append('Missing bed/bath information')

    return min(risk, 100), reasons


# ──────────────────────────────────────────────
#   DATA COMPLETENESS
# ──────────────────────────────────────────────

def calculate_completeness(listing):
    """Calculate % of important fields that are filled."""
    fields = {
        'title': bool(listing.get('title')),
        'description': bool(listing.get('description')),
        'price': listing.get('price', 0) > 0,
        'town': bool(listing.get('location', {}).get('town')),
        'district': bool(listing.get('location', {}).get('district')),
        'beds': listing.get('beds', 0) > 0,
        'baths': listing.get('baths', 0) > 0,
        'size': listing.get('size', 0) > 0,
        'type': listing.get('type', 'Unknown') != 'Unknown',
        'images': len(listing.get('images', [])) > 0,
    }
    filled = sum(1 for v in fields.values() if v)
    return int((filled / len(fields)) * 100)


# ──────────────────────────────────────────────
#   LOCATION INSIGHTS
# ──────────────────────────────────────────────

TOWN_INSIGHTS = {
    'colombo': 'Prime urban location with excellent infrastructure, commercial centers, and high demand.',
    'negombo': 'Coastal city near the airport, popular for beachside living and tourism.',
    'kandy': 'Cultural capital with cool climate, universities, and heritage sites.',
    'galle': 'Historic Dutch fort city with growing tourism and southern charm.',
    'gampaha': 'Suburban hub with good schools, hospitals, and quick Colombo access.',
    'nugegoda': 'Well-connected suburb with active markets and urban amenities.',
    'dehiwala': 'Popular residential area close to Colombo with zoo and beaches.',
    'mount lavinia': 'Scenic beachfront suburb, popular with expats and professionals.',
    'battaramulla': 'Growing IT corridor with modern developments and government offices.',
    'rajagiriya': 'Upscale residential area close to government and business districts.',
}

def generate_location_insights(listing):
    """Generate location-specific insights."""
    town = listing.get('location', {}).get('town', '').lower().strip()
    
    if town in TOWN_INSIGHTS:
        return TOWN_INSIGHTS[town]
    
    # Generic fallback
    town_cap = town.title() if town else 'This area'
    return f"{town_cap} is a developing area in Sri Lanka with improving infrastructure and growing residential appeal."


# ──────────────────────────────────────────────
#   COMPARISON TO LOCAL
# ──────────────────────────────────────────────

def generate_comparison(listing, local_stats):
    """Compare scraped listing to local HouseRentLk data."""
    price = listing.get('price', 0)
    avg_price = local_stats.get('avgPrice', 0)
    total_local = local_stats.get('totalListings', 0)
    beds = listing.get('beds', 0)
    town = listing.get('location', {}).get('town', 'this area')

    parts = []

    if avg_price > 0 and price > 0:
        diff = ((price - avg_price) / avg_price) * 100
        if diff > 0:
            parts.append(f"This listing is {abs(diff):.0f}% above the HouseRentLk average of LKR {avg_price:,.0f}/month in {town}.")
        elif diff < 0:
            parts.append(f"This listing is {abs(diff):.0f}% below the HouseRentLk average of LKR {avg_price:,.0f}/month in {town}.")
        else:
            parts.append(f"This listing matches the HouseRentLk average of LKR {avg_price:,.0f}/month in {town}.")

    if total_local > 0:
        parts.append(f"HouseRentLk has {total_local} verified listings in {town}.")
    else:
        parts.append(f"HouseRentLk has limited coverage in {town} — this external listing helps fill the gap.")

    return ' '.join(parts) if parts else 'No local comparison data available.'


# ──────────────────────────────────────────────
#   TAG GENERATION
# ──────────────────────────────────────────────

def generate_tags(listing):
    """Auto-generate tags from listing data."""
    tags = []
    title = listing.get('title', '').lower()
    desc = listing.get('description', '').lower()
    combined = f"{title} {desc}"

    tag_keywords = {
        'Furnished': ['furnished', 'fully furnished'],
        'Near School': ['school', 'near school'],
        'Near Hospital': ['hospital', 'medical'],
        'Near Beach': ['beach', 'sea view', 'ocean'],
        'Near Transport': ['bus', 'train', 'transport'],
        'Garden': ['garden', 'backyard'],
        'Parking': ['parking', 'garage', 'car park'],
        'AC': ['a/c', 'air condition', 'ac '],
        'WiFi': ['wifi', 'internet'],
        'Pet Friendly': ['pet', 'pets allowed'],
        'New Build': ['new build', 'brand new', 'newly built'],
        'Good Deal': [],  # Set by price analysis
    }

    for tag, keywords in tag_keywords.items():
        for kw in keywords:
            if kw in combined:
                tags.append(tag)
                break

    # Price-based tags
    price = listing.get('price', 0)
    if price > 0:
        if price < 25000: tags.append('Budget Friendly')
        elif price > 100000: tags.append('Premium')

    # Bed-based tags
    beds = listing.get('beds', 0)
    if beds >= 4: tags.append('Family Home')
    elif beds == 1: tags.append('Single/Couple')

    return tags


# ──────────────────────────────────────────────
#   MAIN
# ──────────────────────────────────────────────

def analyze_listing(data):
    listing = data.get('listing', {})
    local_stats = data.get('localStats', {})

    estimated_price, price_rating = estimate_fair_price(listing, local_stats)
    quality = calculate_quality_score(listing)
    scam_risk, scam_reasons = calculate_scam_risk(listing, local_stats)
    completeness = calculate_completeness(listing)
    location_insights = generate_location_insights(listing)
    comparison = generate_comparison(listing, local_stats)
    tags = generate_tags(listing)

    return {
        'estimatedFairPrice': estimated_price,
        'priceRating': price_rating,
        'qualityScore': quality,
        'scamRiskScore': scam_risk,
        'scamReasons': scam_reasons,
        'locationInsights': location_insights,
        'comparisonToLocal': comparison,
        'tags': tags,
        'marketTrend': 'Stable',  # Would need historical data for real analysis
        'dataCompleteness': completeness,
    }

if __name__ == '__main__':
    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
            print(json.dumps({"error": "No input provided"}))
            sys.exit(1)
        data = json.loads(input_data)
        result = analyze_listing(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
