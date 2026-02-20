import sys
import json
import re
from typing import Dict, Any, List, Tuple

# Red flags / spam indicators
SPAM_PATTERNS: List[Tuple[str, str, str]] = [
    # Suspicious pricing
    # Use negative lookbehind (?<!...) to avoid matching "smoke free", "debt free", etc.
    # Python re requires fixed width lookbehind, so we chain them
    (r'\b(?<!smoke\s)(?<!debt\s)(?<!worry\s)(?<!hassle\s)(?<!break\s)(?<!rent\s)(?<!commission\s)free\b', 'price_suspicious', 'Claims property is free'),
    (r'\b(?:only|just)\s*(?:lkr\s*)?\d{2,3}\s*(?:per|/)\s*month', 'price_suspicious', 'Unrealistically low price claimed'),

    # Urgency scams
    (r'\b(?:send money|wire transfer|western union|moneygram)\b', 'payment_scam', 'Requests untraceable payment'),
    (r'\b(?:deposit|advance)\s*(?:first|before|prior)\b', 'payment_scam', 'Demands upfront payment'),
    (r'\b(?:available only today|last chance|act now|hurry|limited time)\b', 'urgency_scam', 'High-pressure urgency language'),

    # External links / contact redirection
    (r'https?://(?!cloudinary|youtube|maps\.google)', 'external_link', 'Contains suspicious external URL'),
    (r'\b(?:whatsapp me|call me|text me)\s*(?:at|on)\s*\+?\d{7,}', 'contact_redirect', 'Redirects contact outside platform'),

    # Profanity / inappropriate
    (r'\b(?:xxx|adult|escort|massage)\b', 'inappropriate', 'Contains inappropriate content'),

    # All caps abuse
    # Use (?-i:...) to force case-sensitive matching for uppercase letters
    (r'(?-i:[A-Z\s]{20,})', 'caps_abuse', 'Excessive use of capital letters'),

    # Emoji spam
    (r'[\U0001F600-\U0001F64F\U0001F680-\U0001F6FF]{5,}', 'emoji_spam', 'Excessive emoji usage'),

    # Repeated characters
    (r'(.)\1{5,}', 'char_repeat', 'Repeated characters detected'),

    # Phone number spam (too many numbers in description)
    (r'(?:\d{10,}.*){3,}', 'phone_spam', 'Multiple phone numbers in description'),
]

QUALITY_CHECKS = {
    'title_too_short': lambda d: len(d.get('title', '')) < 10,
    'desc_too_short': lambda d: len(d.get('description', '')) < 20,
    'title_all_caps': lambda d: d.get('title', '').isupper() and len(d.get('title', '')) > 5,
    'suspicious_price': lambda d: d.get('price', 0) > 0 and d.get('price', 0) < 1000,
    'extreme_price': lambda d: d.get('price', 0) > 1000000,
    'no_town': lambda d: not d.get('town', '').strip(),
}

def detect_spam(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a listing for spam, scam, and quality indicators.
    Returns a trust score (0-100) and list of flagged issues.
    """
    flags: List[Dict[str, Any]] = []
    score = 100

    title = listing_data.get('title', '')
    description = listing_data.get('description', '')
    combined_text = f"{title} {description}"

    # Pattern matching on combined text
    for pattern, flag_type, message in SPAM_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            severity = 'critical' if flag_type in ('payment_scam', 'inappropriate') else 'warning'
            deduction = 25 if severity == 'critical' else 10
            score -= deduction
            flags.append({
                'type': flag_type,
                'severity': severity,
                'message': message,
                'deduction': deduction
            })

    # Quality checks
    if QUALITY_CHECKS['title_too_short'](listing_data):
        score -= 5
        flags.append({
            'type': 'quality',
            'severity': 'info',
            'message': 'Title is very short. Consider adding more detail.',
            'deduction': 5
        })

    if QUALITY_CHECKS['desc_too_short'](listing_data):
        score -= 5
        flags.append({
            'type': 'quality',
            'severity': 'info',
            'message': 'Description is too short. Add more property details.',
            'deduction': 5
        })

    if QUALITY_CHECKS['title_all_caps'](listing_data):
        score -= 8
        flags.append({
            'type': 'formatting',
            'severity': 'warning',
            'message': 'Title is ALL CAPS. Use normal capitalization.',
            'deduction': 8
        })

    if QUALITY_CHECKS['suspicious_price'](listing_data):
        score -= 15
        flags.append({
            'type': 'price_suspicious',
            'severity': 'warning',
            'message': 'Price is unrealistically low (under LKR 1,000/month).',
            'deduction': 15
        })

    if QUALITY_CHECKS['extreme_price'](listing_data):
        score -= 10
        flags.append({
            'type': 'price_suspicious',
            'severity': 'warning',
            'message': 'Price is unusually high (over LKR 1,000,000/month).',
            'deduction': 10
        })

    if QUALITY_CHECKS['no_town'](listing_data):
        score -= 10
        flags.append({
            'type': 'quality',
            'severity': 'warning',
            'message': 'No town/location specified.',
            'deduction': 10
        })

    # Normalize
    score = max(0, min(100, score))

    if score >= 80:
        verdict = 'clean'
        label = 'Looks Good'
    elif score >= 50:
        verdict = 'suspicious'
        label = 'Needs Review'
    else:
        verdict = 'spam'
        label = 'Likely Spam'

    return {
        'trustScore': score,
        'verdict': verdict,
        'label': label,
        'flags': flags,
        'totalFlags': len(flags),
        'shouldAutoApprove': score >= 80,
        'shouldBlock': score < 30
    }

if __name__ == '__main__':
    try:
        input_data = json.loads(sys.stdin.read())
        result = detect_spam(input_data)
        print(json.dumps(result))
    except json.JSONDecodeError:
        print(json.dumps({"trustScore": 0, "verdict": "error", "error": "Invalid JSON"}))
    except Exception as e:
        print(json.dumps({"trustScore": 0, "verdict": "error", "error": str(e)}))
