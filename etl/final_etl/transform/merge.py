import json
import os
import time
from datetime import datetime
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

geolocator = Nominatim(user_agent="real_estate_merger_app_v1")

CACHE_FILE = Path('geocode_cache.json')

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

geocode_cache = load_cache()

WONINGTYPE_MAPPING = {
    '2-kamerappartement': 'Appartement',
    '3-kamerappartement': 'Appartement',
    '2-kamer': 'Appartement',
    '3-kamer': 'Appartement',
    'appartement': 'Appartement',
    'vrijstaande woning': 'Vrijstaande woning',
    'tussenwoning': 'Tussenwoning',
    'twee-onder-een-kapwoning': 'Twee-onder-een-kapwoning',
    'herenhuis': 'Herenhuis',
    'kavel': 'Kavel',
    'penthouse': 'Penthouse',
}

def geocode_location(stad=None, woonplaats=None, straatnaam=None):
    parts = []
    if straatnaam:
        parts.append(straatnaam.strip())
    if woonplaats:
        parts.append(woonplaats.strip())
    if stad and stad.strip().lower() not in [p.lower() for p in parts]:
        parts.append(stad.strip())
    
    if not parts:
        return None, None
        
    query = ", ".join(parts) + ", Netherlands"
    
    if query in geocode_cache:
        return tuple(geocode_cache[query])
        
    try:
        print(f"Geocoding (API call): {query}...")
        time.sleep(1) 
        location = geolocator.geocode(query, timeout=10)
        if location:
            coords = (location.latitude, location.longitude)
            geocode_cache[query] = coords
            return coords
        else:
            geocode_cache[query] = (None, None)
            return None, None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding service error for {query}: {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected geocoding error for {query}: {e}")
        return None, None

def standardize_woningtype(woningtype_str):
    if not woningtype_str:
        return woningtype_str
    
    key = woningtype_str.lower().strip()
    return WONINGTYPE_MAPPING.get(key, woningtype_str)

def standardize_woningtypes_list(woningtypes_list):
    if not woningtypes_list or not isinstance(woningtypes_list, list):
        return woningtypes_list
    
    standardized = [standardize_woningtype(w) for w in woningtypes_list]
    seen = set()
    result = []
    for w in standardized:
        if w not in seen:
            seen.add(w)
            result.append(w)
    return result

def standardize_woonplaats(woonplaats):
    if not woonplaats:
        return woonplaats
    return woonplaats.strip().title()

def standardize_naam(naam):
    if not naam:
        return naam
    return naam.strip()

def transform_houseatthepark_record(record):
    # HATP Transform 1: prijs -> prijs_min & prijs_max
    if 'prijs' in record:
        prijs = record.pop('prijs')
        record['prijs_min'] = prijs
        record['prijs_max'] = prijs
    else:
        record['prijs_min'] = None
        record['prijs_max'] = None
    
    # HATP Transform 2: woningtype -> woningtypes [array]
    if 'woningtype' in record:
        woningtype = record.pop('woningtype')
        record['woningtypes'] = [woningtype] if woningtype else []
    else:
        record['woningtypes'] = []
    
    # HATP Transform 3: bouwnummer -> bouwnummers [array]
    if 'bouwnummer' in record:
        bouwnummer = record.pop('bouwnummer')
        record['bouwnummers'] = [bouwnummer] if bouwnummer else []
    else:
        record['bouwnummers'] = []
    
    # HATP Transform 4: woonoppervlakte (float) -> string
    if 'woonoppervlakte' in record:
        woonoppervlakte = record['woonoppervlakte']
        if isinstance(woonoppervlakte, (int, float)):
            record['woonoppervlakte'] = str(int(woonoppervlakte)) if woonoppervlakte else None
    
    return record

def add_missing_fields(record, site):
    all_fields = {
        'project_id', 'source', 'url', 'naam', 'straatnaam', 'stad', 'woonplaats', 'wijk', 
        'aantal_woningen', 'prijs_min', 'prijs_max', 'woonoppervlakte',
        'start_verkoop', 'start_bouw', 'woningtypes', 'bouwnummers',
        'provided_by', 'huur_of_koop', 'bron',
        'latitude', 'longitude',
        'status', 'verdieping', 'balkon_grootte', 'slaapkamers', 'bouwnummer',
        'aantal_slaapkamers', 'bathroom_descr', 'balkon_present', 'apartement_descr', 'images', 'beschrijving',
        'omschrijving', 'prijs_per_m2', 'aangeboden_sinds', 'soort_bouw', 'bouwjaar', 'aantal_kamers', 
        'aantal_badkamers', 'aantal_woonlagen', 'voorzieningen', 'tuin_present', 'dakterras_present', 
        'energielabel', 'parkeergelegenheid'
    }
    
    for field in all_fields:
        if field not in record:
            record[field] = None
    
    return record

def merge_all_sites(output_dir='output/load'):
    all_records = []
    load_dir = Path(output_dir)
    output_file = load_dir / 'merged_all_sites.json'
    
    site_files = [
        'heijmans_nl.json',
        'nieuwbouw_nl.json',
        'huurwoningen_rotterdam.json',
        'nieuwbouw_rotterdam.json'
    ]
    
    for filename in site_files:
        filepath = load_dir / filename
        if not filepath.exists():
            print(f"File niet gevonden: {filepath}")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        site = data['metadata']['site']
        records = data['records']
        
        print(f"Loading {site}: {len(records)} records")
        
        for record in records:
            if site == 'houseatthepark_nl':
                record = transform_houseatthepark_record(record)
            
            record = add_missing_fields(record, site)
            
            record['naam'] = standardize_naam(record.get('naam'))
            record['woonplaats'] = standardize_woonplaats(record.get('woonplaats'))
            record['woningtypes'] = standardize_woningtypes_list(record.get('woningtypes'))
            
            lat, lng = geocode_location(
                stad=record.get('stad'),
                woonplaats=record.get('woonplaats'),
                straatnaam=record.get('straatnaam')
            )
            record['latitude'] = lat
            record['longitude'] = lng
            
            all_records.append(record)
    
    output = {
        'metadata': {
            'stage': 'merged',
            'total_records': len(all_records),
            'last_updated': datetime.now().isoformat(),
            'transforms_applied': [
                'houseatthepark_nl: prijs -> prijs_min/prijs_max',
                'houseatthepark_nl: woningtype -> woningtypes (array)',
                'houseatthepark_nl: bouwnummer -> bouwnummers (array)',
                'All sites: add missing fields (None for absent)',
                'All sites: standardize naam (trim whitespace)',
                'All sites: standardize woonplaats (title case)',
                'All sites: standardize woningtypes (normalize names)',
                'All sites: geocoding via Geopy (straatnaam/woonplaats/stad -> latitude, longitude)'
            ]
        },
        'records': all_records
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    save_cache(geocode_cache)
    
    print(f"\nMerged output: {output_file}")
    print(f"Total records: {len(all_records)}")
    
    return output_file

if __name__ == '__main__':
    merge_all_sites()