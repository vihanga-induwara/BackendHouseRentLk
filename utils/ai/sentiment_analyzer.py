import sys
import json
import re

# Weighted sentiment dictionaries
POSITIVE_WORDS = {
    # Strong positive (weight 2)
    "excellent": 2, "amazing": 2, "perfect": 2, "outstanding": 2,
    "wonderful": 2, "fantastic": 2, "superb": 2, "love": 2,
    # Normal positive (weight 1)
    "good": 1, "great": 1, "nice": 1, "clean": 1, "safe": 1,
    "comfortable": 1, "friendly": 1, "responsive": 1, "helpful": 1,
    "spacious": 1, "quiet": 1, "peaceful": 1, "modern": 1,
    "well-maintained": 1, "convenient": 1, "affordable": 1,
    "recommend": 1, "decent": 1, "worth": 1, "beautiful": 1,
    "reliable": 1, "polite": 1, "pleasant": 1, "happy": 1,
    "satisfied": 1, "reasonable": 1, "best": 1,
}

NEGATIVE_WORDS = {
    # Strong negative (weight 2)
    "terrible": 2, "awful": 2, "horrible": 2, "worst": 2,
    "scam": 2, "fraud": 2, "fake": 2, "dangerous": 2,
    # Normal negative (weight 1)
    "bad": 1, "poor": 1, "dirty": 1, "noisy": 1, "expensive": 1,
    "rude": 1, "unsafe": 1, "broken": 1, "old": 1, "dark": 1,
    "small": 1, "cramped": 1, "overpriced": 1, "smelly": 1,
    "damp": 1, "leaking": 1, "slow": 1, "unresponsive": 1,
    "cockroach": 1, "mosquito": 1, "insects": 1, "bugs": 1,
    "mold": 1, "mould": 1, "disappointing": 1, "avoid": 1,
    "regret": 1, "waste": 1, "problem": 1, "issue": 1,
}

# Negation words that flip sentiment
NEGATION_WORDS = {"not", "no", "never", "don't", "doesn't", "didn't",
                  "isn't", "aren't", "wasn't", "weren't", "won't",
                  "can't", "couldn't", "shouldn't", "wouldn't"}


def analyze_sentiment(text):
    """
    Analyzes sentiment of a single review text.
    Returns score 0-100 (0=very negative, 50=neutral, 100=very positive).
    """
    if not text:
        return {"score": 50, "label": "neutral", "positiveCount": 0, "negativeCount": 0}

    words = re.findall(r'\b[\w\'-]+\b', text.lower())

    positive_score = 0
    negative_score = 0
    pos_count = 0
    neg_count = 0

    for i, word in enumerate(words):
        # Check for negation in previous 2 words
        negated = False
        for j in range(max(0, i - 2), i):
            if words[j] in NEGATION_WORDS:
                negated = True
                break

        if word in POSITIVE_WORDS:
            weight = POSITIVE_WORDS[word]
            if negated:
                negative_score += weight
                neg_count += 1
            else:
                positive_score += weight
                pos_count += 1

        elif word in NEGATIVE_WORDS:
            weight = NEGATIVE_WORDS[word]
            if negated:
                positive_score += weight
                pos_count += 1
            else:
                negative_score += weight
                neg_count += 1

    total = positive_score + negative_score
    if total == 0:
        normalized_score = 50  # Neutral
    else:
        normalized_score = int((positive_score / total) * 100)

    # Determine label
    if normalized_score >= 70:
        label = "positive"
    elif normalized_score >= 40:
        label = "neutral"
    else:
        label = "negative"

    return {
        "score": normalized_score,
        "label": label,
        "positiveCount": pos_count,
        "negativeCount": neg_count
    }


def analyze_reviews(reviews):
    """
    Analyzes sentiment across multiple reviews.
    """
    if not reviews:
        return {
            "overallScore": 50,
            "overallLabel": "neutral",
            "totalPositive": 0,
            "totalNegative": 0,
            "totalNeutral": 0,
            "reviewSentiments": []
        }

    sentiments = []
    total_score = 0
    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for review in reviews:
        text = review.get('comment', '')
        review_id = review.get('_id', '')
        result = analyze_sentiment(text)
        result['reviewId'] = review_id
        sentiments.append(result)
        total_score += result['score']

        if result['label'] == 'positive':
            positive_count += 1
        elif result['label'] == 'negative':
            negative_count += 1
        else:
            neutral_count += 1

    overall_score = int(total_score / len(reviews)) if reviews else 50

    if overall_score >= 70:
        overall_label = "positive"
    elif overall_score >= 40:
        overall_label = "neutral"
    else:
        overall_label = "negative"

    return {
        "overallScore": overall_score,
        "overallLabel": overall_label,
        "totalPositive": positive_count,
        "totalNegative": negative_count,
        "totalNeutral": neutral_count,
        "reviewSentiments": sentiments
    }


if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input"}))
            sys.exit(1)

        data = json.loads(input_data)

        # Support both single review and batch
        if 'reviews' in data:
            result = analyze_reviews(data['reviews'])
        else:
            result = analyze_sentiment(data.get('text', ''))

        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
