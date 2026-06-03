# ETL Pipeline - Vastgoed Projecten

Een compleet Extract-Transform-Load pipeline voor het verzamelen en verwerken van data van Nederlandse vastgoedprojecten.

## Structuur

```
ETL/
├── extract/           # Scrapers voor 3 vastgoedsites
│   ├── hatp.py        # House at the Park (Selenium-gebaseerd)
│   ├── heijmans.py    # Heijmans Nieuwbouw
│   └── nieuwbouw.py   # Nieuwbouw.nl
│
├── transform/         # Normalisatie en transformatie
│   ├── normalize.py   # Site-specifieke normalisatie
│   └── merge.py       # Merging van alle sites + geocoding
│
├── load/              # (momenteel leeg voor toekomstige use)
│   ├── json_loader.py
│   └── sqlite_loader.py
│
├── common/            # Gedeelde utilities
│   ├── http.py        # Session & retry logic
│   ├── sitemap.py     # Sitemap parsing
│   └── storage.py     # Logging & data I/O
│
├── config/
│   └── sites.py       # Site configuratie & credentials
│
├── output/            # Gegenereerde data (niet in repo)
│   ├── data/          # Extract stage output
│   ├── transform/     # Transform stage output
│   ├── load/          # Load stage output
│   └── logs/          # Scrapy logs
│
├── main.py            # Orchestrator script
└── requirements.txt   # Dependencies
```

## Installatie

```bash
pip install -r requirements.txt
```

## Gebruik

### Extract (scrapen)

```bash
python main.py --site nieuwbouw_nl --stage extract
python main.py --site houseatthepark_nl --stage extract
python main.py --site heijmans_nl --stage extract
```

### Transform (normalisatie)

```bash
python main.py --site nieuwbouw_nl --stage transform
```

### Load (naar JSON/SQLite)

```bash
python main.py --site nieuwbouw_nl --stage load
```

### Full pipeline (extract → transform → load)

```bash
python main.py --site nieuwbouw_nl --stage full
```

### Merge alle sites

```bash
python main.py merge
```

## Data

### Extract Output
- **Locatie**: `output/data/{site}.json`
- **Format**: JSON met `metadata` + `projects` array
- **Content**: Ruwe data van scrapers

### Transform Output
- **Locatie**: `output/transform/{site}.json`
- **Format**: Genormaliseerde records
- **Transformaties**: Type conversie, validatie, standaardisatie

### Load Output
- **Locatie**: `output/load/{site}.json` en `output/load/{site}.sqlite`
- **Format**: JSON met `metadata` + `records` array, SQLite met `etl_records` table

### Merged Output
- **Locatie**: `output/merged_all_sites.json`
- **Format**: Alle records in unified schema
- **Transformaties**: Geocoding, woningtype normalisatie, deduplicatie

## Sites

### 1. Nieuwbouw.nl
- **Type**: Project-level data
- **Scraper**: `extract/nieuwbouw.py`
- **Features**: Woningtypes, provided_by, huur_of_koop
- **Unique Key**: URL

### 2. House at the Park
- **Type**: Property-level data
- **Scraper**: `extract/hatp.py` (Selenium)
- **Features**: JavaScript rendering, detail pages
- **Unique Key**: Bouwnummer

### 3. Heijmans Nieuwbouw
- **Type**: Project-level data  
- **Scraper**: `extract/heijmans.py`
- **Features**: Price parsing, Rotterdam region filtering
- **Unique Key**: URL

### 4. Huurwoningen Rotterdam ⭐ (Nieuw!)
- **Type**: Property-level data
- **Scraper**: `extract/huurwoningen.py`
- **Source**: https://www.huurwoningen.com/nieuwbouw/huren/rotterdam/
- **Features**: JSON-LD parsing, geocoördinaten, huisprijzen
- **Unique Key**: URL

### 5. Nieuwbouw Rotterdam ⭐ (Nieuw!)
- **Type**: Project-level data
- **Scraper**: `extract/nieuwbouw_rotterdam.py`
- **Source**: https://www.nieuwbouw-rotterdam.nl/projecten/
- **Features**: Projectgegevens, prijsrange, woningtype mix
- **Unique Key**: URL

## Configuratie

Edit `config/sites.py` om:
- Max aantal projecten per site aan te passen
- URL exclude patterns te wijzigen
- Crawl delay in te stellen

## Logging

Alle operaties worden gelogd naar:
- **Console**: Real-time output
- **File**: `output/logs/scraper.log`

## Dependencies

- `beautifulsoup4`: HTML parsing
- `requests`: HTTP requests
- `selenium`: JavaScript rendering
- `webdriver-manager`: Automatic ChromeDriver management
- `urllib3`: HTTP client

## Toekomstige Extensies

- Load stage: Database/datawarehouse integratie
- Validatie stage: Data quality checks
- API endpoints voor data access
- Visualisatie dashboard
