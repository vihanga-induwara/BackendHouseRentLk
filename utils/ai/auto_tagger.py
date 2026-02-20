import sys
import json
import re

# Tag patterns: (regex_pattern, tag_name, display_label)
TAG_PATTERNS = [
    # Furnishing
    (r'\bfully\s*furnished\b', 'furnished', 'Fully Furnished'),
    (r'\bsemi[\s-]*furnished\b', 'semi_furnished', 'Semi-Furnished'),
    (r'\bunfurnished\b', 'unfurnished', 'Unfurnished'),

    # Amenities
    (r'\bair[\s-]*condition(?:ed|ing)?\b|\ba/?c\b', 'ac', 'Air Conditioned'),
    (r'\bwi[\s-]*fi\b|\binternet\b|\bbroadband\b', 'wifi', 'WiFi Available'),
    (r'\bparking\b|\bgarage\b|\bcar\s*port\b', 'parking', 'Parking'),
    (r'\bgarden\b|\byard\b|\blawn\b', 'garden', 'Garden'),
    (r'\bpool\b|\bswimming\b', 'pool', 'Swimming Pool'),
    (r'\bsolar\b', 'solar', 'Solar Power'),
    (r'\bsecurity\b|\bcctv\b|\bguard\b', 'security', 'Security'),
    (r'\bhot\s*water\b|\bgeyser\b', 'hot_water', 'Hot Water'),
    (r'\bgym\b|\bfitness\b', 'gym', 'Gym Access'),

    # Nearby places
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?(?:university|uni|campus)\b|\buniversity\s+(?:of|nearby)\b', 'near_university', 'Near University'),
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?hospital\b|\bhospital\s+nearby\b', 'near_hospital', 'Near Hospital'),
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?school\b|\bschool\s+nearby\b', 'near_school', 'Near School'),
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?supermarket\b|\bsupermarket\s+nearby\b', 'near_supermarket', 'Near Supermarket'),
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?(?:bus\s+(?:stop|stand|route|station))\b|\bbus\s+(?:stop|stand|route)\s+nearby\b', 'bus_route', 'Near Bus Route'),
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?(?:train|railway)\b|\btrain\s+(?:station)?\s*nearby\b', 'near_train', 'Near Train Station'),
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?temple\b|\btemple\s+nearby\b', 'near_temple', 'Near Temple'),
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?beach\b|\bbeach\s+nearby\b|\bbeachfront\b', 'near_beach', 'Near Beach'),
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?(?:main\s*road|highway)\b|\bmain\s*road\s+nearby\b', 'main_road', 'Near Main Road'),

    # Property type features
    (r'\bpet[\s-]*(?:friendly|allowed)\b|\bpets?\s+welcome\b', 'pet_friendly', 'Pet Friendly'),
    (r'\bquiet\b|\bpeaceful\b|\btranquil\b', 'quiet_area', 'Quiet Area'),
    (r'\bsafe\b|\bfamily[\s-]*friendly\b', 'safe_area', 'Safe Area'),
    (r'\bnew(?:ly)?\s*(?:built|constructed|renovated)\b', 'newly_built', 'Newly Built/Renovated'),
    (r'\bspacious\b|\blarge\b', 'spacious', 'Spacious'),
    (r'\bbills?\s*included\b|\butilities?\s*included\b', 'bills_included', 'Bills Included'),
    (r'\bground\s*floor\b', 'ground_floor', 'Ground Floor'),
    (r'\battached\s*bath(?:room)?\b|\ben[\s-]*suite\b', 'attached_bath', 'Attached Bathroom'),

    # SL-specific
    (r'\bnear\s+(?:a\s+)?(?:the\s+)?kovil\b', 'near_kovil', 'Near Kovil'),
    (r'\bwater\s*(?:bill)?\s*included\b', 'water_included', 'Water Included'),
    (r'\b(?:close|near)\s+(?:to\s+)?(?:colombo|city)\b', 'near_city', 'Close to Colombo'),
]


def extract_tags(data):
    """
    Extracts tags from listing description and amenities.
    """
    description = data.get('description', '').lower()
    title = data.get('title', '').lower()
    amenities = data.get('amenities', {})
    furnished = data.get('furnished', '')

    combined_text = f"{title} {description}"

    tags = []
    nearby_places = []
    tag_names_set = set()  # avoid duplicates

    # 1. Pattern-based extraction from text
    for pattern, tag_name, label in TAG_PATTERNS:
        if tag_name not in tag_names_set and re.search(pattern, combined_text, re.IGNORECASE):
            tag_names_set.add(tag_name)
            entry = {"tag": tag_name, "label": label, "source": "text"}
            if tag_name.startswith('near_') or tag_name in ('bus_route', 'main_road'):
                nearby_places.append(label)
            tags.append(entry)

    # 2. Direct amenity-based tags
    amenity_map = {
        'ac': ('ac', 'Air Conditioned'),
        'wifi': ('wifi', 'WiFi Available'),
        'parking': ('parking', 'Parking'),
        'garden': ('garden', 'Garden'),
        'solarPower': ('solar', 'Solar Power'),
        'security': ('security', 'Security'),
        'petsAllowed': ('pet_friendly', 'Pet Friendly'),
        'attachedBath': ('attached_bath', 'Attached Bathroom'),
    }

    for amenity_key, (tag_name, label) in amenity_map.items():
        if amenities.get(amenity_key) and tag_name not in tag_names_set:
            tag_names_set.add(tag_name)
            tags.append({"tag": tag_name, "label": label, "source": "amenity"})

    # 3. Furnished status
    if furnished and furnished != 'Unfurnished':
        tag_name = 'furnished' if furnished == 'Furnished' else 'semi_furnished'
        label = 'Fully Furnished' if furnished == 'Furnished' else 'Semi-Furnished'
        if tag_name not in tag_names_set:
            tag_names_set.add(tag_name)
            tags.append({"tag": tag_name, "label": label, "source": "field"})

    return {
        "tags": [t["tag"] for t in tags],
        "tagDetails": tags,
        "nearbyPlaces": nearby_places,
        "totalTags": len(tags)
    }


if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)

        data = json.loads(input_data)
        result = extract_tags(data)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
