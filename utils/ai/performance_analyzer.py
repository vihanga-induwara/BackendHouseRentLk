import sys
import json


def analyze_performance(listing, peer_stats):
    """
    Analyzes a listing's performance relative to peers in the same town/type.
    Returns actionable AI insights.
    """
    suggestions = []
    score = 50  # Start at baseline

    views = listing.get('views', 0)
    shares = listing.get('shares', 0)
    images_count = len(listing.get('images', []))
    price = listing.get('price', 0)
    title = listing.get('title', '')
    description = listing.get('description', '')
    has_video = bool(listing.get('video'))
    furnished = listing.get('furnished', 'Unfurnished')

    peer_avg_views = peer_stats.get('avgViews', 50)
    peer_avg_images = peer_stats.get('avgImages', 4)
    peer_avg_price = peer_stats.get('avgPrice', 40000)
    peer_count = peer_stats.get('count', 1)
    inquiries = listing.get('inquiryCount', 0)
    favorites = listing.get('favoriteCount', 0)

    # 1. Views analysis
    if peer_avg_views > 0:
        view_ratio = views / max(peer_avg_views, 1)
        if view_ratio >= 1.5:
            score += 15
        elif view_ratio >= 0.8:
            score += 8
        else:
            suggestions.append(
                f"Your listing has {views} views vs. the area average of {int(peer_avg_views)}. "
                "Consider sharing on social media to boost visibility."
            )
            score -= 5

    # 2. Image analysis
    if images_count < 3:
        suggestions.append(
            f"Add more photos! You have {images_count}, but top listings average "
            f"{int(peer_avg_images)}. Listings with 5+ photos get 3x more inquiries."
        )
        score -= 10
    elif images_count >= 5:
        score += 10
    else:
        score += 5

    # 3. Video bonus
    if has_video:
        score += 5
    else:
        suggestions.append(
            "Add a video walkthrough — listings with video get 40% more engagement."
        )

    # 4. Price positioning
    if peer_avg_price > 0:
        price_diff_pct = ((price - peer_avg_price) / peer_avg_price) * 100
        if price_diff_pct > 20:
            suggestions.append(
                f"Your price is {int(price_diff_pct)}% above the area average (LKR {int(peer_avg_price):,}). "
                "Consider adjusting to attract more inquiries."
            )
            score -= 10
        elif price_diff_pct < -15:
            score += 10  # Great deal, will attract attention
        else:
            score += 5

    # 5. Title quality
    if len(title) < 20:
        suggestions.append(
            "Your title is too short. Include location, bedrooms, and a key feature "
            "for better SEO. E.g., 'Modern 2BR Apartment in Colombo 03 – Fully Furnished'"
        )
        score -= 5
    elif len(title) > 30:
        score += 5

    # 6. Description length
    if len(description) < 100:
        suggestions.append(
            "Write a more detailed description (at least 200 characters). "
            "Mention amenities, nearby landmarks, and transport links."
        )
        score -= 5
    elif len(description) > 300:
        score += 5

    # 7. Furnished bonus
    if furnished == 'Furnished':
        score += 5

    # 8. Inquiry rate
    if views > 10:
        inquiry_rate = (inquiries / views) * 100
        if inquiry_rate < 2:
            suggestions.append(
                f"Your inquiry rate is {inquiry_rate:.1f}%. "
                "Improve your photos and description to convert more viewers."
            )
        elif inquiry_rate > 5:
            score += 10

    # Clamp score
    score = max(0, min(100, score))

    # Determine rank label
    if score >= 80:
        rank = "Excellent"
    elif score >= 60:
        rank = "Good"
    elif score >= 40:
        rank = "Average"
    else:
        rank = "Needs Improvement"

    if not suggestions:
        suggestions.append("Your listing is performing well! Keep it updated to maintain engagement.")

    return {
        "score": score,
        "rank": rank,
        "suggestions": suggestions[:5],  # Max 5 suggestions
        "metrics": {
            "views": views,
            "peerAvgViews": int(peer_avg_views),
            "inquiries": inquiries,
            "favorites": favorites,
            "imageCount": images_count,
            "peerAvgImages": int(peer_avg_images),
            "inquiryRate": round((inquiries / max(views, 1)) * 100, 1),
            "competingListings": peer_count
        }
    }


if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)

        data = json.loads(input_data)
        listing = data.get('listing', {})
        peer_stats = data.get('peerStats', {})

        result = analyze_performance(listing, peer_stats)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
