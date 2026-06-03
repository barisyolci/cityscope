"""
Huurwoningen.com Generic Scraper
Extracts property details and maps them to the target ETL schema.
Note: Crawl delay / rate limiting is assumed to be handled by the orchestrator/ETL pipeline.
"""

import re
import json
from typing import Optional, Dict, List, Any
from bs4 import BeautifulSoup
import requests


def extract_json_ld(soup: BeautifulSoup) -> Optional[Dict]:
    """Extract JSON-LD structured data"""
    script = soup.find('script', {'type': 'application/ld+json'})
    if not script or not script.string:
        return None
    try:
        return json.loads(script.string)
    except (json.JSONDecodeError, AttributeError):
        return None


def parse_price(price_input) -> Optional[float]:
    """
    Robust price parser that handles both JSON-LD standard floats ("2541.00") 
    and European HTML text formats ("€ 2.541 per maand", "1.250.000", "12").
    """
    if not price_input:
        return None
    
    price_str = str(price_input).strip()
    
    # Remove currency symbols, text, and keep only digits, dots, and commas
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    if not cleaned:
        return None
        
    dots = cleaned.count('.')
    commas = cleaned.count(',')
    
    try:
        if dots == 0 and commas == 0:
            return float(cleaned)
            
        elif dots > 0 and commas == 0:
            if dots > 1:
                return float(cleaned.replace('.', ''))
            
            parts = cleaned.split('.')
            if len(parts[1]) == 3 and len(parts[0]) <= 3:
                return float(cleaned.replace('.', ''))
            else:
                return float(cleaned)
                
        elif commas > 0 and dots == 0:
            if commas > 1:
                return float(cleaned.replace(',', ''))
            
            parts = cleaned.split(',')
            if len(parts[1]) == 3 and len(parts[0]) <= 3:
                return float(cleaned.replace(',', ''))
            else:
                return float(cleaned.replace(',', '.'))
                
        elif dots > 0 and commas > 0:
            if cleaned.rfind('.') > cleaned.rfind(','):
                return float(cleaned.replace(',', ''))
            else:
                return float(cleaned.replace('.', '').replace(',', '.'))
                
    except ValueError:
        return None
        
    return None


def extract_images(soup: BeautifulSoup, json_ld: Dict) -> List[str]:
    """Extract high-quality property images"""
    images = []
    
    # 1. Try JSON-LD images first
    if json_ld:
        json_images = json_ld.get('image') or json_ld.get('images')
        if isinstance(json_images, str):
            images.append(json_images.split('?')[0])
        elif isinstance(json_images, list):
            for img in json_images:
                if isinstance(img, str):
                    images.append(img.split('?')[0])
                elif isinstance(img, dict) and 'url' in img:
                    images.append(img['url'].split('?')[0])

    # 2. Fallback to HTML carousel/picture elements for higher resolution
    for picture in soup.find_all('picture'):
        img = picture.find('img')
        if img:
            src = img.get('src') or img.get('data-src')
            if src and 'casco-media-prod' in src and src not in images:
                images.append(src.split('?')[0])
                
        for source in picture.find_all('source'):
            srcset = source.get('srcset', '')
            if srcset and 'casco-media-prod' in srcset:
                urls = [s.strip().split()[0] for s in srcset.split(',') if s.strip()]
                if urls:
                    clean_url = urls[-1].split('?')[0]
                    if clean_url not in images:
                        images.append(clean_url)
    
    # Deduplicate and remove SVG placeholders
    seen = set()
    unique_images = []
    for img in images:
        if img not in seen and 'data:image' not in img:
            seen.add(img)
            unique_images.append(img)
            
    return unique_images[:15]


def extract_description(soup: BeautifulSoup, json_ld: Dict) -> str:
    """Extract the main property description (omschrijving)"""
    # 1. Try JSON-LD first, as HTML might be truncated for non-premium users
    if json_ld and json_ld.get('description'):
        desc = json_ld['description']
        # Clean up JSON-LD description
        desc = re.sub(r'\\n', '\n', desc)
        desc = re.sub(r'\n+', '\n', desc).strip()
        desc = desc.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        if len(desc) > 50:
            return desc

    # 2. Fallback to HTML
    desc_container = soup.find('wc-listing-detail-description')
    if desc_container:
        content = desc_container.find(class_=re.compile(r'listing-detail-description__(truncated|content)'))
        if content:
            # Remove CTA links and titles
            for elem in content.find_all(['h2', 'a']):
                elem.decompose()
            desc_text = content.get_text(separator='\n', strip=True)
            # Only use HTML if it's not truncated
            if desc_text and len(desc_text) > 20 and not desc_text.endswith('...'):
                return desc_text
        
    return ""


def extract_html_features(soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
    """Extract all key-value pairs from the detail sections dynamically"""
    sections = {}
    
    # Map section headers to internal keys
    section_map = {
        'Overdracht': 'transfer',
        'Oppervlakte en inhoud': 'surface',
        'Bouw': 'construction',
        'Indeling': 'layout',
        'Buitenruimte': 'outdoor',
        'Energie': 'energy',
        'Parkeergelegenheid': 'parking'
    }
    
    for section in soup.find_all('section', class_=re.compile(r'page__details--')):
        heading = section.find('h2', class_=re.compile(r'page__heading--sub'))
        if not heading:
            continue
            
        section_title = heading.get_text(strip=True)
        internal_key = section_map.get(section_title, section_title.lower().replace(' ', '_'))
        
        pairs = {}
        for dl in section.find_all('dl', class_='listing-features__list'):
            for dt in dl.find_all('dt', class_='listing-features__term'):
                key = dt.get_text(strip=True)
                dd = dt.find_next_sibling('dd', class_='listing-features__description')
                if dd:
                    # Handle lists (like Voorzieningen)
                    ul = dd.find('ul', class_='listing-features__main-description')
                    if ul:
                        value = ', '.join([li.get_text(strip=True) for li in ul.find_all('li')])
                    else:
                        main_desc = dd.find('span', class_='listing-features__main-description')
                        value = main_desc.get_text(strip=True) if main_desc else dd.get_text(strip=True)
                    
                    if key and value:
                        pairs[key] = value
        sections[internal_key] = pairs
        
    return sections


def map_to_schema(url: str, json_ld: Dict, features: Dict, description: str, images: List[str]) -> Dict[str, Any]:
    """Map extracted data to the final target schema"""
    
    # Base JSON-LD data
    address = json_ld.get('address', {})
    geo = json_ld.get('geo', {})
    offers = json_ld.get('offers', {})
    
    # Extract basic fields
    project_id = json_ld.get('@id', url).split('/')[-2] if json_ld.get('@id') else url.split('/')[-2]
    naam = json_ld.get('name', '')
    straatnaam = address.get('streetAddress')
    stad = address.get('addressLocality')
    woonplaats = address.get('addressRegion') or stad
    latitude = geo.get('latitude')
    longitude = geo.get('longitude')
    
    # Features mapping
    transfer = features.get('transfer', {})
    surface = features.get('surface', {})
    construction = features.get('construction', {})
    layout = features.get('layout', {})
    outdoor = features.get('outdoor', {})
    energy = features.get('energy', {})
    parking = features.get('parking', {})
    
    # Pricing (Smart parsing handles both JSON-LD "2541.00" and HTML "€ 2.541 per maand")
    prijs = parse_price(offers.get('price'))
    if not prijs:
        prijs = parse_price(transfer.get('Huurprijs'))
        
    prijs_per_m2 = parse_price(transfer.get('Prijs per m²'))
    
    # Parse integers safely
    def safe_int(val):
        if not val: return None
        match = re.search(r'\d+', str(val))
        return int(match.group()) if match else None

    woonoppervlakte = safe_int(surface.get('Woonoppervlakte'))
    aantal_slaapkamers = safe_int(layout.get('Aantal slaapkamers'))
    aantal_badkamers = safe_int(layout.get('Aantal badkamers'))
    
    # Woningtypes array
    woningtypes = []
    type_woning = construction.get('Type woning')
    soort_woning = construction.get('Soort woning')
    if type_woning: woningtypes.append(type_woning)
    if soort_woning and soort_woning != type_woning: woningtypes.append(soort_woning)
    
    # Balkon / Outdoor logic
    balkon_text = outdoor.get('Balkon', '').lower()
    balkon_present = balkon_text not in ['niet aanwezig', 'nee', '']
    
    # Bathroom description (from facilities)
    facilities = layout.get('Voorzieningen', '')
    bathroom_descr = None
    if facilities:
        bath_items = [f for f in facilities.split(',') if any(x in f.lower() for x in ['douche', 'bad', 'toilet', 'wc'])]
        if bath_items:
            bathroom_descr = ', '.join(bath_items)

    # Final Schema Construction
    return {
        # --- Target Schema Matches ---
        "project_id": project_id,
        "source": "huurwoningen_rotterdam",
        "url": url,
        "naam": naam,
        "straatnaam": straatnaam,
        "stad": stad,
        "woonplaats": woonplaats,
        "latitude": float(latitude) if latitude else None,
        "longitude": float(longitude) if longitude else None,
        "aantal_woningen": 1,
        "prijs_min": prijs,
        "prijs_max": prijs,
        "woonoppervlakte": woonoppervlakte,
        "aantal_slaapkamers": aantal_slaapkamers,
        "bathroom_descr": bathroom_descr,
        "balkon_present": balkon_present,
        "balkon_grootte": None,
        "omschrijving": description,  # Renamed from appartement_descr
        "images": images,
        "woningtypes": woningtypes,
        "beschrijving": transfer.get('Status', ''),  # e.g., "Te huur"
        "start_verkoop": transfer.get('Beschikbaar', ''), # e.g., "Per 01-07-2026"
        "bron": "huurwoningen.com",
        
        # --- Extra Requested Datapoints ---
        "prijs_per_m2": prijs_per_m2,
        "aangeboden_sinds": transfer.get('Aangeboden sinds'),
        "soort_bouw": construction.get('Soort bouw'),
        "bouwjaar": safe_int(construction.get('Bouwjaar')),
        "aantal_kamers": safe_int(layout.get('Aantal kamers')),
        "aantal_badkamers": aantal_badkamers,
        "aantal_woonlagen": safe_int(layout.get('Aantal woonlagen')),
        "voorzieningen": facilities,
        "tuin_present": outdoor.get('Tuin', '').lower() not in ['niet aanwezig', 'nee', ''],
        "dakterras_present": outdoor.get('Dakterras', '').lower() not in ['niet aanwezig', 'nee', ''],
        "energielabel": energy.get('Energielabel'),
        "parkeergelegenheid": parking.get('Aanwezig')
    }


def scrape_url(url: str, session: requests.Session) -> Optional[Dict]:
    """Main scraper function for a single Huurwoningen URL"""
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        json_ld = extract_json_ld(soup)
        if not json_ld:
            print(f"Warning: No JSON-LD found for {url}")
            return None
            
        description = extract_description(soup, json_ld)
        images = extract_images(soup, json_ld)
        features = extract_html_features(soup)
        
        return map_to_schema(url, json_ld, features, description, images)
        
    except requests.RequestException as e:
        print(f"HTTP error scraping {url}: {e}")
        return None
    except Exception as e:
        print(f"Error scraping {url}: {type(e).__name__}: {e}")
        return None