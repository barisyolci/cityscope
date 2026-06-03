import argparse
import importlib
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from config.sites import SITES, CRAWL_DELAY, OUTPUT_DIR
from common.http import create_session
from common.sitemap import fetch_urls_from_sitemap, fetch_urls_from_listing
from common.storage import setup_central_logging, load_json, save_json, merge_data
from transform.normalize import normalize_site_records
from transform.merge import merge_all_sites
from transform.validator import process_and_validate
from load.json_loader import save_load_json
from load.sqlite_loader import load_records_to_sqlite
from load.supabase_loader import load_records_to_supabase

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / OUTPUT_DIR / "logs"
DATA_DIR = BASE_DIR / OUTPUT_DIR / "data"
TRANSFORM_DIR = BASE_DIR / OUTPUT_DIR / "transform"
LOAD_DIR = BASE_DIR / OUTPUT_DIR / "load"
STAGE_CHOICES = ["extract", "transform", "load", "full"]

def run_extract(site_key: str): 
    if site_key not in SITES:
        print(f"[FOUT] Site '{site_key}' niet gevonden in config.")
        return

    config = SITES[site_key]
    logger = setup_central_logging(LOG_DIR)
    logger.info(f"START EXTRACT | Site: {site_key}")

    session = create_session()
    if config.get("sitemap"):
        logger.info("URLs ophalen uit sitemap...")
        urls = fetch_urls_from_sitemap(config["sitemap"], session, config.get("exclude_patterns", []))
    elif config.get("listing_url"):
        logger.info("URLs ophalen uit listing page...")
        urls = fetch_urls_from_listing(config["listing_url"], session)
        if site_key == "huurwoningen_rotterdam":
            urls = [u for u in urls if '/huren/rotterdam/' in u and 'nieuwbouw' not in u]
        elif site_key == "nieuwbouw_rotterdam":
            urls = [u for u in urls if '/projecten/kaart/' not in u and ('/project/' in u or u.endswith('/projecten/'))]
    else:
        logger.info("Geen sitemap, gebruik base_url...")
        urls = [config.get("base_url", "")]

    if site_key == "heijmans_nl":
        urls = [url for url in urls if "/projecten/" in url and url.rstrip("/").split("/")[-1] and url.rstrip("/").split("/")[-1] != "projecten"]

    if config.get("max_projects"):
        urls = urls[: config["max_projects"]]
    logger.info(f"Te verwerken URLs: {len(urls)}")

    logger.info("Scraper module laden...")
    scraper_module = importlib.import_module(config["scraper_module"])

    existing_data = load_json(DATA_DIR / f"{site_key}.json")
    logger.info(f"Bestaande records in database: {len(existing_data)}")

    new_records = []
    success_count = 0
    error_urls = []

    for i, url in enumerate(urls, 1):
        if not url or url.strip() == "":
            continue
        print(f"[{i}/{len(urls)}] {url}")
        try:
            data = scraper_module.scrape_url(url, session)
            if data:
                if isinstance(data, list):
                    new_records.extend(data)
                    success_count += len(data)
                else:
                    new_records.append(data)
                    success_count += 1
            else:
                error_urls.append(url)
                logger.warning(f"LEEG RESULTAAT | Site: {site_key} | URL: {url}")
        except Exception as e:
            error_urls.append(url)
            logger.error(f"EXTRACTIE FOUT | Site: {site_key} | URL: {url} | Error: {e}")

        if i < len(urls):
            time.sleep(CRAWL_DELAY)

    logger.info(f"EXTRACT VOLTOOID | Site: {site_key} | Succes: {success_count} | Fouten: {len(error_urls)}")

    valid_records = process_and_validate(new_records)
    logger.info(f"VALIDATIE VOLTOOID | {len(valid_records)} geldige records over van {len(new_records)}.")

    merged_data = merge_data(valid_records, existing_data, config.get("unique_key", "url"))
    metadata = {
        "site": site_key,
        "stage": "extract",
        "last_updated": datetime.now().isoformat(),
        "total_projects": len(merged_data),
        "scraped_this_run": success_count,
        "errors_this_run": len(error_urls),
    }
    save_json(DATA_DIR / f"{site_key}.json", merged_data, metadata)
    logger.info(f"EXTRACT DATABASE GEUPDATET | Pad: {DATA_DIR / f'{site_key}.json'}")
    session.close()

def run_transform(site_key: str):
    if site_key not in SITES:
        print(f"[FOUT] Site '{site_key}' niet gevonden in config.")
        return

    logger = setup_central_logging(LOG_DIR)
    logger.info(f"START TRANSFORM | Site: {site_key}")

    raw_data = load_json(DATA_DIR / f"{site_key}.json")
    if not raw_data:
        logger.warning(f"Geen extract gegevens gevonden voor {site_key}. Voer eerst extract uit.")
        return

    transformed = normalize_site_records(raw_data, site_key)
    metadata = {
        "site": site_key,
        "stage": "transform",
        "last_updated": datetime.now().isoformat(),
        "total_projects": len(transformed),
    }
    save_json(TRANSFORM_DIR / f"{site_key}.json", transformed, metadata)
    logger.info(f"TRANSFORM VOLTOOID | Pad: {TRANSFORM_DIR / f'{site_key}.json'}")
    return transformed

def run_load(site_key: str):
    if site_key not in SITES:
        print(f"[FOUT] Site '{site_key}' niet gevonden in config.")
        return

    logger = setup_central_logging(LOG_DIR)
    logger.info(f"START LOAD | Site: {site_key}")

    transform_path = TRANSFORM_DIR / f"{site_key}.json"
    source_path = transform_path if transform_path.exists() else DATA_DIR / f"{site_key}.json"
    if not source_path.exists():
        logger.warning(f"Geen data gevonden om te laden voor {site_key}. Voer eerst extract of transform uit.")
        return

    records = load_json(source_path)
    metadata = {
        "site": site_key,
        "stage": "load",
        "last_updated": datetime.now().isoformat(),
        "total_records": len(records),
    }
    save_load_json(LOAD_DIR / f"{site_key}.json", records, metadata)
    
    db_path = LOAD_DIR / f"{site_key}.sqlite"
    load_records_to_sqlite(records, site_key, db_path)
    
    # FIX: 'cleaned_data' bestond niet, we gebruiken 'records' (de opgehaalde data)
    logger.info("START SUPABASE LOAD...")
    load_records_to_supabase(records, table_name="algemene_info") 
    
    logger.info(f"LOAD VOLTOOID | JSON: {LOAD_DIR / f'{site_key}.json'} | DB: {db_path}")

def run_merge():
    logger = setup_central_logging(LOG_DIR)
    logger.info("START MERGE | Combining all site outputs")
    
    try:
        merge_all_sites(str(LOAD_DIR))
        logger.info("MERGE VOLTOOID")
    except Exception as e:
        logger.error(f"MERGE FOUT | {e}")

def run_site(site_key: str, stage: str = "extract"):
    if stage == "extract":
        return run_extract(site_key)
    if stage == "transform":
        return run_transform(site_key)
    if stage == "load":
        return run_load(site_key)
    if stage == "full":
        run_extract(site_key)
        run_transform(site_key)
        run_load(site_key)
        return
    print(f"[FOUT] Ongeldig stage: {stage}. Kies uit: {', '.join(STAGE_CHOICES)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL Pipeline voor vastgoedprojecten")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    site_parser = subparsers.add_parser("site", help="Run pipeline for a different site")
    site_parser.add_argument("--site", required=True, help="Site key")
    site_parser.add_argument("--stage", choices=STAGE_CHOICES, default="extract", help="Run stage")
    
    merge_parser = subparsers.add_parser("merge", help="Merge all sites into unified format")
    
    parser.add_argument("--site", help="Site key (legacy format)")
    parser.add_argument("--stage", choices=STAGE_CHOICES, default="extract", help="Run stage (legacy format)")
    
    args = parser.parse_args()
    
    if args.command == "site":
        run_site(args.site, args.stage)
    elif args.command == "merge":
        run_merge()
    elif args.site:
        run_site(args.site, args.stage)
    else:
        parser.print_help()