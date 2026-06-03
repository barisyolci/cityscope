import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

extracted_data = [
    {"id": 1, "name": "Product A", "price": 100},
    {"id": 2, "name": "Product B", "price": 200},
]

def chunk_data(data, chunk_size=500):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

table_name = "products"
conflict_column = "id" 

total_loaded = 0
for batch in chunk_data(extracted_data, chunk_size=500):
    try:
        response = (
            supabase.table(table_name)
            .upsert(batch, on_conflict=conflict_column)
            .execute()
        )
        total_loaded += len(response.data)
        print(f"Loaded batch... Total: {total_loaded}")
        
    except Exception as e:
        print(f"Error loading batch: {e}")
        raise