import sys
import json
import re
from typing import Dict, Any, List

# Sri Lankan town safety baseline data (curated estimates)
# Scale: 0-100 where 100 is safest
TOWN_SAFETY_BASELINES: Dict[str, int] = {
    "colombo": 60, "colombo 7": 80, "colombo 3": 75, "colombo 5": 75,
    "rajagiriya": 78, "nugegoda": 72, "maharagama": 68,
    "dehiwala": 65, "mount lavinia": 70, "moratuwa": 62,
    "piliyandala": 70, "malabe": 74, "kaduwela": 72,
    "kottawa": 75, "thalawathugoda": 80, "battaramulla": 78,
    "nawala": 76, "borella": 62, "wellawatte": 58,
    "bambalapitiya": 65, "kollupitiya": 72, "kohuwala": 74,
    "pepiliyana": 73, "boralesgamuwa": 72,
    "kandy": 68, "galle": 72, "negombo": 60,
    "nuwara eliya": 82, "ella": 85, "bandarawela": 80,
    "matara": 65, "jaffna": 58, "trincomalee": 60,
    "anuradhapura": 70, "kurunegala": 68,
    "panadura": 64, "kalutara": 66,
    "wattala": 62, "kadawatha": 70, "kiribathgoda": 66,
    "kelaniya": 64, "homagama": 72,
    "fort": 55, "pettah": 50, "athurugiriya": 73,
    "hokandara": 76, "horana": 70,
}

# Configurable constants
DEFAULT_BASELINE = 65
SENTIMENT_ADJUSTMENT_FACTOR = 20

def calculate_safety_score(town: str, review_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate neighborhood safety score from:
    1. Baseline town data
    2. Review sentiment about safety
    3. Community feedback
    """
    town_lower = town.lower().strip() if town else ''

    # Get baseline
    baseline = TOWN_SAFETY_BASELINES.get(town_lower, DEFAULT_BASELINE)

    # Analyze reviews for safety-related keywords
    # Use word boundaries (\b) to avoid substring matches like "safe" in "unsafe"
    safety_positive = [
        r'\bsafe\b', r'\bsecure\b', r'\bquiet\b', r'\bpeaceful\b', r'\bcalm\b', r'\bfamily\b',
        r'\bguard\b', r'\bcctv\b', r'\bgated\b', r'\bwell-lit\b', r'\bfriendly\b', r'\bclean\b'
    ]
    safety_negative = [
        r'\bunsafe\b', r'\bdangerous\b', r'\bsketchy\b', r'\bnoisy\b', r'\bloud\b', r'\btheft\b',
        r'\brobbery\b', r'\bcrime\b', r'\bharassment\b', r'\bstray dogs\b', r'\bflooding\b',
        r'\bdirty\b', r'\bpollution\b', r'\bdark streets\b', r'\bscary\b'
    ]

    positive_count = 0
    negative_count = 0
    review_comments = review_data.get('reviews', [])

    for review in review_comments:
        comment = review.get('comment', '').lower()
        
        # Check positive keywords
        for pattern in safety_positive:
            if re.search(pattern, comment):
                positive_count += 1
                
        # Check negative keywords
        for pattern in safety_negative:
            if re.search(pattern, comment):
                negative_count += 1

    # Adjust baseline with review sentiment
    review_adjustment = 0
    if positive_count + negative_count > 0:
        sentiment_ratio = positive_count / (positive_count + negative_count)
        # Ratio 1.0 -> (0.5 * 20) = +10
        # Ratio 0.0 -> (-0.5 * 20) = -10
        review_adjustment = (sentiment_ratio - 0.5) * SENTIMENT_ADJUSTMENT_FACTOR

    final_score = max(0, min(100, baseline + review_adjustment))

    # Generate category breakdown
    categories = []

    # Night safety
    night_score = final_score - 10 if final_score > 50 else final_score - 5
    categories.append({
        'name': 'Night Safety',
        'score': max(0, min(100, round(night_score))),
        'icon': '🌙'
    })

    # Public transport
    transport_score = final_score + 5 if town_lower in ['colombo', 'kandy', 'galle', 'nugegoda', 'maharagama'] else final_score - 5
    categories.append({
        'name': 'Transport Access',
        'score': max(0, min(100, round(transport_score))),
        'icon': '🚌'
    })

    # Family friendliness
    family_score = final_score + 8 if final_score > 70 else final_score
    categories.append({
        'name': 'Family Friendly',
        'score': max(0, min(100, round(family_score))),
        'icon': '👨‍👩‍👧'
    })

    # Walkability
    walk_score = final_score + 3
    categories.append({
        'name': 'Walkability',
        'score': max(0, min(100, round(walk_score))),
        'icon': '🚶'
    })

    # Determine label
    if final_score >= 80:
        label = 'Very Safe'
        color = 'green'
    elif final_score >= 65:
        label = 'Safe'
        color = 'blue'
    elif final_score >= 50:
        label = 'Moderate'
        color = 'yellow'
    else:
        label = 'Exercise Caution'
        color = 'orange'

    return {
        'overallScore': round(final_score),
        'label': label,
        'color': color,
        'categories': categories,
        'basedOn': {
            'town': town,
            'reviewsAnalyzed': len(review_comments),
            'positiveSignals': positive_count,
            'negativeSignals': negative_count
        }
    }

if __name__ == '__main__':
    try:
        input_data = json.loads(sys.stdin.read())
        town_input = input_data.get('town', '')
        review_data_input = input_data.get('reviewData', {})
        result_output = calculate_safety_score(town_input, review_data_input)
        print(json.dumps(result_output))
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input", "trustScore": 0}))
    except Exception as e:
        print(json.dumps({"error": str(e), "trustScore": 0}))
