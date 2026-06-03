"""
Nieuwbouw Rotterdam scraper - new build projects in Rotterdam area
Scrapes: https://www.nieuwbouw-rotterdam.nl/projecten/
"""

import re
from typing import Optional, Dict, List
from bs4 import BeautifulSoup
import requests


def extract_project_id(url: str) -> Optional[str]:
    """Extract project ID from URL pattern"""
    match = re.search(r'/project/(\d+)/', url)
    if match:
        return match.group(1)
    return None


def extract_coordinates(soup: BeautifulSoup) -> tuple:
    """Extract latitude/longitude from map element"""
    map_elem = soup.find(attrs={'data-gemy': True, 'data-gemx': True})
    if map_elem:
        try:
            lat = float(map_elem.get('data-gemy'))
            lon = float(map_elem.get('data-gemx'))
            return lat, lon
        except:
            pass
    return None, None


def extract_location_info(soup: BeautifulSoup) -> tuple:
    """Extract stad and woonplaats from project header (e.g., 'Rotterdam - Overschie')"""
    stad = None
    woonplaats = None
    
    header_locale = soup.find(class_='project-header-locatie')
    if header_locale:
        text = header_locale.get_text(strip=True)
        if ' - ' in text:
            parts = text.split(' - ')
            stad = parts[0].strip()
            woonplaats = parts[1].strip() if len(parts) > 1 else None
        else:
            stad = text.strip()
    return stad, woonplaats


def extract_from_project_info(soup: BeautifulSoup, label_text: str) -> Optional[str]:
    """Extract value from project-info dl/dd structure by label text"""
    info_section = soup.find(id='project-voorzieningen')
    if info_section:
        for dt in info_section.find_all('dt'):
            if label_text.lower() in dt.get_text(strip=True).lower():
                dd = dt.find_next_sibling('dd')
                if dd:
                    return dd.get_text(strip=True)
    return None


def extract_aantal_woningen(soup: BeautifulSoup) -> Optional[int]:
    """Extract available woningen from 'X van Y beschikbaar' in project info section"""
    woningen_text = extract_from_project_info(soup, 'Woningen')
    if woningen_text:
        numbers = re.findall(r'(\d+)', woningen_text)
        if numbers:
            try:
                return int(numbers[0])
            except:
                pass
    return None


def extract_beschrijving(soup: BeautifulSoup) -> Optional[str]:
    """Extract status/beschrijving from badge element"""
    status_keywords = ['verkoop gestart', 'in voorbereiding', 'in aanbieding', 'actueel aanbod']
    
    badge = soup.find(class_='badge-primary')
    if badge:
        text = badge.get_text(strip=True).lower()
        for keyword in status_keywords:
            if keyword in text:
                return keyword.title()
    
    return None


def extract_prijs(soup: BeautifulSoup) -> tuple:
    """Extract prijs_min and prijs_max from project header"""
    prijs_min = None
    prijs_max = None
    
    prijs_elem = soup.find(class_='project-header-prijs')
    if prijs_elem:
        text = prijs_elem.get_text(strip=True)
        
        if 'n.n.b.' in text.lower() or 'nog niet bekend' in text.lower():
            return None, None
        
        prices = re.findall(r'€\s*([\d.]+)', text)
        if len(prices) >= 2:
            try:
                prijs_min = float(prices[0].replace('.', ''))
                prijs_max = float(prices[1].replace('.', ''))
                return prijs_min, prijs_max
            except:
                pass
        elif len(prices) == 1:
            try:
                prijs_min = float(prices[0].replace('.', ''))
                return prijs_min, prijs_min
            except:
                pass
    
    return prijs_min, prijs_max


def extract_images(soup: BeautifulSoup) -> List[str]:
    """Extract image URLs from project photos section"""
    images = []
    fotos_section = soup.find(id='project-fotos')
    if fotos_section:
        for img in fotos_section.find_all('img', class_='img-fluid'):
            src = img.get('src')
            if src and src.startswith('http'):
                images.append(src)
    return images


def extract_woonoppervlakte(soup: BeautifulSoup) -> Optional[str]:
    """Extract woonoppervlakte from features section using label"""
    features_section = soup.find(id='project-kenmerken')
    if features_section:
        for feature in features_section.find_all(class_='col-feature'):
            label = feature.find(class_='feature-label')
            if label and 'woonoppervlak' in label.get_text(strip=True).lower():
                value = feature.find(class_='feature-value')
                if value:
                    text = value.get_text(strip=True)
                    text = re.sub(r'm\s*<sup>\s*2\s*</sup>\s*$', ' m²', text, flags=re.IGNORECASE)
                    text = re.sub(r'm2$', ' m²', text, flags=re.IGNORECASE)
                    if 'm²' not in text:
                        text = text + ' m²'
                    return text.strip()
    return None


def extract_aantal_slaapkamers(soup: BeautifulSoup) -> Optional[str]:
    """Extract aantal slaapkamers from features section using label"""
    features_section = soup.find(id='project-kenmerken')
    if features_section:
        for feature in features_section.find_all(class_='col-feature'):
            label = feature.find(class_='feature-label')
            if label and 'slaapkamer' in label.get_text(strip=True).lower():
                value = feature.find(class_='feature-value')
                if value:
                    return value.get_text(strip=True)
    return None


def extract_bathroom_descr(soup: BeautifulSoup) -> Optional[str]:
    """Extract bathroom description from bullet points in project description"""
    beschrijving_section = soup.find(id='project-beschrijving')
    if beschrijving_section:
        text_collapse = beschrijving_section.find(class_='text-collapse')
        if text_collapse:
            text = text_collapse.get_text()
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('-') and 'badkamer' in line.lower():
                    return line.lstrip('- ').strip()
    return None


def extract_balcony_info(soup: BeautifulSoup) -> tuple:
    """Extract balcony presence and size description from bullet points"""
    balkon_present = False
    balkon_grootte = None
    
    beschrijving_section = soup.find(id='project-beschrijving')
    if beschrijving_section:
        text_collapse = beschrijving_section.find(class_='text-collapse')
        if text_collapse:
            text = text_collapse.get_text()
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('-') and 'balkon' in line.lower():
                    balkon_present = True
                    balkon_grootte = line.lstrip('- ').strip()
                    break
    
    return balkon_present, balkon_grootte


def extract_apartment_descr(soup: BeautifulSoup) -> Optional[str]:
    """Extract main apartment description, excluding initial bullet points"""
    beschrijving_section = soup.find(id='project-beschrijving')
    if beschrijving_section:
        text_collapse = beschrijving_section.find(class_='text-collapse')
        if text_collapse:
            text = text_collapse.get_text()
            lines = text.split('\n')
            description_lines = [line.strip() for line in lines 
                               if line.strip() and not line.strip().startswith('-')]
            if description_lines:
                return ' '.join(description_lines).strip()
    return None


def extract_woningtypes(soup: BeautifulSoup) -> List[str]:
    """Extract woningtypes from 'Type woningen' field in project info section"""
    woningtypes = []
    types_text = extract_from_project_info(soup, 'Type woningen')
    if types_text:
        known_types = ['Appartement', 'Tussenwoning', 'Vrijstaande woning', 'Herenhuis', '2-onder-1-kap', 'Bungalow']
        for wtype in known_types:
            if wtype.lower() in types_text.lower():
                woningtypes.append(wtype)
    return woningtypes


def extract_start_verkoop(soup: BeautifulSoup) -> Optional[str]:
    """Extract start verkoop date from project info section"""
    return extract_from_project_info(soup, 'Start verkoop')


def scrape_url(url: str, session: requests.Session) -> Optional[Dict]:
    """Scrape a Nieuwbouw Rotterdam project page"""
    
    if '/projecten/kaart/' in url:
        return None
    
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        h1 = soup.find('h1')
        naam = h1.get_text(strip=True) if h1 else ""
        
        project_id = extract_project_id(url)
        latitude, longitude = extract_coordinates(soup)
        stad, woonplaats = extract_location_info(soup)
        aantal_woningen = extract_aantal_woningen(soup)
        beschrijving = extract_beschrijving(soup)
        prijs_min, prijs_max = extract_prijs(soup)
        start_verkoop = extract_start_verkoop(soup)
        
        images = extract_images(soup)
        woonoppervlakte = extract_woonoppervlakte(soup)
        aantal_slaapkamers = extract_aantal_slaapkamers(soup)
        bathroom_descr = extract_bathroom_descr(soup)
        balkon_present, balkon_grootte = extract_balcony_info(soup)
        apartement_descr = extract_apartment_descr(soup)
        woningtypes = extract_woningtypes(soup)
        
        return {
            "project_id": project_id or url,
            "source": "nieuwbouw_rotterdam",
            "url": url,
            "naam": naam,
            "straatnaam": None,
            "stad": stad or "Rotterdam",
            "woonplaats": woonplaats,
            "latitude": latitude,
            "longitude": longitude,
            "aantal_woningen": aantal_woningen,
            "prijs_min": prijs_min,
            "prijs_max": prijs_max,
            "woonoppervlakte": woonoppervlakte,
            "aantal_slaapkamers": aantal_slaapkamers,
            "bathroom_descr": bathroom_descr,
            "balkon_present": balkon_present,
            "balkon_grootte": balkon_grootte,
            "apartement_descr": apartement_descr,
            "images": images,
            "woningtypes": woningtypes,
            "beschrijving": beschrijving,
            "start_verkoop": start_verkoop,
            "bron": "nieuwbouw-rotterdam.nl"
        }
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None