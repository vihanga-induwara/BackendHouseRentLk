import sys
import json

# Base prices for 1-bed unit in various towns (LKR)
BASE_MARKET_DATA = {
    "colombo": 85000,
    "colombo 03": 120000,
    "colombo 07": 150000,
    "dehiwala": 45000,
    "mount lavinia": 55000,
    "negombo": 35000,
    "kandy": 40000,
    "galle": 50000,
    "gampaha": 30000,
    "rajagiriya": 70000,
}

def suggest_price(data):
    town = data.get('town', 'Generic').lower()
    beds = int(data.get('beds', 1))
    baths = int(data.get('baths', 1))
    size = int(data.get('size', 1000))
    
    # Base price calculation
    base = BASE_MARKET_DATA.get(town, 30000)
    
    # Multipliers
    bed_multiplier = 1 + ((beds - 1) * 0.4)  # Each extra bed adds 40%
    bath_multiplier = 1 + ((baths - 1) * 0.15) # Each extra bath adds 15%
    
    # Size factor (normalized to 1000sqft baseline)
    size_factor = 1 + ((size - 1000) / 2000)  # Each 1000sqft adds ~50%
    
    suggested = base * bed_multiplier * bath_multiplier * size_factor
    
    # Round to nearest 500 for professionalism
    suggested = round(suggested / 500) * 500
    
    return {
        "suggestedPrice": suggested,
        "marketAvg": base,
        "confidence": "High" if town in BASE_MARKET_DATA else "Medium",
        "breakdown": {
            "baseForArea": base,
            "bedAdjustment": round((bed_multiplier - 1) * 100),
            "sizeAdjustment": round((size_factor - 1) * 100)
        }
    }

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)
            
        data = json.loads(input_data)
        result = suggest_price(data)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
