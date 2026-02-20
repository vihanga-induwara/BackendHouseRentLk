"""
Market Intelligence — Generates competitive analytics reports from scraped vs local data.

Input (stdin JSON): {
    "scrapedByArea": [{ "town": "...", "count": N, "avgPrice": N, "sources": [...] }],
    "localByArea": [{ "town": "...", "count": N, "avgPrice": N }],
    "scrapedBySource": [{ "source": "...", "count": N, "avgPrice": N }],
    "totalScraped": N,
    "totalLocal": N
}
Output (stdout JSON): {
    "priceComparison": [...],
    "hotAreas": [...],
    "gapOpportunities": [...],
    "supplyAnalysis": {...},
    "summary": "..."
}
"""
import sys
import json
import io
from typing import List, Dict, Any, TypedDict, Optional

# Set up UTF-8 encoding for stdin and stdout
# sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Constants for Analysis Thresholds
PRICE_DIFF_SIGNIFICANT = 10.0  # Percentage difference to be considered significant
SUPPLY_SPIKE_FACTOR = 1.5      # Factor above average count to consider a spike
PRICE_SPIKE_FACTOR = 1.3       # Factor above average price to consider high
PRICE_DROP_FACTOR = 0.7        # Factor below average price to consider low
GAP_OPPORTUNITY_MIN_LISTINGS = 5
GAP_OPPORTUNITY_RATIO = 0.3    # Local listings must be less than 30% of competitor listings
GAP_PRIORITY_HIGH_RATIO = 5.0  # Ratio of competitor/local listings to be high priority
EXTERNAL_INTERNAL_RATIO_HIGH = 3.0
EXTERNAL_INTERNAL_RATIO_LOW = 1.0

# Type Definitions
class ScrapedArea(TypedDict, total=False):
    town: str
    count: int
    avgPrice: float
    sources: List[str]

class LocalArea(TypedDict, total=False):
    town: str
    count: int
    avgPrice: float

class ComparisonResult(TypedDict):
    town: str
    scrapedAvgPrice: int
    localAvgPrice: int
    priceDiffPercent: float
    scrapedCount: int
    localCount: int
    volumeDiffPercent: float
    insight: str

class HotArea(TypedDict):
    town: str
    listingCount: int
    avgPrice: int
    reasons: List[str]
    heatScore: int

class GapOpportunity(TypedDict):
    town: str
    competitorListings: int
    ourListings: int
    gapRatio: float
    opportunity: str
    priority: str

class SupplySource(TypedDict):
    source: str
    count: int
    avgPrice: int
    marketShare: float

class SupplyAnalysis(TypedDict):
    totalExternal: int
    totalInternal: int
    externalToInternalRatio: float
    sourceBreakdown: List[SupplySource]
    dominantSource: str

class MarketReport(TypedDict):
    priceComparison: List[ComparisonResult]
    hotAreas: List[HotArea]
    gapOpportunities: List[GapOpportunity]
    supplyAnalysis: SupplyAnalysis
    summary: str

def generate_price_comparison(scraped_areas: List[ScrapedArea], local_areas: List[LocalArea]) -> List[ComparisonResult]:
    """Compare prices between scraped data and local listings per area."""
    local_map: Dict[str, LocalArea] = {a.get('town', '').lower(): a for a in local_areas}
    comparisons: List[ComparisonResult] = []

    for area in scraped_areas:
        town = area.get('town', '')
        if not town:
            continue
            
        town_lower = town.lower()
        local = local_map.get(town_lower, {})
        
        scraped_avg = area.get('avgPrice', 0.0)
        local_avg = local.get('avgPrice', 0.0)
        scraped_count = area.get('count', 0)
        local_count = local.get('count', 0)

        diff_pct = 0.0
        if local_avg > 0 and scraped_avg > 0:
            diff_pct = round(((scraped_avg - local_avg) / local_avg) * 100, 1)

        insight = ''
        if diff_pct > PRICE_DIFF_SIGNIFICANT:
            insight = f'Competitor prices are {diff_pct}% higher — your listings are more affordable.'
        elif diff_pct < -PRICE_DIFF_SIGNIFICANT:
            insight = f'Competitor prices are {abs(diff_pct)}% lower — consider reviewing your pricing strategy.'
        else:
            insight = 'Prices are comparable across platforms.'

        # Avoid division by zero for volume diff
        volume_msg_denom = local_count if local_count > 0 else 1
        volume_diff = round(((scraped_count - local_count) / volume_msg_denom) * 100, 1)

        comparisons.append({
            'town': town,
            'scrapedAvgPrice': round(scraped_avg),
            'localAvgPrice': round(local_avg),
            'priceDiffPercent': diff_pct,
            'scrapedCount': scraped_count,
            'localCount': local_count,
            'volumeDiffPercent': volume_diff,
            'insight': insight,
        })

    # Sort by price difference magnitude descending (biggest gaps first)
    comparisons.sort(key=lambda x: abs(x['priceDiffPercent']), reverse=True)
    return comparisons

def detect_hot_areas(scraped_areas: List[ScrapedArea]) -> List[HotArea]:
    """Detect areas with high activity / price spikes."""
    hot: List[HotArea] = []
    
    if not scraped_areas:
        return hot

    total_count = sum(a.get('count', 0) for a in scraped_areas)
    total_price = sum(a.get('avgPrice', 0.0) for a in scraped_areas)
    num_areas = len(scraped_areas)
    
    if num_areas == 0:
        return []

    avg_count = total_count / num_areas
    avg_price = total_price / num_areas

    for area in scraped_areas:
        count = area.get('count', 0)
        price = area.get('avgPrice', 0.0)
        reasons = []

        if count > avg_count * SUPPLY_SPIKE_FACTOR:
            reasons.append(f'Supply spike: {count} listings vs avg {avg_count:.0f}')
        if price > avg_price * PRICE_SPIKE_FACTOR:
            reasons.append(f'High prices: LKR {price:,.0f} vs avg LKR {avg_price:,.0f}')
        if price < avg_price * PRICE_DROP_FACTOR and count > avg_count * 0.8: # 0.8 is arbitrary "decent supply" check
            reasons.append(f'Affordable area with good supply')

        if reasons:
            # Heat score calculation
            # Normalized metrics: count importance 50%, price importance 50%
            norm_count = (count / avg_count) if avg_count > 0 else 0
            norm_price = (price / avg_price) if avg_price > 0 else 0
            
            raw_score = (norm_count * 50) + (norm_price * 50)
            heat_score = min(100, int(raw_score))

            hot.append({
                'town': area.get('town', ''),
                'listingCount': count,
                'avgPrice': round(price),
                'reasons': reasons,
                'heatScore': heat_score,
            })

    hot.sort(key=lambda x: x['heatScore'], reverse=True)
    return hot[:10]

def detect_gap_opportunities(scraped_areas: List[ScrapedArea], local_areas: List[LocalArea]) -> List[GapOpportunity]:
    """Find areas where competitors have listings but we have few/none."""
    local_map = {a.get('town', '').lower(): a.get('count', 0) for a in local_areas}
    gaps: List[GapOpportunity] = []

    for area in scraped_areas:
        town = area.get('town', '')
        if not town:
            continue
            
        scraped_count = area.get('count', 0)
        local_count = local_map.get(town.lower(), 0)

        # Gap Criteria
        if scraped_count >= GAP_OPPORTUNITY_MIN_LISTINGS and local_count < scraped_count * GAP_OPPORTUNITY_RATIO:
            denom = local_count if local_count > 0 else 1
            gap_ratio = scraped_count / denom
            
            gaps.append({
                'town': town,
                'competitorListings': scraped_count,
                'ourListings': local_count,
                'gapRatio': round(gap_ratio, 1),
                'opportunity': f'{town} has {scraped_count} competitor listings but only {local_count} on HouseRentLk. This is an expansion opportunity.',
                'priority': 'HIGH' if gap_ratio > GAP_PRIORITY_HIGH_RATIO else 'MEDIUM',
            })

    gaps.sort(key=lambda x: x['gapRatio'], reverse=True)
    return gaps

def analyze_supply(scraped_by_source: List[Dict[str, Any]], total_scraped: int, total_local: int) -> SupplyAnalysis:
    """Analyze supply distribution across sources."""
    source_breakdown: List[SupplySource] = []
    
    safe_total_scraped = total_scraped if total_scraped > 0 else 1
    
    for source in scraped_by_source:
        count = source.get('count', 0)
        source_breakdown.append({
            'source': source.get('source', 'Unknown'),
            'count': count,
            'avgPrice': round(source.get('avgPrice', 0.0)),
            'marketShare': round((count / safe_total_scraped) * 100, 1),
        })

    safe_total_local = total_local if total_local > 0 else 1
    
    dominant_source = 'N/A'
    if source_breakdown:
         dominant_source_obj = max(source_breakdown, key=lambda x: x['count'])
         dominant_source = dominant_source_obj['source']

    return {
        'totalExternal': total_scraped,
        'totalInternal': total_local,
        'externalToInternalRatio': round(total_scraped / safe_total_local, 1),
        'sourceBreakdown': source_breakdown,
        'dominantSource': dominant_source,
    }

def generate_summary(comparisons: List[ComparisonResult], hot_areas: List[HotArea], gaps: List[GapOpportunity], supply: SupplyAnalysis) -> str:
    """Generate a human-readable executive summary."""
    parts = []

    parts.append(f"Market Overview: {supply['totalExternal']} external listings tracked across competitors vs {supply['totalInternal']} on HouseRentLk.")

    ratio = supply['externalToInternalRatio']
    if ratio > EXTERNAL_INTERNAL_RATIO_HIGH:
        parts.append(f"⚠️ Competitors have {ratio}x more listings — significant growth opportunity.")
    elif ratio < EXTERNAL_INTERNAL_RATIO_LOW:
        parts.append(f"✅ HouseRentLk has more listings than tracked competitors.")

    if comparisons:
        higher = [c for c in comparisons if c['priceDiffPercent'] > PRICE_DIFF_SIGNIFICANT]
        if higher:
            parts.append(f"📊 {len(higher)} areas where competitor prices are {PRICE_DIFF_SIGNIFICANT}%+ higher — your platform offers better value.")

    if gaps:
        parts.append(f"📍 {len(gaps)} gap opportunity areas detected where competitors dominate but HouseRentLk has few listings.")

    if hot_areas:
        top = hot_areas[0]
        parts.append(f"🔥 Hottest area: {top['town']} with {top['listingCount']} listings and avg LKR {top['avgPrice']:,.0f}/month.")

    return ' '.join(parts)

def generate_report(data: Dict[str, Any]) -> MarketReport:
    scraped_areas = data.get('scrapedByArea', [])
    local_areas = data.get('localByArea', [])
    scraped_by_source = data.get('scrapedBySource', [])
    total_scraped = data.get('totalScraped', 0)
    total_local = data.get('totalLocal', 0)

    comparisons = generate_price_comparison(scraped_areas, local_areas)
    hot_areas = detect_hot_areas(scraped_areas)
    gaps = detect_gap_opportunities(scraped_areas, local_areas)
    supply = analyze_supply(scraped_by_source, total_scraped, total_local)
    summary = generate_summary(comparisons, hot_areas, gaps, supply)

    return {
        'priceComparison': comparisons,
        'hotAreas': hot_areas,
        'gapOpportunities': gaps,
        'supplyAnalysis': supply,
        'summary': summary,
    }

if __name__ == '__main__':
    # Set up UTF-8 encoding for stdin and stdout
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
            print(json.dumps({"error": "No input provided"}))
            sys.exit(1)
        data = json.loads(input_data)
        result = generate_report(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        # Catch-all for unexpected runtime errors to output JSON error rather than stack trace
        print(json.dumps({"error": f"Internal Error: {str(e)}"}))
        sys.exit(1)
