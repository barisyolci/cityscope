import sys
import os
from pathlib import Path
from dagster import asset, AssetExecutionContext, get_dagster_logger

# --- SIMPLE, EXPLICIT PATH RESOLUTION ---
ETL_DIR = Path(__file__).resolve().parent.parent.parent

print(f"DEBUG: ETL_DIR resolved to: {ETL_DIR}")

# Base paths to inject into the subprocess
PATHS_TO_INJECT = [
    str(ETL_DIR),
    str(ETL_DIR / 'extract'),
    str(ETL_DIR / 'transform'),
    str(ETL_DIR / 'load'),
    str(ETL_DIR / 'common'),
    str(ETL_DIR / 'config'),
    '' # Current directory
]

if str(ETL_DIR) not in sys.path:
    sys.path.insert(0, str(ETL_DIR))

from main import run_extract, run_transform, run_load, run_merge
from config.sites import SITES

logger = get_dagster_logger()

def make_extract_asset(site_key):
    @asset(
        name=f"extract_{site_key}", 
        group_name="cityscope_etl",
        description=f"Extracts raw property data for {site_key}"
    )
    def extract_asset(context: AssetExecutionContext):
        os.chdir(ETL_DIR) 
        # BRUTE FORCE PATH INJECTION FOR SUBPROCESSES
        for p in PATHS_TO_INJECT:
            if p not in sys.path: sys.path.insert(0, p)
            
        logger.info(f"Starting Extract stage for {site_key}")
        run_extract(site_key)
        logger.info(f"Finished Extract stage for {site_key}")
    return extract_asset

def make_transform_asset(site_key):
    @asset(
        name=f"transform_{site_key}", 
        deps=[f"extract_{site_key}"], 
        group_name="cityscope_etl",
        description=f"Normalizes extracted data for {site_key}"
    )
    def transform_asset(context: AssetExecutionContext):
        os.chdir(ETL_DIR)
        for p in PATHS_TO_INJECT:
            if p not in sys.path: sys.path.insert(0, p)
        
        logger.info(f"Starting Transform stage for {site_key}")
        run_transform(site_key)
        logger.info(f"Finished Transform stage for {site_key}")
    return transform_asset

def make_load_asset(site_key):
    @asset(
        name=f"load_{site_key}", 
        deps=[f"transform_{site_key}"], 
        group_name="cityscope_etl",
        description=f"Loads normalized data for {site_key} into SQLite"
    )
    def load_asset(context: AssetExecutionContext):
        os.chdir(ETL_DIR)
        for p in PATHS_TO_INJECT:
            if p not in sys.path: sys.path.insert(0, p)
        
        logger.info(f"Starting Load stage for {site_key}")
        run_load(site_key)
        logger.info(f"Finished Load stage for {site_key}")
    return load_asset

def create_site_assets():
    assets = []
    for site_key in SITES.keys():
        assets.append(make_extract_asset(site_key))
        assets.append(make_transform_asset(site_key))
        assets.append(make_load_asset(site_key))
    return assets

site_assets = create_site_assets()

@asset(
    deps=[f"load_{site_key}" for site_key in SITES.keys()], 
    group_name="cityscope_etl",
    description="Merges all site databases into a unified master dataset"
)
def merge_all_sites_asset(context: AssetExecutionContext):
    os.chdir(ETL_DIR) 
    for p in PATHS_TO_INJECT:
        if p not in sys.path: sys.path.insert(0, p)
    
    logger.info("Starting Merge stage for all sites")
    run_merge()
    logger.info("Finished Merge stage for all sites")

all_assets = site_assets + [merge_all_sites_asset]