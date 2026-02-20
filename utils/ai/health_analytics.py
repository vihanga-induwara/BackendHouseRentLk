import sys
import json
import random

def generate_health_metrics(listings_data):
    """
    Simulates platform analytics based on current listings.
    """
    # Group listings by town for heatmap data
    town_activity = {}
    for l in listings_data:
        town = l.get('location', {}).get('town', 'Unknown')
        town_activity[town] = town_activity.get(town, 0) + 1
        
    # Generate mock conversion data
    hubs = ["Colombo 03", "Dehiwala", "Negombo", "Gampaha", "Kandy"]
    heatmap_data = []
    for hub in hubs:
        demand = random.randint(30, 95)
        supply = town_activity.get(hub, random.randint(5, 40))
        heatmap_data.append({
            "town": hub,
            "demandScore": demand,
            "supplyCount": supply,
            "ratio": round(demand / max(supply, 1), 2)
        })
        
    return {
        "platformPulse": {
            "totalActivity": sum(town_activity.values()),
            "overallScamRisk": 0.02, # 2% simulated risk
            "growthRate": "12.4% MoM"
        },
        "heatmap": heatmap_data,
        "recommendations": [
            "Increase supply in highly active hubs" if heatmap_data[0]["ratio"] > 2 else "Market stable",
            "Owner verification incentive needed in new towns"
        ]
    }

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)
            
        data = json.loads(input_data)
        listings = data.get('listings', [])
        
        result = generate_health_metrics(listings)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
