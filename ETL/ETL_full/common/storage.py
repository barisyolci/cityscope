import json
import logging
from pathlib import Path
from typing import Dict, List

def setup_central_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "scraper.log"
    logger = logging.getLogger("scraper_pipeline")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

def load_json(path: Path) -> List[Dict]:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("projects", data) if isinstance(data, dict) else data
    return []

def save_json(path: Path, data: List[Dict], metadata: Dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {"metadata": metadata, "projects": data}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

def merge_data(new_records: List[Dict], existing_records: List[Dict], unique_key: str) -> List[Dict]:
    existing_map = {rec.get(unique_key): rec for rec in existing_records if rec.get(unique_key)}
    for rec in new_records:
        key = rec.get(unique_key)
        if key:
            existing_map[key] = rec
    return list(existing_map.values())
