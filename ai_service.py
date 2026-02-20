import sys
import json
import os

# ────────────────────────────────────────────────
#   KNOWLEDGE BASE – defined at the top
# ────────────────────────────────────────────────

knowledge_base = {
    "negombo": [
        "Negombo is a lively city by the sea with nice beaches and many fish markets.",
        "It has old buildings from colonial times and new hotels and eateries.",
        "It is close to the airport, so it is easy for travelers to reach."
    ],
    "colombo": [
        "Colombo is the busy main city of Sri Lanka with lots of business and shops.",
        "It has old and new buildings, malls, and many places to eat different foods.",
        "It is good for work and fun, with many people living a city life."
    ],
    "kandy": [
        "Kandy is a city with lots of culture, hills, and tea farms around it.",
        "It has the important Temple of the Tooth and a calm feel.",
        "The weather is cool, and it is nice for people who want peace."
    ],
    "galle": [
        "Galle is an old city with a big Dutch fort that is protected by UNESCO.",
        "It has nice buildings, art shops, and small cafes.",
        "The beaches are pretty, and it has a relaxed vibe for living."
    ],
    "gampaha": [
        "Gampaha is a growing city with green areas and gardens.",
        "It has good schools and hospitals for families.",
        "It is connected to Colombo, so commuting is easy."
    ],
    # ... (you can keep ALL the other entries you had – I shortened it here for clarity)
    "boralesgamuwa": [
        "Boralesgamuwa has lakes and parks.",
        "It offers homes and schools.",
        "It is near Colombo."
    ],
    # Add the rest back as needed
}

def generate_town_vibe(town):
    """
    Generates a vibe description for a town based on the knowledge base.
    """
    if not town:
        return "A pleasant location in Sri Lanka with access to basic amenities and community facilities."

    town = town.lower().strip()

    matched_town = None
    for key in knowledge_base:
        if key in town or town in key:
            matched_town = key
            break

    if matched_town:
        assert matched_town is not None  # narrow type from str | None → str
        # Join the list of sentences into one coherent paragraph
        vibe = " ".join(knowledge_base[matched_town])
    else:
        # Generic fallback
        town_cap = town.title()
        vibe = (
            f"{town_cap} is a growing town with improving infrastructure and "
            "community facilities. It offers a developing residential environment "
            "suitable for families. The area is seeing new commercial establishments, "
            "making daily life more convenient."
        )

    return vibe


def generate_description(data):
    """
    Generates a property description based on provided data.
    """
    title = data.get('title', 'Property')
    p_type = data.get('type', 'Property')
    beds = data.get('beds', 0)
    baths = data.get('baths', 0)
    price = data.get('price', 0)
    amenities = data.get('amenities', {})
    location = data.get('location', {}).get('town', 'Sri Lanka')

    # Rule-Based Expert System for Description Generation
    adjectives = ["charming", "spacious", "modern", "cozy", "luxurious", "budget-friendly", "convenient"]

    # 1. Opening Hook based on Price and Type
    rating = "luxury" if price > 100000 else "mid-range" if price > 40000 else "affordable"

    opening = ""
    if rating == "luxury":
        opening = f"Experience premium living in this elegant {beds}-bedroom {p_type.lower()}."
    elif rating == "affordable":
        opening = f"Looking for value? Check out this wallet-friendly {beds}-bedroom {p_type.lower()} in {location}."
    else:
        opening = f"A perfect balance of comfort and style, this {p_type.lower()} in {location} offers everything a family needs."

    # 2. Features Paragraph
    size = data.get('size', 'a spacious area')
    features_text = f"This property boasts {beds} bedrooms and {baths} bathrooms, spanning {size} sqft."

    if data.get('furnished') == 'Furnished':
        features_text += " It comes fully furnished, ready for you to move in immediately."
    elif data.get('furnished') == 'Semi-Furnished':
        features_text += " Semi-furnished with essential fittings included."

    # 3. Amenities Logic
    amenity_highlights: list[str] = []
    if amenities.get('ac'):              amenity_highlights.append("air conditioning for those hot days")
    if amenities.get('solarPower'):      amenity_highlights.append("solar power to save on electricity bills")
    if amenities.get('garden'):          amenity_highlights.append("a private garden for relaxation")
    if amenities.get('servantQuarters'): amenity_highlights.append("dedicated servant quarters")
    if amenities.get('waterSupply') in ['Well', 'Both']:
        amenity_highlights.append("reliable well water supply")

    amenity_text = ""
    if amenity_highlights:
        if len(amenity_highlights) == 1:
            amenity_text = f"Key highlight: {amenity_highlights[0]}."
        else:
            highlights_copy = list(amenity_highlights)
            last: str = highlights_copy.pop()
            rest = ", ".join(highlights_copy)
            amenity_text = f"Key highlights include {rest} and {last}."

    else:
        amenity_text = "The property includes all standard amenities for a comfortable stay."

    # 4. Location Context
    loc_text = f"Situated in {location}, you are close to local shops and transport links."
    if amenities.get('templeDistance'):
        loc_text += f" Only {amenities['templeDistance']}km from the nearest temple."
    if amenities.get('mainRoadDistance'):
        loc_text += f" Just {amenities['mainRoadDistance']}km to the main road."

    # 5. Call to Action
    cta = f"Available now for LKR {price:,}/month. Don't miss this opportunity in {location}!"

    description = f"{opening} {features_text} {amenity_text} {loc_text} {cta}"

    return description.strip()


if __name__ == "__main__":
    try:
        # Read input from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            print(json.dumps({"error": "No input provided"}))
            sys.exit(1)

        data = json.loads(input_data)

        town = data.get('location', {}).get('town', '')

        result = {
            "description": generate_description(data),
            "townVibe": generate_town_vibe(town)
        }

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)