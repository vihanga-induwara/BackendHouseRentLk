import sys
import json

def generate_comparison(listings):
    """
    Generate an AI comparison summary for 2+ listings.
    Analyzes price, value, location, amenities, and recommends winner.
    """
    if len(listings) < 2:
        return {
            'summary': 'Need at least 2 listings to compare.',
            'winner': None,
            'insights': []
        }

    insights = []
    scores = {}

    # Initialize scores
    for i, l in enumerate(listings):
        scores[i] = {'total': 0, 'reasons': [], 'title': l.get('title', f'Property {i+1}')}

    # --- Price Analysis ---
    prices = [l.get('price', 0) for l in listings]
    min_price = min(prices)
    max_price = max(prices)

    if max_price > 0 and max_price != min_price:
        cheapest_idx = prices.index(min_price)
        savings = max_price - min_price
        savings_pct = round((savings / max_price) * 100)
        insights.append({
            'category': 'Price',
            'icon': '💰',
            'text': f'{scores[cheapest_idx]["title"]} is the most affordable, saving you LKR {savings:,} ({savings_pct}%) compared to the priciest option.'
        })
        scores[cheapest_idx]['total'] += 20
        scores[cheapest_idx]['reasons'].append('Best price')
    else:
        insights.append({
            'category': 'Price',
            'icon': '💰',
            'text': 'All properties are similarly priced — focus on value-adds like amenities and location.'
        })

    # --- Size / Value Analysis ---
    sizes = [l.get('size', 0) for l in listings]
    if all(s > 0 for s in sizes):
        value_ratios = [(p / s if s > 0 else float('inf')) for p, s in zip(prices, sizes)]
        best_value_idx = value_ratios.index(min(value_ratios))
        insights.append({
            'category': 'Value',
            'icon': '📐',
            'text': f'{scores[best_value_idx]["title"]} offers the best value per sqft at LKR {round(min(value_ratios))}/sqft.'
        })
        scores[best_value_idx]['total'] += 15
        scores[best_value_idx]['reasons'].append('Best value/sqft')

    # --- Space Analysis ---
    beds_list = [l.get('beds', 0) for l in listings]
    baths_list = [l.get('baths', 0) for l in listings]

    if max(beds_list) != min(beds_list):
        most_space_idx = beds_list.index(max(beds_list))
        insights.append({
            'category': 'Space',
            'icon': '🛏️',
            'text': f'{scores[most_space_idx]["title"]} has the most bedrooms ({max(beds_list)}). Ideal for families.'
        })
        scores[most_space_idx]['total'] += 10
        scores[most_space_idx]['reasons'].append('Most bedrooms')

    # --- Amenity Analysis ---
    for i, l in enumerate(listings):
        amenities = l.get('amenities', {})
        amenity_count = sum(1 for v in amenities.values() if v is True)
        scores[i]['amenity_count'] = amenity_count

    amenity_counts = [scores[i].get('amenity_count', 0) for i in range(len(listings))]
    if max(amenity_counts) > min(amenity_counts):
        best_amenity_idx = amenity_counts.index(max(amenity_counts))
        insights.append({
            'category': 'Amenities',
            'icon': '✨',
            'text': f'{scores[best_amenity_idx]["title"]} offers the most amenities ({max(amenity_counts)} features). Best equipped.'
        })
        scores[best_amenity_idx]['total'] += 10
        scores[best_amenity_idx]['reasons'].append('Most amenities')

    # --- Furnished Status ---
    furnished_options = [l.get('furnished', 'Unfurnished') for l in listings]
    furnished_listings = [i for i, f in enumerate(furnished_options) if f == 'Furnished']
    if furnished_listings and len(furnished_listings) < len(listings):
        insights.append({
            'category': 'Convenience',
            'icon': '🛋️',
            'text': f'{scores[furnished_listings[0]]["title"]} comes fully furnished — move in with zero setup cost.'
        })
        scores[furnished_listings[0]]['total'] += 10
        scores[furnished_listings[0]]['reasons'].append('Fully furnished')

    # --- Determine Winner ---
    winner_idx = max(scores.keys(), key=lambda k: scores[k]['total'])
    runner_up_idx = sorted(scores.keys(), key=lambda k: scores[k]['total'], reverse=True)[1] if len(listings) > 1 else None

    # Build summary text
    winner_title = scores[winner_idx]['title']
    winner_reasons = scores[winner_idx]['reasons']

    summary_parts = [
        f"**{winner_title}** comes out on top",
    ]
    if winner_reasons:
        summary_parts.append(f"with advantages in: {', '.join(winner_reasons)}.")
    else:
        summary_parts.append("as the most well-rounded option.")

    if runner_up_idx is not None:
        runner_title = scores[runner_up_idx]['title']
        runner_reasons = scores[runner_up_idx]['reasons']
        if runner_reasons:
            summary_parts.append(f"{runner_title} is a close runner-up, excelling in {', '.join(runner_reasons)}.")

    return {
        'summary': ' '.join(summary_parts),
        'winner': {
            'index': winner_idx,
            'title': winner_title,
            'score': scores[winner_idx]['total'],
            'reasons': winner_reasons
        },
        'insights': insights,
        'scores': {i: {'title': s['title'], 'score': s['total'], 'reasons': s['reasons']} for i, s in scores.items()}
    }

if __name__ == '__main__':
    input_data = json.loads(sys.stdin.read())
    listings = input_data.get('listings', [])
    result = generate_comparison(listings)
    print(json.dumps(result))
