import requests
from typing import Optional, Dict


def lookup_fuzzy(name: str) -> Optional[Dict]:
    try:
        r = requests.get(
            "https://api.scryfall.com/cards/named", params={"fuzzy": name}, timeout=10
        )
        if r.status_code != 200:
            return None
        j = r.json()
        return {
            "name": j.get("name"),
            "id": j.get("id"),
            "uri": j.get("scryfall_uri"),
            "set": j.get("set"),
        }
    except Exception:
        return None
