"""
Scam Detector — Specialized PII and scam detection for scraped listings.

Input (stdin JSON): { "listings": [{ title, description, price, ... }] }
Output (stdout JSON): {
    "results": [{ "sourceUrl": "...", "scamRiskScore": N, "piiDetected": bool, "piiDetails": [...], "flags": [...] }]
}
"""
import sys
import json
import re

# ──────────────────────────────────────────────
#   PII PATTERNS
# ──────────────────────────────────────────────

PATTERNS = {
    'phone_number': [
        re.compile(r'(?:\+94|0)\s*\d[\d\s\-]{7,12}'),
        re.compile(r'\b\d{3}[\s\-]\d{7}\b'),
        re.compile(r'\b0\d{9}\b'),
    ],
    'email': [
        re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    ],
    'whatsapp': [
        re.compile(r'(?:whatsapp|viber|imo|telegram)\s*[:\-]?\s*(?:\+94|0)?\s*\d[\d\s\-]{7,12}', re.I),
        re.compile(r'(?:call|contact|sms|text)\s*(?:me\s*)?[:\-]?\s*(?:\+94|0)\s*\d[\d\s\-]{7,12}', re.I),
    ],
    'nic_number': [
        re.compile(r'\b\d{9}[VXvx]\b'),
        re.compile(r'\b\d{12}\b'),
    ],
}

# Scam indicator patterns
SCAM_PATTERNS = {
    'urgency': [
        re.compile(r'\b(?:urgent|urgently|hurry|act\s*fast|limited\s*time|won\'?t\s*last|today\s*only)\b', re.I),
    ],
    'payment_fraud': [
        re.compile(r'\b(?:send\s*money|wire\s*transfer|western\s*union|money\s*gram|advance\s*payment|deposit\s*first)\b', re.I),
        re.compile(r'\b(?:before\s*(?:viewing|seeing)|pay\s*(?:now|first|before))\b', re.I),
    ],
    'overseas_scam': [
        re.compile(r'\b(?:overseas|abroad|out\s*of\s*(?:country|town)|can\'?t\s*(?:show|meet))\b', re.I),
        re.compile(r'\b(?:sight\s*unseen|without\s*visit)\b', re.I),
    ],
    'too_good': [
        re.compile(r'\b(?:free|giveaway|no\s*(?:charge|rent|payment))\b', re.I),
    ],
    'suspicious_contact': [
        re.compile(r'\b(?:only\s*(?:whatsapp|viber|call))\b', re.I),
    ],
}

def detect_all_pii(text):
    """Detect all types of PII in text."""
    detected = []
    for pii_type, patterns in PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text):
                detected.append(pii_type)
                break
    return detected

def detect_scam_flags(text, price=0, avg_price=0):
    """Detect scam indicators in text and pricing."""
    flags = []

    # Text-based scam patterns
    for flag_type, patterns in SCAM_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                flags.append({
                    'type': flag_type,
                    'matched': match.group(),
                    'severity': 'HIGH' if flag_type in ['payment_fraud', 'overseas_scam'] else 'MEDIUM',
                })
                break

    # Price-based flags
    if price > 0 and avg_price > 0:
        ratio = price / avg_price
        if ratio < 0.3:
            flags.append({
                'type': 'suspiciously_cheap',
                'matched': f'Price LKR {price:,} is less than 30% of avg LKR {avg_price:,}',
                'severity': 'HIGH',
            })
        elif ratio < 0.5:
            flags.append({
                'type': 'below_market',
                'matched': f'Price LKR {price:,} is less than 50% of avg LKR {avg_price:,}',
                'severity': 'MEDIUM',
            })

    return flags

def calculate_risk_score(pii, flags, has_images=True, desc_length=0):
    """Calculate overall scam risk score 0-100."""
    score = 0

    # PII in listing (+5 each)
    score += len(pii) * 5

    # Scam flags
    for flag in flags:
        if flag['severity'] == 'HIGH':
            score += 25
        elif flag['severity'] == 'MEDIUM':
            score += 10

    # No images
    if not has_images:
        score += 15

    # Very short description
    if desc_length < 20:
        score += 10
    elif desc_length < 50:
        score += 5

    return min(score, 100)

def analyze_listings(data):
    listings = data.get('listings', [])
    avg_price = data.get('avgPrice', 0)
    results = []

    for listing in listings:
        combined_text = f"{listing.get('title', '')} {listing.get('description', '')}"
        pii = detect_all_pii(combined_text)
        flags = detect_scam_flags(combined_text, listing.get('price', 0), avg_price)
        has_images = len(listing.get('images', [])) > 0
        desc_length = len(listing.get('description', ''))
        risk = calculate_risk_score(pii, flags, has_images, desc_length)

        results.append({
            'sourceUrl': listing.get('sourceUrl', ''),
            'title': listing.get('title', ''),
            'scamRiskScore': risk,
            'riskLevel': 'HIGH' if risk >= 50 else 'MEDIUM' if risk >= 25 else 'LOW',
            'piiDetected': len(pii) > 0,
            'piiDetails': pii,
            'flags': flags,
        })

    return {'results': results}

if __name__ == '__main__':
    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
            print(json.dumps({"error": "No input provided"}))
            sys.exit(1)
        data = json.loads(input_data)
        result = analyze_listings(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
