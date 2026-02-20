import sys
import json
import math

# Heuristic Coordinates for major hubs in SL (Longitude, Latitude)
HUBS = {
    "colombo": (79.8612, 6.9271),
    "kandy": (80.6337, 7.2906),
    "galle": (80.2170, 6.0367),
    "jaffna": (80.0074, 9.6615),
    "negombo": (79.8358, 7.2083),
}

def haversine(coord1, coord2):
    """Calculate the great circle distance between two points in km."""
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 6371  # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def estimate_commute(origin_town, destination_hub="colombo"):
    origin_town = origin_town.lower()
    destination_hub = destination_hub.lower()
    
    # Fallback coordinates if town not in HUBS (Randomized slight offset for realism)
    origin_coords = HUBS.get(origin_town)
    if not origin_coords:
        # Default to some offset from Colombo if unknown
        origin_coords = (79.9, 7.0)
        
    dest_coords = HUBS.get(destination_hub, HUBS["colombo"])
    
    distance = haversine(origin_coords, dest_coords)
    
    # Heuristic speeds (km/h)
    speeds = {
        "car": 40,
        "bus": 25,
        "train": 35
    }
    
    results = {}
    for mode, speed in speeds.items():
        time_hours = distance / speed
        # Add "overhead" time for traffic/stops (20-30 mins)
        time_mins = int((time_hours * 60) + 20)
        results[mode] = {
            "time": time_mins,
            "distance": round(distance, 1),
            "label": f"{time_mins} mins" if time_mins < 60 else f"{time_mins // 60}h {time_mins % 60}m"
        }
        
    return results

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)
            
        data = json.loads(input_data)
        town = data.get('town', 'Colombo')
        destination = data.get('destination', 'Colombo')
        
        commute_data = estimate_commute(town, destination)
        print(json.dumps(commute_data))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
