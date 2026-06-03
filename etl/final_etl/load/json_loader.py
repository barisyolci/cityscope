import json
from pathlib import Path
from typing import Dict, List


def save_load_json(path: Path, records: List[Dict], metadata: Dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"metadata": metadata, "records": records}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
