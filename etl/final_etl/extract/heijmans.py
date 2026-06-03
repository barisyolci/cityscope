import re
import json
from typing import Optional, Dict, List
from bs4 import BeautifulSoup
import requests

def extract_text(el, default: str = "") -> str:
    """Safely extract and clean text from element"""
    if not el:
        return default
    return re.sub(r'\s+', ' ', el.get_text(separator=' ', strip=True)).strip()

def parse_number(text: str) -> Optional[int]:
    """Extract first integer from text"""
    if not text:
        return None
    match = re.search(r'\d+', text)
    return int(match.group(0)) if match else None

def parse_price(text: str) -> Optional[float]:
    """Parse price from text (e.g., '414K' -> 414000, '1,02 mln' -> 1020000)"""
    if not text:
        return None
    
    text = text.strip().replace(',', '.')
    
    if 'mln' in text.lower():
        match = re.search(r'([\d.]+)\s*mln', text, re.I)
        if match:
            return float(match.group(1)) * 1_000_000
    
    if 'K' in text:
        match = re.search(r'([\d.]+)\s*K', text)
        if match:
            return float(match.group(1)) * 1_000
    
    match = re.search(r'[\d.]+', text)
    if match:
        return float(match.group(0))
    
    return None

def extract_city_from_title(title: str) -> Optional[str]:
    """Dynamically extract city from og:title format: 'Project - City - Description'"""
    if not title:
        return None
    
    parts = title.split(' - ')
    if len(parts) >= 2:
        return parts[1].strip()
    
    return None

def scrape_url(url: str, session: requests.Session, target_city: Optional[str] = None) -> Optional[Dict]:
    """Scrape a Heijmans project page using requests, BeautifulSoup, and Next.js RSC payload"""
    if '/projecten/' not in url:
        return None
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        html = response.text
        
        if len(html) < 1000:
            print(f"Response too small ({len(html)} chars) for {url}. Skipping.")
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text(separator=' ', strip=True)
        
        # 1. Extract City (og:title -> RSC payload fallback)
        woonplaats = None
        og_title = soup.find('meta', {'property': 'og:title'})
        if og_title and og_title.get('content'):
            woonplaats = extract_city_from_title(og_title.get('content'))
        
        if not woonplaats:
            # Fallback to Next.js RSC payload which contains exact location data
            loc_match = re.search(r'"location"\s*:\s*"([^"]+)"', html)
            if loc_match:
                woonplaats = loc_match.group(1).strip()
                
        # Filter by target city if specified (Set to None to scrape all)
        if target_city and (not woonplaats or woonplaats.lower() != target_city.lower()):
            return None
            
        url_slug = url.rstrip('/').split('/')[-1]
        straatnaam = ' '.join(word.capitalize() for word in url_slug.split('-'))
        
        # 2. Extract Wijk
        wijk = None
        wijk_match = re.search(r'wijk\s+([A-Za-zà-ÿ\s]+?)(?:,|\.|$|\n)', page_text, re.I)
        if wijk_match:
            wijk = wijk_match.group(1).strip()[:50]
            
        # 3. Extract Data from Next.js RSC Payload (Much more robust than page_text regex)
        aantal_woningen = None
        plots_match = re.search(r'"plots_total"\s*:\s*(\d+)', html)
        if plots_match:
            aantal_woningen = int(plots_match.group(1))
            
        woonoppervlakte = None
        min_surf = re.search(r'"living_surface_min"\s*:\s*(\d+)', html)
        max_surf = re.search(r'"living_surface_max"\s*:\s*(\d+)', html)
        if min_surf and max_surf:
            woonoppervlakte = f"{min_surf.group(1)} - {max_surf.group(1)}"
        elif min_surf:
            woonoppervlakte = min_surf.group(1)
        elif max_surf:
            woonoppervlakte = max_surf.group(1)
            
        prijs_min = None
        prijs_max = None
        min_price = re.search(r'"price_min"\s*:\s*(\d+)', html)
        max_price = re.search(r'"price_max"\s*:\s*(\d+)', html)
        if min_price:
            prijs_min = float(min_price.group(1))
        if max_price:
            prijs_max = float(max_price.group(1))
            
        start_verkoop = None
        start_bouw = None
        
        if '"phase_status":"In verkoop"' in html or 'In verkoop' in page_text:
            start_verkoop = "In verkoop"
        
        if '"phase_status":"Toekomstig"' in html or 'In ontwikkeling' in page_text:
            start_bouw = "In ontwikkeling"
            
        woningtypes = []
        housing_types = [
            'Appartement', 
            'Vrijstaande woning', 
            'Twee-onder-een-kapwoning', 
            'Tussenwoning',
            'Herenhuis',
            'Kavel',
            'Penthouse'
        ]
        for htype in housing_types:
            if htype in page_text:
                woningtypes.append(htype)
        
        provided_by = 'Heijmans' if 'Heijmans' in page_text else None
        
        huur_of_koop = None
        if 'huurappartementen' in page_text.lower() or 'huurwoningen' in page_text.lower():
            if 'koopappartementen' in page_text.lower() or 'koopwoningen' in page_text.lower():
                huur_of_koop = 'huur_en_koop'
            else:
                huur_of_koop = 'huur'
        elif 'koopappartementen' in page_text.lower() or 'koopwoningen' in page_text.lower():
            huur_of_koop = 'koop'
            
        return {
            "url": url,
            "straatnaam": straatnaam,
            "aantal_woningen": aantal_woningen,
            "woonplaats": woonplaats,
            "wijk": wijk,
            "prijs_min": prijs_min,
            "prijs_max": prijs_max,
            "woonoppervlakte": woonoppervlakte,
            "start_verkoop": start_verkoop,
            "start_bouw": start_bouw,
            "woningtypes": woningtypes,
            "provided_by": provided_by,
            "huur_of_koop": huur_of_koop,
            "bouwnummers": []
        }
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def extract_urls_from_html_file(file_path: str) -> List[str]:
    """Extract all unique project URLs from the saved HTML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    urls = set()
    base_url = "https://heijmansnieuwbouw.nl"
    
    # Find all links that point to /projecten/
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/projecten/') and href != '/projecten/':
            full_url = base_url + href
            urls.add(full_url)
            
    # Also extract from Next.js JSON payload (RSC payload) if rendered links are missing
    rsc_urls = re.findall(r'href=\\?"(/projecten/[^"\\]+)\\?"', html)
    for href in rsc_urls:
        if href != '/projecten/':
            urls.add(base_url + href)
            
    return list(urls)

def main():
    file_path = 'Pasted_Text_1780441004379.txt'
    project_urls = extract_urls_from_html_file(file_path)
    print(f"Found {len(project_urls)} project URLs in the HTML file.")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"
    })
    
    all_projects = []
    
    for url in project_urls:
        print(f"Scraping {url}...")
        # CHANGE: Set target_city=None to scrape ALL cities instead of just Rotterdam
        project_data = scrape_url(url, session, target_city=None)
        if project_data:
            all_projects.append(project_data)
            print(f" -> Added: {project_data['straatnaam']} ({project_data['woonplaats']})")
        else:
            print(f" -> Skipped (Error or missing data)")
            
    print(f"\nTotal projects found: {len(all_projects)}")
    for p in all_projects:
        print(f"- {p['straatnaam']} ({p['woonplaats']})")

if __name__ == "__main__":
    main()