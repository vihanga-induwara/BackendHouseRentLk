"""
Scraper Runner — Orchestrator that runs selected scrapers and deduplicates results.
Input (stdin JSON): {
    "sources": [{"slug": "ikman", "script": "ikman_scraper.py", "config": {...}}, ...],
    "type": "full|incremental|recheck"
}
Output (stdout JSON): {
    "results": { "ikman": {...}, "lpw": {...} },
    "combined": { "listings": [...], "totalScraped": N },
    "errors": [...]
}
"""
import sys
import json
import importlib.util
import os

SCRAPERS_DIR = os.path.dirname(os.path.abspath(__file__))

# Map slug to scraper module and function
SCRAPER_MAP = {
    'ikman': ('ikman_scraper', 'scrape_ikman'),
    'lpw': ('lpw_scraper', 'scrape_lpw'),
    'hitad': ('hitad_scraper', 'scrape_hitad'),
    'house': ('house_scraper', 'scrape_house'),
    'ceylon': ('ceylon_scraper', 'scrape_ceylon'),
}

def load_scraper(module_name):
    """Dynamically load a scraper module."""
    module_path = os.path.join(SCRAPERS_DIR, f"{module_name}.py")
    if not os.path.exists(module_path):
        return None
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def deduplicate_listings(listings):
    """Remove duplicate listings by sourceUrl."""
    seen = set()
    unique = []
    for listing in listings:
        url = listing.get('sourceUrl', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(listing)
        elif not url:
            unique.append(listing)
    return unique, len(listings) - len(unique)

def run_scrapers(config):
    sources = config.get('sources', [])
    scrape_type = config.get('type', 'full')
    
    results = {}
    all_listings = []
    all_errors = []
    
    for source in sources:
        slug = source.get('slug', '')
        scraper_config = source.get('config', {})
        
        if slug not in SCRAPER_MAP:
            all_errors.append({
                'source': slug,
                'message': f'Unknown scraper slug: {slug}'
            })
            continue
        
        module_name, func_name = SCRAPER_MAP[slug]
        
        try:
            module = load_scraper(module_name)
            if not module:
                all_errors.append({
                    'source': slug,
                    'message': f'Scraper module not found: {module_name}.py'
                })
                continue
            
            scrape_func = getattr(module, func_name, None)
            if not scrape_func:
                all_errors.append({
                    'source': slug,
                    'message': f'Scraper function not found: {func_name}'
                })
                continue
            
            result = scrape_func(scraper_config)
            results[slug] = {
                'stats': result.get('stats', {}),
                'listingCount': len(result.get('listings', [])),
                'source': result.get('source', slug),
            }
            
            # Tag each listing with its source slug
            for listing in result.get('listings', []):
                listing['_sourceSlug'] = slug
            
            all_listings.extend(result.get('listings', []))
            all_errors.extend(result.get('errors', []))
            
        except Exception as e:
            all_errors.append({
                'source': slug,
                'message': f'Scraper execution failed: {str(e)}'
            })
            results[slug] = {'stats': {}, 'listingCount': 0, 'error': str(e)}
    
    # Deduplicate across all sources
    unique_listings, dupes_removed = deduplicate_listings(all_listings)
    
    return {
        'results': results,
        'combined': {
            'listings': unique_listings,
            'totalScraped': len(unique_listings),
            'duplicatesRemoved': dupes_removed,
        },
        'errors': all_errors,
    }

if __name__ == '__main__':
    try:
        input_data = sys.stdin.read().strip()
        config = json.loads(input_data) if input_data else {}
        result = run_scrapers(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
