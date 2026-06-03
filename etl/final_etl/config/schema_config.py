# The "Canonical" names your database will actually use
CANONICAL_COLUMNS = {
    'id': 'property_id',
    'url': 'source_url',
    'title': 'property_title',
    'price': 'price_eur',
    'size': 'size_sqm',
    'rooms': 'num_rooms',
    'type': 'property_type',
    'city': 'city',
    'lat': 'latitude',
    'lon': 'longitude',
    'scraped_at': 'last_scraped'
}

# Mapping from raw scraper outputs to Canonical names
SITE_MAPPINGS = {
    'heijmans_nl': {
        'vraagprijs': 'price_eur',
        'oppervlakte': 'size_sqm',
        'aantal_kamers': 'num_rooms'
    },
    'huurwoningen_rotterdam': {
        'huurprijs': 'price_eur',
        'woningtype': 'property_type',
        'inhoud': 'volume_m3'
    }
}