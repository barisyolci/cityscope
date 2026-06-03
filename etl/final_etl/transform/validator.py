import json
import os
from transform.cleaners import clean_price, clean_size 

def process_and_validate(raw_records):
    valid_records = []
    invalid_records = []
    
    for record in raw_records:
        try:
            record['price'] = clean_price(record.get('raw_price', record.get('price')))
            record['size'] = clean_size(record.get('raw_size', record.get('size')))
            
            if record.get('price') is None or record['price'] < 0:
                raise ValueError("Invalid or missing Price")
            if not record.get('source_url'):
                raise ValueError("Missing Source URL")
                
            valid_records.append(record)
            
        except Exception as e:
            record['error_reason'] = str(e)
            invalid_records.append(record)
            
    if invalid_records:
        os.makedirs("output", exist_ok=True)
        dlq_path = "output/dead_letter_queue.json"
        
        existing_errors = []
        if os.path.exists(dlq_path):
            with open(dlq_path, 'r', encoding='utf-8') as f:
                existing_errors = json.load(f)
                
        existing_errors.extend(invalid_records)
        
        with open(dlq_path, 'w', encoding='utf-8') as f:
            json.dump(existing_errors, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(invalid_records)} invalid records to {dlq_path}")
            
    return valid_records