import sys
import json
import re

def normalize(text):
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def word_overlap(text1, text2):
    """Calculate Jaccard similarity between two texts."""
    words1 = set(normalize(text1).split())
    words2 = set(normalize(text2).split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)

def detect_duplicates(new_listing, existing_listings):
    """
    Detect potential duplicate listings.
    Compares: title similarity, same location, same price range, same beds/baths
    Returns: list of potential duplicates with similarity scores
    """
    potential_duplicates = []

    new_title = new_listing.get('title', '')
    new_desc = new_listing.get('description', '')
    new_town = new_listing.get('town', '').lower()
    new_price = new_listing.get('price', 0)
    new_beds = new_listing.get('beds', 0)
    new_baths = new_listing.get('baths', 0)
    new_type = new_listing.get('type', '').lower()

    for listing in existing_listings:
        score = 0
        reasons = []

        ex_town = listing.get('town', '').lower()
        ex_price = listing.get('price', 0)
        ex_beds = listing.get('beds', 0)
        ex_baths = listing.get('baths', 0)
        ex_type = listing.get('type', '').lower()
        ex_title = listing.get('title', '')
        ex_desc = listing.get('description', '')

        # Same town (+25)
        if new_town and ex_town and new_town == ex_town:
            score += 25
            reasons.append('Same town')

        # Same property type (+15)
        if new_type and ex_type and new_type == ex_type:
            score += 15
            reasons.append('Same property type')

        # Same beds + baths (+20)
        if new_beds == ex_beds and new_baths == ex_baths and new_beds > 0:
            score += 20
            reasons.append(f'Same {new_beds}BR/{new_baths}BA')

        # Price within 10% (+15)
        if new_price > 0 and ex_price > 0:
            price_diff = abs(new_price - ex_price) / max(new_price, ex_price)
            if price_diff < 0.05:
                score += 15
                reasons.append('Nearly identical price')
            elif price_diff < 0.10:
                score += 10
                reasons.append('Similar price range')

        # Title similarity (+25)
        title_sim = word_overlap(new_title, ex_title)
        if title_sim > 0.7:
            score += 25
            reasons.append(f'Very similar title ({int(title_sim * 100)}%)')
        elif title_sim > 0.5:
            score += 15
            reasons.append(f'Similar title ({int(title_sim * 100)}%)')

        # Description similarity (bonus)
        if new_desc and ex_desc:
            desc_sim = word_overlap(new_desc, ex_desc)
            if desc_sim > 0.6:
                score += 10
                reasons.append(f'Similar description ({int(desc_sim * 100)}%)')

        # Only flag if score is significant
        if score >= 50:
            potential_duplicates.append({
                'listingId': listing.get('_id', ''),
                'title': ex_title,
                'similarityScore': min(score, 100),
                'reasons': reasons,
                'isDuplicate': score >= 75
            })

    # Sort by similarity
    potential_duplicates.sort(key=lambda x: x['similarityScore'], reverse=True)

    return {
        'hasDuplicates': any(d['isDuplicate'] for d in potential_duplicates),
        'potentialDuplicates': potential_duplicates[:5],
        'totalChecked': len(existing_listings)
    }

if __name__ == '__main__':
    input_data = json.loads(sys.stdin.read())
    new_listing = input_data.get('newListing', {})
    existing = input_data.get('existingListings', [])
    result = detect_duplicates(new_listing, existing)
    print(json.dumps(result))
