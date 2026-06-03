import re
from datetime import datetime

def clean_price(raw_price: str) -> float:
    """Converts '€ 250.000,-' or '1200 ex.' to 250000.0 or 1200.0"""
    if not raw_price: return None
    # Remove currency symbols, spaces, dots, and text
    cleaned = re.sub(r'[^\d]', '', str(raw_price))
    return float(cleaned) if cleaned else None

def clean_size(raw_size: str) -> float:
    """Converts '85 m²' or '85m2' to 85.0"""
    if not raw_size: return None
    match = re.search(r'(\d+)', str(raw_size))
    return float(match.group(1)) if match else None

def standardize_date(raw_date: str) -> str:
    """Converts any date string to ISO 8601 (YYYY-MM-DD)"""
    # Add your date parsing logic here (e.g., using dateutil.parser)
    pass