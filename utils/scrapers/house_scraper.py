"""
house.lk Rental Listing Scraper
Input (stdin JSON): { "maxPages": 3, "location": "", "priceMin": 0, "priceMax": 0 }
Output (stdout JSON): { "listings": [...], "stats": {...}, "errors": [...] }
"""
import sys, json, time, re

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print(json.dumps({"error": "Missing deps. Run: pip install requests beautifulsoup4 lxml"}))
    sys.exit(1)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}
BASE_URL = "https://www.house.lk"
SEARCH_URL = "https://www.house.lk/rent"

PHONE_RE = re.compile(r'(?:\+94|0)\s*\d[\d\s\-]{7,12}')
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

DISTRICT_MAP = {
    'colombo': 'Western', 'gampaha': 'Western', 'kalutara': 'Western',
    'kandy': 'Central', 'galle': 'Southern', 'matara': 'Southern',
    'jaffna': 'Northern', 'kurunegala': 'North Western',
    'anuradhapura': 'North Central', 'badulla': 'Uva',
    'ratnapura': 'Sabaragamuwa', 'batticaloa': 'Eastern',
}

def detect_pii(t):
    d = []
    if PHONE_RE.search(t): d.append('phone_number')
    if EMAIL_RE.search(t): d.append('email')
    return d

def strip_pii(t):
    return EMAIL_RE.sub('[REDACTED]', PHONE_RE.sub('[REDACTED]', t))

def guess_district(t):
    for d, p in DISTRICT_MAP.items():
        if d in t.lower(): return d.title(), p
    return '', ''

def parse_price(t):
    if not t: return 0
    try: return int(re.sub(r'[^\d]', '', t))
    except: return 0

def scrape_house(config):
    max_pages = config.get('maxPages', 3)
    rate_limit = config.get('rateLimit', 2000)
    
    listings, errors = [], []
    stats = {'pagesScraped': 0, 'totalFound': 0, 'errors': 0}

    for page in range(1, max_pages + 1):
        url = SEARCH_URL
        if page > 1: url += f"?page={page}"

        try:
            time.sleep(rate_limit / 1000.0)
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'lxml')
        except Exception as e:
            errors.append({'page': page, 'message': str(e), 'source': 'house'})
            stats['errors'] += 1
            continue

        stats['pagesScraped'] += 1
        cards = soup.select('.property-item, .listing-item, .property-card, [class*="property-list"]')
        if not cards:
            cards = soup.select('div[class*="listing"], div[class*="property"]')

        for card in cards:
            try:
                title_el = card.select_one('h2, h3, .title, a[class*="title"]')
                title = title_el.get_text(strip=True) if title_el else ''
                if not title: continue

                link_el = card.select_one('a[href]')
                href = link_el.get('href', '') if link_el else ''
                if href and not href.startswith('http'): href = BASE_URL + href

                price_el = card.select_one('.price, [class*="price"]')
                price = parse_price(price_el.get_text(strip=True) if price_el else '')

                loc_el = card.select_one('.location, [class*="location"], .address')
                raw_loc = loc_el.get_text(strip=True) if loc_el else ''
                town = raw_loc.split(',')[0].strip() if raw_loc else ''
                district, province = guess_district(raw_loc)

                desc_el = card.select_one('.description, p')
                desc = desc_el.get_text(strip=True) if desc_el else ''

                img_el = card.select_one('img[src]')
                img = img_el.get('src', '') if img_el else ''
                images = [img] if img and 'placeholder' not in img.lower() else []

                ft = f"{title} {desc}"
                beds = int(m.group(1)) if (m := re.search(r'(\d+)\s*(?:bed|br)', ft, re.I)) else 0
                baths = int(m.group(1)) if (m := re.search(r'(\d+)\s*bath', ft, re.I)) else 0
                size = int(m.group(1)) if (m := re.search(r'(\d+)\s*(?:sq|perch)', ft, re.I)) else 0

                lt = 'Unknown'
                tl = title.lower()
                if 'house' in tl: lt = 'House'
                elif 'apartment' in tl: lt = 'Apartment'
                elif 'annex' in tl: lt = 'Annex'
                elif 'room' in tl: lt = 'Boarding Room'

                pii = detect_pii(f"{title} {desc}")
                listings.append({
                    'title': strip_pii(title), 'description': strip_pii(desc),
                    'price': price,
                    'location': {'town': town, 'district': district, 'province': province, 'rawAddress': raw_loc},
                    'beds': beds, 'baths': baths, 'size': size,
                    'type': lt, 'furnished': 'Unknown', 'images': images,
                    'sourceUrl': href, 'sourceId': href.split('/')[-1] if href else '',
                    'piiDetected': len(pii) > 0, 'piiDetails': pii,
                })
                stats['totalFound'] += 1
            except Exception as e:
                errors.append({'page': page, 'message': str(e), 'source': 'house'})
                stats['errors'] += 1

    return {'listings': listings, 'stats': stats, 'errors': errors, 'source': 'house.lk'}

if __name__ == '__main__':
    try:
        inp = sys.stdin.read().strip()
        config = json.loads(inp) if inp else {}
        print(json.dumps(scrape_house(config), ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
