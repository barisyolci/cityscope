
# met transform run = python ETL/main.py --site nieuwbouw_rotterdam --stage full
# om data te mergen is voor nu = python ETL/main.py merge
# config/sites.py
CRAWL_DELAY = 5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUTPUT_DIR = "output"
SITES = {
    "nieuwbouw_nl": {
        "sitemap": "https://nieuwbouw.nl/sitemap_project.xml",
        "max_projects": 10,
        "exclude_patterns": [],
        "scraper_module": "extract.nieuwbouw",
        "unique_key": "url"
    },
    "heijmans_nl": {
        "sitemap": "https://heijmansnieuwbouw.nl/sitemap.xml",
        "max_projects": 10,
        "exclude_patterns": [
            "/gerealiseerde-projecten/",
            "/privacy/",
            "/campagne/",
            "/cookieverklaring/",
            "/maximale-hypotheek-berekenen/",
            "/over-heijmans/",
            "/woordenboek/",
            "/stappenplan-",
            "/contact/",
            "/nieuws/",
            "/vacatures/",
            "/algemene-voorwaarden/"
        ],
        "scraper_module": "extract.heijmans",
        "unique_key": "url"
    },
    # "houseatthepark_nl": {
    #     "name": "House at the Park",
    #     "sitemap": None,
    #     "base_url": "https://account.houseatthepark.nl/aanbod/#/",
    #     "scraper_module": "extract.hatp",
    #     "unique_key": "bouwnummer",
    #     "exclude_patterns": [],
    #     "max_projects": 10
    # },
    "huurwoningen_rotterdam": {
        "name": "Huurwoningen Rotterdam",
        "listing_url": "https://www.huurwoningen.com/nieuwbouw/huren/rotterdam/",
        "base_url": "https://www.huurwoningen.com/nieuwbouw/huren/rotterdam/",
        "sitemap": None,
        "scraper_module": "extract.huurwoningen",
        "unique_key": "url",
        "max_projects": 10,
        "exclude_patterns": []
    },
    "nieuwbouw_rotterdam": {
        "name": "Nieuwbouw Rotterdam",
        "listing_url": "https://www.nieuwbouw-rotterdam.nl/projecten/",
        "base_url": "https://www.nieuwbouw-rotterdam.nl/projecten/",
        "sitemap": None,
        "scraper_module": "extract.nieuwbouw_rotterdam",
        "unique_key": "url",
        "max_projects": 10,
        "exclude_patterns": []
    }
}
