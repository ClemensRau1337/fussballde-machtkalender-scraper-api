from typing import Dict, List
from ..config import REQUEST_TIMEOUT
from .http import get_json
from ..config import BASE


def get_postal_codes(query: str = "Hamburg") -> List[Dict[str, str]]:
    url = f"{BASE}/public.service/-/action/getPostalCodeCompletions/plz/{query}"
    data = get_json(url, timeout=REQUEST_TIMEOUT)
    return data


def _resolve_plz_inputs(area: str) -> List[str]:
    area = (area or "").strip()
    if "," in area or area.isdigit():
        return [p.strip() for p in area.split(",") if p.strip()]
    pcs = get_postal_codes(area)
    return [e.get("postalCode") for e in pcs if e.get("postalCode")]
