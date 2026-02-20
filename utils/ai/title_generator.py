import sys
import json
import random

# Adjective pools by price tier
ADJECTIVES = {
    "luxury": ["Elegant", "Premium", "Luxurious", "Upscale", "Exclusive"],
    "mid": ["Modern", "Comfortable", "Stylish", "Well-Maintained", "Spacious"],
    "budget": ["Affordable", "Budget-Friendly", "Cozy", "Compact", "Value-Packed"]
}

# Hook templates based on tenant type
HOOKS = {
    "Students": [
        "Ideal for Students",
        "Perfect for University Students",
        "Student-Friendly",
        "Near Educational Institutes"
    ],
    "Family": [
        "Perfect for Families",
        "Family-Friendly Home",
        "Ideal Family Living",
        "Great for Growing Families"
    ],
    "Professionals": [
        "Ideal for Working Professionals",
        "Close to CBD",
        "Perfect for Young Professionals",
        "Convenient City Living"
    ],
    "Any": [
        "Ready to Move In",
        "Don't Miss This!",
        "Great Location",
        "Excellent Opportunity"
    ]
}

# Type display names
TYPE_DISPLAY = {
    "House": "House",
    "Boarding Room": "Boarding Room",
    "Annex": "Annex",
    "Apartment": "Apartment",
    "Other": "Property"
}

# Amenity highlights for title
AMENITY_KEYWORDS = {
    "ac": "A/C",
    "wifi": "WiFi",
    "parking": "Parking",
    "garden": "Garden",
    "solarPower": "Solar Power",
    "attachedBath": "Attached Bath",
    "security": "24/7 Security"
}


def generate_title(data):
    """
    Generates catchy, SEO-optimized property titles.
    """
    p_type = data.get('type', 'Property')
    beds = int(data.get('beds', 0))
    baths = int(data.get('baths', 0))
    town = data.get('town', '')
    price = int(data.get('price', 0))
    tenant_type = data.get('tenantType', 'Any')
    amenities = data.get('amenities', {})
    furnished = data.get('furnished', 'Unfurnished')

    # Determine price tier
    if price > 100000:
        tier = "luxury"
    elif price > 40000:
        tier = "mid"
    else:
        tier = "budget"

    type_name = TYPE_DISPLAY.get(p_type, "Property")
    hooks = HOOKS.get(tenant_type, HOOKS["Any"])

    # Pick top amenity for title
    top_amenity = ""
    for key, label in AMENITY_KEYWORDS.items():
        if amenities.get(key):
            top_amenity = label
            break

    furnished_tag = ""
    if furnished == "Furnished":
        furnished_tag = "Fully Furnished"
    elif furnished == "Semi-Furnished":
        furnished_tag = "Semi-Furnished"

    titles = []

    # Pattern 1: "[Adj] [Beds]BR [Type] in [Town] – [Hook]"
    adj1 = random.choice(ADJECTIVES[tier])
    hook1 = random.choice(hooks)
    title1 = f"{adj1} {beds}BR {type_name} in {town.title()} – {hook1}"
    titles.append(title1)

    # Pattern 2: "[Furnished] [Beds]-Bedroom [Type] Near [Town] | [Amenity]"
    adj2 = random.choice(ADJECTIVES[tier])
    parts2 = []
    if furnished_tag:
        parts2.append(furnished_tag)
    parts2.append(f"{beds}-Bedroom {type_name} in {town.title()}")
    if top_amenity:
        title2 = " ".join(parts2) + f" | {top_amenity} Included"
    else:
        title2 = " ".join(parts2) + f" | {random.choice(hooks)}"
    titles.append(title2)

    # Pattern 3: "For Rent: [Adj] [Type] in [Town] – [Beds]BR, [Baths]Bath"
    adj3 = random.choice(ADJECTIVES[tier])
    title3 = f"For Rent: {adj3} {type_name} in {town.title()} – {beds}BR, {baths}Bath"
    titles.append(title3)

    return {
        "title": titles[0],
        "alternatives": titles[1:]
    }


if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)

        data = json.loads(input_data)
        result = generate_title(data)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
