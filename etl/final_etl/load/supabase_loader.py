import os
import logging
from typing import List, Dict
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def load_records_to_supabase(records: List[Dict], table_name: str = "properties"):

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 

    if not url or not key:
        logger.error("SUPABASE_URL of SUPABASE_SERVICE_ROLE_KEY niet gevonden in .env")
        return

    supabase: Client = create_client(url, key)

    def chunk_data(data, chunk_size=500):
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]

    logger.info(f"START SUPABASE LOAD | {len(records)} records te verwerken...")
    total_loaded = 0

    for batch in chunk_data(records, chunk_size=500):
        try:

            response = (
                supabase.table(table_name)
                .upsert(batch, on_conflict="url")  
                .execute()
            )
            total_loaded += len(response.data)
            logger.info(f"Batch geladen. Totaal verwerkt: {total_loaded}")
        except Exception as e:
            logger.error(f"Fout bij laden naar Supabase: {e}")
            raise 
            
    logger.info(f"SUPABASE LOAD VOLTOOID | {total_loaded} records succesvol geladen.")