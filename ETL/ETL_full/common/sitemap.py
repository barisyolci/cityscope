from typing import List
from xml.etree import ElementTree
import requests
from bs4 import BeautifulSoup


def fetch_urls_from_sitemap(sitemap_url: str, session: requests.Session, exclude_patterns: List[str] = None) -> List[str]:
    response = session.get(sitemap_url, timeout=30)
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in root.findall(".//ns:loc", namespace)]
    if exclude_patterns:
        urls = [u for u in urls if not any(p in u for p in exclude_patterns)]
    return urls


def fetch_urls_from_listing(listing_url: str, session: requests.Session, url_pattern: str = None) -> List[str]:
    """Extract all links from a listing page"""
    response = session.get(listing_url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    urls = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        # Make absolute URL
        if href.startswith('http'):
            url = href
        elif href.startswith('/'):
            from urllib.parse import urljoin
            url = urljoin(listing_url, href)
        else:
            continue
        
        # Filter by pattern if provided
        if url_pattern and url_pattern not in url:
            continue
        
        # Avoid duplicates
        if url not in urls:
            urls.append(url)
    
    return urls

