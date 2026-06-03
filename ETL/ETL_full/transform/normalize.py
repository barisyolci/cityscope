import re
from typing import Any, Dict, List, Optional


def normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return re.sub(r"\s+", " ", text)


def parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    digits = re.findall(r"\d+", text.replace(".", "").replace(",", ""))
    return int(digits[0]) if digits else None


def parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("€", "").replace(" ", "").replace("\xa0", "")
    if text.count(",") > 0 and text.count(".") == 0:
        text = text.replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_nieuwbouw_record(record: Dict[str, Any]) -> Dict[str, Any]:
    url = normalize_text(record.get("url"))
    naam = normalize_text(record.get("naam")) or normalize_text(record.get("Project"))
    
    # Handle price - if "n.n.b." then None, otherwise try to parse
    prijs = record.get("prijs")
    prijs_min = None
    prijs_max = None
    if prijs and prijs != "n.n.b." and prijs.lower() != "n.n.b.":
        prijs_val = parse_float(prijs)
        if prijs_val:
            prijs_min = prijs_val
            prijs_max = prijs_val
    
    # Fallback to prijs_min/prijs_max fields if they exist
    if not prijs_min:
        prijs_min = parse_float(record.get("prijs_min")) or parse_float(record.get("Prijs van"))
    if not prijs_max:
        prijs_max = parse_float(record.get("prijs_max")) or parse_float(record.get("Prijs tot"))
    
    return {
        "project_id": url,
        "source": "nieuwbouw_nl",
        "url": url,
        "naam": naam,
        "straatnaam": normalize_text(record.get("straatnaam")) or normalize_text(record.get("wijk")),
        "stad": normalize_text(record.get("stad")) or "Rotterdam",
        "woonplaats": normalize_text(record.get("woonplaats")),
        "wijk": normalize_text(record.get("wijk")),
        "aantal_woningen": parse_int(record.get("aantal_woningen")),
        "prijs_min": prijs_min,
        "prijs_max": prijs_max,
        "woonoppervlakte": normalize_text(record.get("woonoppervlakte")),
        "start_verkoop": normalize_text(record.get("start_verkoop")),
        "start_bouw": normalize_text(record.get("start_bouw")),
        "woningtypes": ensure_list(record.get("woningtypes")),
        "bouwnummers": ensure_list(record.get("bouwnummers")),
        "provided_by": normalize_text(record.get("provided_by")),
        "huur_of_koop": normalize_text(record.get("huur_of_koop")),
        "omschrijving": normalize_text(record.get("omschrijving")) or normalize_text(record.get("description")),
    }


def normalize_hatp_record(record: Dict[str, Any]) -> Dict[str, Any]:
    bouwnummer = normalize_text(record.get("bouwnummer"))
    naam = normalize_text(record.get("naam")) or (f"House at the Park {bouwnummer}" if bouwnummer else None)
    return {
        "project_id": f"houseatthepark_nl:{bouwnummer}" if bouwnummer else None,
        "source": "houseatthepark_nl",
        "url": normalize_text(record.get("url")),
        "naam": naam,
        "bouwnummer": bouwnummer,
        "status": normalize_text(record.get("status")),
        "woningtype": normalize_text(record.get("woningtype")),
        "verdieping": normalize_text(record.get("verdieping")),
        "woonoppervlakte": parse_float(record.get("woonoppervlakte")) or normalize_text(record.get("woonoppervlakte")),
        "balkon_grootte": parse_float(record.get("balkon_grootte")),
        "slaapkamers": parse_int(record.get("slaapkamers")),
        "prijs": parse_float(record.get("prijs")),
        "straatnaam": normalize_text(record.get("straatnaam")),
        "wijk": normalize_text(record.get("wijk")),
        "woonplaats": normalize_text(record.get("woonplaats")) or "The Park",
    }


def normalize_heijmans_record(record: Dict[str, Any]) -> Dict[str, Any]:
    url = normalize_text(record.get("url"))
    # Use straatnaam as naam since scraper returns straatnaam instead of naam
    naam = normalize_text(record.get("straatnaam")) or normalize_text(record.get("naam"))
    return {
        "project_id": url,
        "source": "heijmans_nl",
        "url": url,
        "naam": naam,
        "straatnaam": naam,
        "stad": normalize_text(record.get("stad")) or "Rotterdam",
        "woonplaats": normalize_text(record.get("woonplaats")),
        "wijk": normalize_text(record.get("wijk")),
        "aantal_woningen": parse_int(record.get("aantal_woningen")),
        "prijs_min": parse_float(record.get("prijs_min")),
        "prijs_max": parse_float(record.get("prijs_max")),
        "woonoppervlakte": normalize_text(record.get("woonoppervlakte")),
        "start_verkoop": normalize_text(record.get("start_verkoop")),
        "start_bouw": normalize_text(record.get("start_bouw")),
        "woningtypes": ensure_list(record.get("woningtypes")),
        "bouwnummers": ensure_list(record.get("bouwnummers")),
        "provided_by": normalize_text(record.get("provided_by")),
        "huur_of_koop": normalize_text(record.get("huur_of_koop")),
    }


def normalize_huurwoningen_record(record: Dict[str, Any]) -> Dict[str, Any]:
    url = normalize_text(record.get("url"))
    naam = normalize_text(record.get("naam")) or normalize_text(record.get("straatnaam"))
    return {
        "project_id": record.get("project_id") or url,
        "source": "huurwoningen_rotterdam",
        "url": url,
        "naam": naam,
        "straatnaam": normalize_text(record.get("straatnaam")),
        "stad": normalize_text(record.get("stad")) or "Rotterdam",
        "woonplaats": normalize_text(record.get("woonplaats")),
        "latitude": parse_float(record.get("latitude")),
        "longitude": parse_float(record.get("longitude")),
        "aantal_woningen": 1,
        "prijs_min": parse_float(record.get("prijs_min")) or parse_float(record.get("prijs")),
        "prijs_max": parse_float(record.get("prijs_max")) or parse_float(record.get("prijs")),
        "woonoppervlakte": parse_int(record.get("woonoppervlakte")),
        "aantal_slaapkamers": parse_int(record.get("aantal_slaapkamers")),
        "bathroom_descr": normalize_text(record.get("bathroom_descr")),
        "balkon_present": record.get("balkon_present", False),
        "balkon_grootte": normalize_text(record.get("balkon_grootte")),
        "omschrijving": normalize_text(record.get("omschrijving")),
        "images": ensure_list(record.get("images")),
        "woningtypes": ensure_list(record.get("woningtypes")),
        "beschrijving": normalize_text(record.get("beschrijving")),
        "start_verkoop": normalize_text(record.get("start_verkoop")),
        "prijs_per_m2": parse_float(record.get("prijs_per_m2")),
        "aangeboden_sinds": normalize_text(record.get("aangeboden_sinds")),
        "soort_bouw": normalize_text(record.get("soort_bouw")),
        "bouwjaar": parse_int(record.get("bouwjaar")),
        "aantal_kamers": parse_int(record.get("aantal_kamers")),
        "aantal_badkamers": parse_int(record.get("aantal_badkamers")),
        "aantal_woonlagen": parse_int(record.get("aantal_woonlagen")),
        "voorzieningen": normalize_text(record.get("voorzieningen")),
        "tuin_present": record.get("tuin_present", False),
        "dakterras_present": record.get("dakterras_present", False),
        "energielabel": normalize_text(record.get("energielabel")),
        "parkeergelegenheid": normalize_text(record.get("parkeergelegenheid")),
        "bron": "huurwoningen.com",
    }


def normalize_nieuwbouw_rotterdam_record(record: Dict[str, Any]) -> Dict[str, Any]:
    url = normalize_text(record.get("url"))
    naam = normalize_text(record.get("naam"))
    return {
        "project_id": record.get("project_id") or url,
        "source": "nieuwbouw_rotterdam",
        "url": url,
        "naam": naam,
        "straatnaam": normalize_text(record.get("straatnaam")),
        "stad": normalize_text(record.get("stad")) or "Rotterdam",
        "woonplaats": normalize_text(record.get("woonplaats")) or "Rotterdam",
        "latitude": parse_float(record.get("latitude")),
        "longitude": parse_float(record.get("longitude")),
        "aantal_woningen": parse_int(record.get("aantal_woningen")),
        "prijs_min": parse_float(record.get("prijs_min")),
        "prijs_max": parse_float(record.get("prijs_max")),
        "woonoppervlakte": normalize_text(record.get("woonoppervlakte")),
        "aantal_slaapkamers": normalize_text(record.get("aantal_slaapkamers")),
        "bathroom_descr": normalize_text(record.get("bathroom_descr")),
        "balkon_present": record.get("balkon_present", False),
        "balkon_grootte": normalize_text(record.get("balkon_grootte")),
        "apartement_descr": normalize_text(record.get("apartement_descr")),
        "images": ensure_list(record.get("images")),
        "woningtypes": ensure_list(record.get("woningtypes")),
        "beschrijving": normalize_text(record.get("beschrijving")),
        "start_verkoop": normalize_text(record.get("start_verkoop")),
        "bron": "nieuwbouw-rotterdam.nl",
    }


def normalize_site_records(records: List[Dict[str, Any]], site_key: str) -> List[Dict[str, Any]]:
    if site_key == "nieuwbouw_nl":
        return [normalize_nieuwbouw_record(record) for record in records if isinstance(record, dict)]
    if site_key == "houseatthepark_nl":
        return [normalize_hatp_record(record) for record in records if isinstance(record, dict)]
    if site_key == "heijmans_nl":
        return [normalize_heijmans_record(record) for record in records if isinstance(record, dict)]
    if site_key == "huurwoningen_rotterdam":
        return [normalize_huurwoningen_record(record) for record in records if isinstance(record, dict)]
    if site_key == "nieuwbouw_rotterdam":
        return [normalize_nieuwbouw_rotterdam_record(record) for record in records if isinstance(record, dict)]
    return [record for record in records if isinstance(record, dict)]
