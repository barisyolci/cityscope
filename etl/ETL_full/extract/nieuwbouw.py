import re
from typing import Optional, Dict, List
from bs4 import BeautifulSoup, Tag
import requests
import json


def extract_text(el: Optional[Tag], default: str = "") -> str:
    """Extract clean text from a BeautifulSoup element"""
    if not el:
        return default
    return re.sub(r'\s+', ' ', el.get_text(strip=True)).strip()


def find_section_by_heading(soup: BeautifulSoup, heading_text: str) -> Optional[Tag]:
    """Find a section container by its h2 heading"""
    h2 = soup.find("h2", string=lambda text: text and heading_text.lower() in text.lower())
    if h2:
        next_el = h2.find_next_sibling()
        if next_el:
            return next_el
        return h2.parent
    return None


def extract_key_value_pairs(container: Tag, keys_to_find: List[str]) -> Dict[str, str]:
    """Extract key-value pairs from structured list items with label/value layout"""
    results = {}
    if not container:
        return results
    
    for li in container.find_all('li'):
        # Find label (text-light-500 class)
        label_el = li.find('div', class_=lambda c: c and 'text-light-500' in c)
        if not label_el:
            continue
        
        # Find value element (text-dark class or next div)
        value_el = label_el.find_next('div', class_=lambda c: c and 'text-dark' in c)
        if not value_el:
            value_el = label_el.find_next_sibling('div')
        if not value_el:
            # Fallback: any other div in same li
            divs = [child for child in li.find_all('div', recursive=False) if child is not label_el]
            value_el = divs[0] if divs else None
        
        label = extract_text(label_el)
        value = extract_text(value_el) if value_el else ''
        
        for key in keys_to_find:
            if label.lower().startswith(key.lower()):
                if value:
                    results[key] = value
                break
    
    return results


def parse_price(txt: str) -> str:
    """Return 'n.n.b.' for unknown prices, otherwise return cleaned price text"""
    if not txt:
        return "n.n.b."
    txt_lower = txt.lower().strip()
    if "prijs nog niet bekend" in txt_lower or "n.n.b." in txt_lower or "verkocht" in txt_lower:
        return "n.n.b."
    return txt.strip()


def scrape_url(url: str, session: requests.Session) -> Optional[Dict]:
    """
    Scrape project data from nieuwbouw.nl URL.
    Returns dict with statically available data only.
    """
    response = session.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find main project characteristics section
    project_section = find_section_by_heading(soup, "Project kenmerken") or soup
    
    # Extract project data
    project_data = extract_key_value_pairs(project_section, [
        "Project", "Aantal woningen", "Woningsoort(en)", "Woningsoort"
    ])
    
    # Extract location data  
    locatie_section = find_section_by_heading(soup, "Locatie") or soup
    locatie_data = extract_key_value_pairs(locatie_section, ["Woonplaats", "Wijk"])
    
    # Extract provider info from "Overig" section
    overig_section = find_section_by_heading(soup, "Overig") or soup
    overig_data = extract_key_value_pairs(overig_section, ["Project van"])
    provided_by = overig_data.get("Project van")
    
    # Determine huur/koop from URL path
    huur_of_koop = None
    if "/huur/" in url.lower():
        huur_of_koop = "huur"
    elif "/koop/" in url.lower():
        huur_of_koop = "koop"

    # Get project name from h1
    h1 = soup.find("h1")
    naam = extract_text(h1) if h1 else project_data.get("Project", "")
    
    # Fallback to JSON-LD if h1 missing
    if not naam:
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld and json_ld.string:
            try:
                json_data = json.loads(json_ld.string)
                if isinstance(json_data, dict):
                    naam = json_data.get('name', '')
                elif isinstance(json_data, list):
                    for item in json_data:
                        if isinstance(item, dict) and item.get('@type') == 'ItemPage':
                            naam = item.get('name', '')
                            break
            except Exception:
                pass

    # Parse woningtypes from comma/semicolon separated list
    woningtypes = []
    raw_woningtypes = project_data.get("Woningsoort(en)") or project_data.get("Woningsoort")
    if raw_woningtypes:
        woningtypes = [t.strip() for t in re.split(r'[;,]', raw_woningtypes) if t.strip()]

    # Extract description from "Omschrijving" section
    omschrijving = None
    omschrijving_heading = soup.find("h2", string=lambda text: text and "Omschrijving" in text)
    if omschrijving_heading:
        omschrijving_section = omschrijving_heading.find_next_sibling() or omschrijving_heading.find_next("div")
        if omschrijving_section:
            omschrijving = omschrijving_section.get_text(separator=' ', strip=True)
    
    # Fallback to JSON-LD description
    if not omschrijving:
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld and json_ld.string:
            try:
                json_data = json.loads(json_ld.string)
                if isinstance(json_data, dict) and json_data.get('description'):
                    omschrijving = json_data.get('description')
                elif isinstance(json_data, list):
                    for item in json_data:
                        if isinstance(item, dict) and item.get('@type') == 'ItemPage' and item.get('description'):
                            omschrijving = item.get('description')
                            break
            except Exception:
                pass

    # Handle price - check for "Prijs nog niet bekend" text
    prijs = "n.n.b."  # Default assumption
    price_span = soup.find('span', string=lambda t: t and "Prijs nog niet bekend" in t)
    if not price_span:
        # Try to find actual price with € symbol
        price_text = soup.find(string=lambda t: t and "€" in str(t))
        if price_text and price_text.parent:
            prijs = parse_price(extract_text(price_text.parent))

    # Map columns according to requirements:
    # - straatnaam ← Wijk from site
    # - woonplaats ← Woonplaats from site  
    # - stad ← hardcoded "Rotterdam"
    wijk = locatie_data.get("Wijk", "")
    woonplaats = locatie_data.get("Woonplaats", "")
    aantal_woningen = project_data.get("Aantal woningen")

    return {
        "url": url,  # Full URL as requested (no project_id)
        "naam": naam,
        "straatnaam": wijk,  # Mapped from Wijk
        "woonplaats": woonplaats,  # Mapped from Woonplaats
        "stad": "Rotterdam",  # Hardcoded per requirement
        "aantal_woningen": aantal_woningen,
        "prijs": prijs,  # "n.n.b." if unknown
        "woningtypes": woningtypes,
        "provided_by": provided_by,
        "huur_of_koop": huur_of_koop,
        "omschrijving": omschrijving,
    }