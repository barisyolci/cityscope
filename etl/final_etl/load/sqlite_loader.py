import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

def load_to_sqlite(df: pd.DataFrame, db_path: str = "data/properties.db"):
    conn = sqlite3.connect(db_path)
    
    # Create a strict table schema if it doesn't exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS properties (
        property_id TEXT PRIMARY KEY,
        source_url TEXT UNIQUE,
        property_title TEXT,
        price_eur REAL,
        size_sqm REAL,
        num_rooms INTEGER,
        city TEXT,
        latitude REAL,
        longitude REAL,
        last_scraped TIMESTAMP
    );
    """
    conn.execute(create_table_query)
    
    # Use Pandas to_sql with 'append' and handle duplicates
    # The `if_exists='append'` combined with the UNIQUE constraint on source_url 
    # allows us to handle updates cleanly using an upsert logic if needed.
    df.to_sql('properties', conn, if_exists='append', index=False)
    conn.close()

def _record_id(record: Dict, site_key: str, index: int) -> str:
    if record.get("project_id"):
        return str(record["project_id"])
    if record.get("url"):
        return f"{site_key}:{record['url']}"
    return f"{site_key}:{index}"


def load_records_to_sqlite(records: List[Dict], site_key: str, db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS etl_records (
                record_id TEXT PRIMARY KEY,
                site_key TEXT NOT NULL,
                payload TEXT NOT NULL,
                loaded_at TEXT NOT NULL
            )
            """
        )
        insert_sql = "INSERT OR REPLACE INTO etl_records (record_id, site_key, payload, loaded_at) VALUES (?, ?, ?, ?)"
        loaded_at = datetime.utcnow().isoformat() + "Z"
        for index, record in enumerate(records, start=1):
            payload = json.dumps(record, ensure_ascii=False)
            conn.execute(insert_sql, (_record_id(record, site_key, index), site_key, payload, loaded_at))
        conn.commit()
    finally:
        conn.close()
    return db_path
