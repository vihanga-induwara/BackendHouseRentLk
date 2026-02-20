"""
ikman.lk Rental Listing Scraper
Scrapes property rental listings from ikman.lk
Input (stdin JSON): { "maxPages": 3, "location": "", "priceMin": 0, "priceMax": 0 }
Output (stdout JSON): { "listings": [...], "stats": {...} }
"""
import sys
import json
import time
import re

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print(json.dumps({"error": "Missing dependencies. Run: pip install requests beautifulsoup4 lxml"}))
    sys.exit(1)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

BASE_URL = "https://ikman.lk"
SEARCH_URL = "https://ikman.lk/en/ads/sri-lanka/properties?type=rent"

# PII regex patterns
PHONE_PATTERN = re.compile(r'(?:\+94|0)\s*\d[\d\s\-]{7,12}')
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
WHATSAPP_PATTERN = re.compile(r'(?:whatsapp|viber|call|contact)\s*[:\-]?\s*(?:\+94|0)\s*\d[\d\s\-]{7,12}', re.IGNORECASE)

# Sri Lanka location mapping
DISTRICT_PROVINCE_MAP = {
    'colombo': 'Western', 'gampaha': 'Western', 'kalutara': 'Western',
    'kandy': 'Central', 'matale': 'Central', 'nuwara eliya': 'Central',
    'galle': 'Southern', 'matara': 'Southern', 'hambantota': 'Southern',
    'jaffna': 'Northern', 'kilinochchi': 'Northern', 'mannar': 'Northern',
    'mullaitivu': 'Northern', 'vavuniya': 'Northern',
    'batticaloa': 'Eastern', 'ampara': 'Eastern', 'trincomalee': 'Eastern',
    'kurunegala': 'North Western', 'puttalam': 'North Western',
    'anuradhapura': 'North Central', 'polonnaruwa': 'North Central',
    'badulla': 'Uva', 'monaragala': 'Uva',
    'ratnapura': 'Sabaragamuwa', 'kegalle': 'Sabaragamuwa',
}

def detect_pii(text):
    """Detect personal info in text and return list of detected types."""
    detected = []
    if PHONE_PATTERN.search(text):
        detected.append('phone_number')
    if EMAIL_PATTERN.search(text):
        detected.append('email')
    if WHATSAPP_PATTERN.search(text):
        detected.append('whatsapp')
    return detected

def strip_pii(text):
    """Remove PII from text."""
    text = PHONE_PATTERN.sub('[REDACTED]', text)
    text = EMAIL_PATTERN.sub('[REDACTED]', text)
    text = WHATSAPP_PATTERN.sub('[REDACTED]', text)
    return text

def guess_district(location_text):
    """Try to match location text to a district."""
    location_lower = location_text.lower()
    for district, province in DISTRICT_PROVINCE_MAP.items():
        if district in location_lower:
            return district.title(), province
    return '', ''

def parse_price(price_text):
    """Parse price string like 'Rs 45,000' to integer."""
    if not price_text:
        return 0
    cleaned = re.sub(r'[^\d]', '', price_text)
    try:
        return int(cleaned)
    except ValueError:
        return 0

def extract_number(text, pattern):
    """Extract a number using regex pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            return 0
    return 0

def scrape_page(url, rate_limit=2000):
    """Fetch and parse a single page."""
    try:
        time.sleep(rate_limit / 1000.0)
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')
    except requests.RequestException as e:
        return None

def scrape_ikman(config):
    """Main scraping function for ikman.lk"""
    max_pages = config.get('maxPages', 3)
    location = config.get('location', '')
    price_min = config.get('priceMin', 0)
    price_max = config.get('priceMax', 0)
    rate_limit = config.get('rateLimit', 2000)

    listings = []
    errors = []
    stats = {
        'pagesScraped': 0,
        'totalFound': 0,
        'errors': 0,
    }

    for page in range(1, max_pages + 1):
        url = SEARCH_URL
        params = []
        if page > 1:
            params.append(f"page={page}")
        if location:
            url = f"https://ikman.lk/en/ads/{location.lower().replace(' ', '-')}/properties?type=rent"
        if price_min:
            params.append(f"price_min={price_min}")
        if price_max:
            params.append(f"price_max={price_max}")
        
        if params:
            separator = '&' if '?' in url else '?'
            url += separator + '&'.join(params)

        soup = scrape_page(url, rate_limit)
        if not soup:
            errors.append({'page': page, 'message': f'Failed to fetch page {page}', 'source': 'ikman'})
            stats['errors'] += 1
            continue

        stats['pagesScraped'] += 1

        # Parse listing cards
        ad_cards = soup.select('li[class*="ad-card"], div[class*="ad-card"], a[class*="card"]')
        
        # Fallback: try common ikman listing selectors
        if not ad_cards:
            ad_cards = soup.select('[data-testid="ad-card"], .list--item, .ad-item')
        
        # Generic fallback for list items with links
        if not ad_cards:
            ad_cards = soup.select('ul li a[href*="/ad/"]')

        for card in ad_cards:
            try:
                # Extract title
                title_el = card.select_one('h2, h3, [class*="title"], [data-testid="title"]')
                title = title_el.get_text(strip=True) if title_el else ''
                if not title:
                    continue

                # Extract link
                link_el = card if card.name == 'a' else card.select_one('a[href]')
                href = link_el.get('href', '') if link_el else ''
                if href and not href.startswith('http'):
                    href = BASE_URL + href

                # Extract price
                price_el = card.select_one('[class*="price"], [data-testid="price"]')
                price_text = price_el.get_text(strip=True) if price_el else ''
                price = parse_price(price_text)

                # Extract location
                loc_el = card.select_one('[class*="location"], [data-testid="location"], [class*="subtitle"]')
                raw_location = loc_el.get_text(strip=True) if loc_el else ''
                
                # Parse location parts
                town = raw_location.split(',')[0].strip() if raw_location else ''
                district, province = guess_district(raw_location)

                # Extract description (may need detail page)
                desc_el = card.select_one('[class*="description"], p')
                description = desc_el.get_text(strip=True) if desc_el else ''

                # Extract image
                img_el = card.select_one('img[src]')
                image_url = img_el.get('src', '') if img_el else ''
                images = [image_url] if image_url and 'placeholder' not in image_url.lower() else []

                # Extract beds/baths from description or tags
                full_text = f"{title} {description}"
                beds = extract_number(full_text, r'(\d+)\s*(?:bed|br|bedroom)', )
                baths = extract_number(full_text, r'(\d+)\s*(?:bath|bathroom)')
                size = extract_number(full_text, r'(\d+)\s*(?:sq\.?\s*ft|sqft|perch)')

                # Detect type
                listing_type = 'Unknown'
                title_lower = title.lower()
                if 'house' in title_lower:
                    listing_type = 'House'
                elif 'apartment' in title_lower or 'flat' in title_lower:
                    listing_type = 'Apartment'
                elif 'annex' in title_lower:
                    listing_type = 'Annex'
                elif 'room' in title_lower or 'boarding' in title_lower:
                    listing_type = 'Boarding Room'

                # PII detection
                combined_text = f"{title} {description}"
                pii = detect_pii(combined_text)
                clean_description = strip_pii(description)
                clean_title = strip_pii(title)

                listing = {
                    'title': clean_title,
                    'description': clean_description,
                    'price': price,
                    'location': {
                        'town': town,
                        'district': district,
                        'province': province,
                        'rawAddress': raw_location,
                    },
                    'beds': beds,
                    'baths': baths,
                    'size': size,
                    'type': listing_type,
                    'furnished': 'Unknown',
                    'images': images,
                    'sourceUrl': href,
                    'sourceId': href.split('/')[-1].split('?')[0] if href else '',
                    'piiDetected': len(pii) > 0,
                    'piiDetails': pii,
                }

                listings.append(listing)
                stats['totalFound'] += 1

            except Exception as e:
                errors.append({'page': page, 'message': str(e), 'source': 'ikman'})
                stats['errors'] += 1

    return {
        'listings': listings,
        'stats': stats,
        'errors': errors,
        'source': 'ikman.lk',
    }

if __name__ == '__main__':
    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
            config = {}
        else:
            config = json.loads(input_data)
        
        result = scrape_ikman(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
