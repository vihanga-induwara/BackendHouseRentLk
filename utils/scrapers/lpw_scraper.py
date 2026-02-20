"""
LankaPropertyWeb.com Rental Listing Scraper
Input (stdin JSON): { "maxPages": 3, "location": "", "priceMin": 0, "priceMax": 0 }
Output (stdout JSON): { "listings": [...], "stats": {...}, "errors": [...] }
"""
import sys
import json
import time
import re

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print(json.dumps({"error": "Missing deps. Run: pip install requests beautifulsoup4 lxml"}))
    sys.exit(1)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

BASE_URL = "https://www.lankapropertyweb.com"
SEARCH_URL = "https://www.lankapropertyweb.com/rent/houses-for-rent.php"

PHONE_PATTERN = re.compile(r'(?:\+94|0)\s*\d[\d\s\-]{7,12}')
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

DISTRICT_PROVINCE_MAP = {
    'colombo': 'Western', 'gampaha': 'Western', 'kalutara': 'Western',
    'kandy': 'Central', 'matale': 'Central', 'nuwara eliya': 'Central',
    'galle': 'Southern', 'matara': 'Southern', 'hambantota': 'Southern',
    'jaffna': 'Northern', 'kurunegala': 'North Western', 'puttalam': 'North Western',
    'anuradhapura': 'North Central', 'polonnaruwa': 'North Central',
    'badulla': 'Uva', 'ratnapura': 'Sabaragamuwa', 'kegalle': 'Sabaragamuwa',
    'batticaloa': 'Eastern', 'ampara': 'Eastern', 'trincomalee': 'Eastern',
}

def detect_pii(text):
    detected = []
    if PHONE_PATTERN.search(text): detected.append('phone_number')
    if EMAIL_PATTERN.search(text): detected.append('email')
    return detected

def strip_pii(text):
    text = PHONE_PATTERN.sub('[REDACTED]', text)
    text = EMAIL_PATTERN.sub('[REDACTED]', text)
    return text

def guess_district(text):
    for district, province in DISTRICT_PROVINCE_MAP.items():
        if district in text.lower():
            return district.title(), province
    return '', ''

def parse_price(text):
    if not text: return 0
    cleaned = re.sub(r'[^\d]', '', text)
    try: return int(cleaned)
    except ValueError: return 0

def scrape_lpw(config):
    max_pages = config.get('maxPages', 3)
    location = config.get('location', '')
    rate_limit = config.get('rateLimit', 2000)

    listings = []
    errors = []
    stats = {'pagesScraped': 0, 'totalFound': 0, 'errors': 0}

    for page in range(1, max_pages + 1):
        url = SEARCH_URL
        if page > 1:
            url += f"?page={page}"
        if location:
            url = f"{BASE_URL}/rent/{location.lower().replace(' ', '-')}.php"
            if page > 1:
                url += f"?page={page}"

        try:
            time.sleep(rate_limit / 1000.0)
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
        except Exception as e:
            errors.append({'page': page, 'message': str(e), 'source': 'lpw'})
            stats['errors'] += 1
            continue

        stats['pagesScraped'] += 1

        # LPW uses property listing cards
        cards = soup.select('.property-item, .listing-item, .property-card, .result-item, li.property')
        if not cards:
            cards = soup.select('[class*="property"], [class*="listing"]')

        for card in cards:
            try:
                title_el = card.select_one('h2 a, h3 a, .title a, a.property-title')
                title = title_el.get_text(strip=True) if title_el else ''
                if not title:
                    continue

                href = ''
                if title_el and title_el.get('href'):
                    href = title_el['href']
                    if not href.startswith('http'):
                        href = BASE_URL + href

                price_el = card.select_one('.price, [class*="price"]')
                price = parse_price(price_el.get_text(strip=True) if price_el else '')

                loc_el = card.select_one('.location, [class*="location"], .address')
                raw_loc = loc_el.get_text(strip=True) if loc_el else ''
                town = raw_loc.split(',')[0].strip() if raw_loc else ''
                district, province = guess_district(raw_loc)

                desc_el = card.select_one('.description, p, .details')
                description = desc_el.get_text(strip=True) if desc_el else ''

                img_el = card.select_one('img[src]')
                image_url = img_el.get('src', '') if img_el else ''
                images = [image_url] if image_url and 'placeholder' not in image_url.lower() else []

                full_text = f"{title} {description}"
                beds = int(m.group(1)) if (m := re.search(r'(\d+)\s*(?:bed|br|bedroom)', full_text, re.I)) else 0
                baths = int(m.group(1)) if (m := re.search(r'(\d+)\s*(?:bath)', full_text, re.I)) else 0
                size = int(m.group(1)) if (m := re.search(r'(\d+)\s*(?:sq|perch)', full_text, re.I)) else 0

                listing_type = 'Unknown'
                tl = title.lower()
                if 'house' in tl: listing_type = 'House'
                elif 'apartment' in tl or 'flat' in tl: listing_type = 'Apartment'
                elif 'annex' in tl: listing_type = 'Annex'
                elif 'room' in tl: listing_type = 'Boarding Room'

                combined = f"{title} {description}"
                pii = detect_pii(combined)

                listings.append({
                    'title': strip_pii(title),
                    'description': strip_pii(description),
                    'price': price,
                    'location': {'town': town, 'district': district, 'province': province, 'rawAddress': raw_loc},
                    'beds': beds, 'baths': baths, 'size': size,
                    'type': listing_type, 'furnished': 'Unknown',
                    'images': images,
                    'sourceUrl': href,
                    'sourceId': href.split('/')[-1].split('.')[0] if href else '',
                    'piiDetected': len(pii) > 0,
                    'piiDetails': pii,
                })
                stats['totalFound'] += 1
            except Exception as e:
                errors.append({'page': page, 'message': str(e), 'source': 'lpw'})
                stats['errors'] += 1

    return {'listings': listings, 'stats': stats, 'errors': errors, 'source': 'lankapropertyweb.com'}

if __name__ == '__main__':
    try:
        input_data = sys.stdin.read().strip()
        config = json.loads(input_data) if input_data else {}
        result = scrape_lpw(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
