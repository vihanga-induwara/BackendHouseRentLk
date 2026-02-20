import sys
import json
import re
import io
import os
from typing import Dict, Any, List, Optional, Union

# Set up UTF-8 encoding for stdin and stdout
# sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load towns from JSON config with fallback
try:
    towns_path = os.path.join(os.path.dirname(__file__), 'towns.json')
    if os.path.exists(towns_path):
        with open(towns_path, 'r', encoding='utf-8') as f:
            SL_TOWNS = json.load(f)
    else:
        # Minimal fallback list
        SL_TOWNS = ["colombo", "kandy", "galle", "negombo", "matara", "kurunegala"]
except Exception:
    # Fallback if file read fails
    SL_TOWNS = ["colombo", "kandy", "galle", "negombo"]

PROPERTY_TYPES: Dict[str, str] = {
    "house": "House",
    "houses": "House",
    "boarding": "Boarding Room",
    "boarding room": "Boarding Room",
    "room": "Boarding Room",
    "rooms": "Boarding Room",
    "annex": "Annex",
    "annexe": "Annex",
    "apartment": "Apartment",
    "apartments": "Apartment",
    "flat": "Apartment",
    "flats": "Apartment",
    "land": "Land",
    "lands": "Land",
}

def parse_price(price_str: str, multiplier: Optional[str] = None) -> Optional[int]:
    """Helper to parse price strings like '1.2m', '50k', '1,000'."""
    try:
        clean_str = price_str.replace(',', '').lower()
        val = float(clean_str)
        
        if multiplier:
            if multiplier.lower() == 'k':
                val *= 1000
            elif multiplier.lower() == 'm': # Add million support if regex captures it
                val *= 1000000
        
        return int(val)
    except ValueError:
        return None

def parse_nlp_query(query: str) -> Dict[str, Any]:
    """
    Parse a natural language search query into structured filters.
    """
    q = query.lower().strip()
    filters: Dict[str, Any] = {}

    # Extract bedrooms: "2 bed", "3 bedroom", "2br"
    bed_match = re.search(r'(\d+)\s*(?:bed(?:room)?s?|br)\b', q)
    if bed_match:
        filters['beds'] = int(bed_match.group(1))
        q = q[:bed_match.start()] + q[bed_match.end():]

    # Extract bathrooms: "2 bath", "1 bathroom"
    bath_match = re.search(r'(\d+)\s*(?:bath(?:room)?s?)\b', q)
    if bath_match:
        filters['baths'] = int(bath_match.group(1))
        q = q[:bath_match.start()] + q[bath_match.end():]

    # Extract price range: "20k-50k", "20000 to 40000"
    # Regex explains: (digits+commas) opt (k/m) space (to|-) space (digits+commas) opt (k/m)
    price_range = re.search(r'([\d,]+(\.\d+)?)\s*(k|m)?\s*(?:to|-)\s*([\d,]+(\.\d+)?)\s*(k|m)?', q)
    if price_range:
        min_str = price_range.group(1)
        min_mult = price_range.group(3)
        max_str = price_range.group(4)
        max_mult = price_range.group(6)

        min_val = parse_price(min_str, min_mult)
        max_val = parse_price(max_str, max_mult)

        if min_val is not None and max_val is not None:
             filters['minPrice'] = min_val
             filters['maxPrice'] = max_val
             q = q[:price_range.start()] + q[price_range.end():]

    # Extract max price if not already found in range
    if 'maxPrice' not in filters:
        price_max = re.search(r'(?:under|below|max(?:imum)?|budget|less than|up to)\s*(?:lkr|rs\.?|rs)?\s*([\d,]+(\.\d+)?)\s*(k|m)?\b', q)
        if price_max:
             val = parse_price(price_max.group(1), price_max.group(3))
             if val is not None:
                filters['maxPrice'] = val
                q = q[:price_max.start()] + q[price_max.end():]

    # Extract min price if not already found in range
    if 'minPrice' not in filters:
        price_min = re.search(r'(?:above|over|min(?:imum)?|from|at least|more than)\s*(?:lkr|rs\.?|rs)?\s*([\d,]+(\.\d+)?)\s*(k|m)?\b', q)
        if price_min:
            val = parse_price(price_min.group(1), price_min.group(3))
            if val is not None:
                filters['minPrice'] = val
                q = q[:price_min.start()] + q[price_min.end():]

    # Extract property type
    for keyword, ptype in PROPERTY_TYPES.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', q):
            filters['type'] = ptype
            q = re.sub(r'\b' + re.escape(keyword) + r'\b', '', q)
            break

    # Extract furnished status
    if re.search(r'\bfully\s*furnished\b', q):
        filters['furnished'] = 'Furnished'
        q = re.sub(r'\bfully\s*furnished\b', '', q)
    elif re.search(r'\bsemi[- ]?furnished\b', q):
        filters['furnished'] = 'Semi-Furnished'
        q = re.sub(r'\bsemi[- ]?furnished\b', '', q)
    elif re.search(r'\bfurnished\b', q):
        filters['furnished'] = 'Furnished'
        q = re.sub(r'\bfurnished\b', '', q)
    elif re.search(r'\bunfurnished\b', q):
        filters['furnished'] = 'Unfurnished'
        q = re.sub(r'\bunfurnished\b', '', q)

    # Extract amenities
    amenities = {}
    if re.search(r'\b(?:ac|air\s*con(?:dition(?:ed|ing)?)?)\b', q):
        amenities['ac'] = True
        q = re.sub(r'\b(?:ac|air\s*con(?:dition(?:ed|ing)?)?)\b', '', q)
    if re.search(r'\bparking\b', q):
        amenities['parking'] = True
        q = re.sub(r'\bparking\b', '', q)
    if re.search(r'\b(?:wifi|wi-fi|internet)\b', q):
        amenities['wifi'] = True
        q = re.sub(r'\b(?:wifi|wi-fi|internet)\b', '', q)

    if amenities:
        filters['amenities'] = amenities

    # Extract town — match longest town name first to avoid partials (e.g. "Mount" vs "Mount Lavinia")
    q_clean = re.sub(r'\b(?:in|near|at|around|close to|nearby)\b', ' ', q)
    q_clean = re.sub(r'\s+', ' ', q_clean).strip()

    # Ensure towns are strings (handle potential bad data)
    safe_towns = [str(t) for t in SL_TOWNS if isinstance(t, str)]
    sorted_towns = sorted(safe_towns, key=len, reverse=True)
    
    found_town = None
    for town in sorted_towns:
        # Use word boundary mapping to avoid partial matches within words
        # and case-insensitive matching logic is already handled by lowercasing q
        # But we need to ensure the town regex is also case insensitive if town list has caps
        if re.search(r'\b' + re.escape(town.lower()) + r'\b', q_clean):
            found_town = town.title()
            break
            
    if found_town:
        filters['town'] = found_town

    return {
        'original_query': query,
        'parsed_filters': filters,
        'confidence': 'high' if len(filters) >= 2 else 'medium' if len(filters) == 1 else 'low'
    }

if __name__ == '__main__':
    # Set up UTF-8 encoding for stdin and stdout
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
             # Allow running without input for testing/import
             sys.exit(0)
             
        data = json.loads(input_data)
        query_input = data.get('query', '')
        result_output = parse_nlp_query(query_input)
        print(json.dumps(result_output))
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input", "confidence": "0"}))
    except Exception as e:
        print(json.dumps({"error": str(e), "confidence": "0"}))
