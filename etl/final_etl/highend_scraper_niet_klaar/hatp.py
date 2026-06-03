from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin

DEFAULT_URL = "https://account.houseatthepark.nl/aanbod/#/"

def scrape_houseatthepark(url: str = DEFAULT_URL, timeout: int = 15):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Student Project")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    properties = []

    try:
        driver.get(url)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "list-group-item"))
        )
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        for item in soup.select("li.list-group-item"):
            prop = {}
            
            bouwnummer_div = item.select_one("h6.card-title")
            if bouwnummer_div:
                bouwnummer_text = bouwnummer_div.get_text(strip=True)
                prop["bouwnummer"] = bouwnummer_text.replace("Bouwnummer", "").strip()
            
            status_div = item.select_one("div.small")
            if status_div:
                prop["status"] = status_div.get_text(strip=True)
            
            details_p = item.select_one("p.card-text.dotted-spans")
            if details_p:
                spans = details_p.find_all("span", recursive=False)
                for span in spans:
                    text = span.get_text(strip=True)
                    if "kamerappartement" in text or "herenhuis" in text or "penthouse" in text:
                        prop["woningtype"] = text
                    elif "begane grond" in text.lower() or "verdieping" in text.lower() or "zolder" in text.lower():
                        prop["verdieping"] = text
                    elif "m²" in text and "balkon" not in text:
                        prop["woonoppervlakte"] = text.replace("m²", "").strip()
                    elif "balkon" in text:
                        balkon_match = re.search(r"([\d.]+)\s*m²", text)
                        if balkon_match:
                            prop["balkon_grootte"] = float(balkon_match.group(1))
                    elif "slaapkamer" in text:
                        slaapkamer_match = re.search(r"(\d+)\s*slaapkamer", text)
                        if slaapkamer_match:
                            prop["slaapkamers"] = int(slaapkamer_match.group(1))
            
            prijs_div = item.select_one("div[class*='fw-bold']")
            if not prijs_div:
                prijs_div = item.find("div", string=re.compile(r"€[\d.]+"))
            if prijs_div:
                prijs_text = prijs_div.get_text(strip=True)
                prijs_match = re.search(r"€([\d.]+)", prijs_text.replace(".", "").replace(",", "."))
                if prijs_match:
                    prop["prijs"] = float(prijs_match.group(1).replace(".", ""))
            
            link_tag = item.select_one("a[href*='/aanbod/']")
            if link_tag and link_tag.get("href"):
                prop["url"] = urljoin("https://account.houseatthepark.nl", link_tag["href"])
            
            if prop:
                properties.append(prop)
        
        for i, prop in enumerate(properties):
            if "url" not in prop or not prop["url"]:
                continue
            try:
                driver.get(prop["url"])
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "omschrijvingType"))
                )
                time.sleep(1)
                
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                desc_div = detail_soup.select_one("#omschrijvingType")
                
                straatnaam = None
                if desc_div:
                    p_tag = desc_div.find("p")
                    if p_tag:
                        desc_text = p_tag.get_text(strip=True)
                        street_match = re.search(r"aan de\s+([A-Za-z0-9À-ÿ\s\-]+?)(?:\s+(?:met|op|in|,|\.|$))", desc_text, re.IGNORECASE)
                        if not street_match:
                            street_match = re.search(r"aan\s+([A-Za-z0-9À-ÿ\s\-]+?)(?:\s+(?:met|op|in|,|\.|$))", desc_text, re.IGNORECASE)
                        if not street_match:
                            literal = re.search(r"Westerlaan", desc_text, re.IGNORECASE)
                            if literal:
                                straatnaam = "Westerlaan"
                        if street_match:
                            straatnaam = street_match.group(1).strip()

                prop["straatnaam"] = straatnaam if straatnaam else None
                prop["wijk"] = straatnaam if straatnaam else None
                prop["woonplaats"] = "The Park"
                
            except Exception:
                prop["straatnaam"] = None
                prop["wijk"] = None
                prop["woonplaats"] = "The Park"
            
            time.sleep(0.5)
        
        return properties
    finally:
        driver.quit()

def scrape_url(url: str, session=None):
    """Wrapper function for ETL pipeline compatibility."""
    return scrape_houseatthepark(url)

if __name__ == "__main__":
    properties = scrape_houseatthepark()
    print(f"Totaal {len(properties)} woningen gevonden")
    for item in properties:
        print(item)
