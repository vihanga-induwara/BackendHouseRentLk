import sys
import json

def calculate_match_score(renter_prefs, property_features):
    """
    Calculates a match score between 0 and 100 based on preferences.
    """
    total_score = 0
    max_score = 0
    
    # Weights for different factors
    WEIGHTS = {
        "town": 40,
        "price": 30,
        "beds": 20,
        "type": 10
    }
    
    # 1. Town Match (Exact)
    max_score += WEIGHTS["town"]
    if renter_prefs.get("town", "").lower() == property_features.get("town", "").lower():
        total_score += WEIGHTS["town"]
    
    # 2. Price Match
    max_score += WEIGHTS["price"]
    r_max_price = renter_prefs.get("maxPrice", float('inf'))
    p_price = property_features.get("price", 0)
    if p_price <= r_max_price:
        # Higher score if well below budget
        savings_ratio = (r_max_price - p_price) / r_max_price if r_max_price != 0 else 0
        total_score += WEIGHTS["price"] * (0.8 + (0.2 * min(savings_ratio, 1)))
    
    # 3. Beds Match
    max_score += WEIGHTS["beds"]
    r_beds = int(renter_prefs.get("beds", 1))
    p_beds = int(property_features.get("beds", 0))
    if p_beds >= r_beds:
        total_score += WEIGHTS["beds"]
    elif p_beds == r_beds - 1:
        total_score += WEIGHTS["beds"] * 0.5 # Partial match for one less bed
        
    # 4. Property Type Match
    max_score += WEIGHTS["type"]
    if renter_prefs.get("type", "Any").lower() == "any" or \
       renter_prefs.get("type", "").lower() == property_features.get("type", "").lower():
        total_score += WEIGHTS["type"]

    final_score = (total_score / max_score) * 100
    return round(final_score, 1)

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)
            
        data = json.loads(input_data)
        prefs = data.get('preferences', {})
        listing = data.get('listing', {})
        
        score = calculate_match_score(prefs, listing)
        
        result = {
            "matchScore": score,
            "matchLevel": "Excellent" if score > 85 else "Good" if score > 65 else "Fair" if score > 40 else "Poor",
            "highlights": [
                "Perfect Location" if prefs.get("town") == listing.get("town") else None,
                "Within Budget" if listing.get("price", 0) <= prefs.get("maxPrice", 0) else None,
                "Ideal Space" if listing.get("beds", 0) >= prefs.get("beds", 0) else None
            ]
        }
        # Filter out None values from highlights
        result["highlights"] = [h for h in result["highlights"] if h]
        
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
