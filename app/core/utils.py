import os
import re
from urllib.parse import urljoin
from ..config import BASE, CACHE_DIR


def cache_path_for(category: str, key: str, base_dir: str = CACHE_DIR) -> str:
    safe = re.sub(r"[^\w\.-]+", "_", key).strip("_")
    d = os.path.join(base_dir, category)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, safe)


def abs_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return urljoin(BASE + "/", u.lstrip("/"))


# Regex helpers
game_id_IN_URL = re.compile(r"/-/spiel/([A-Za-z0-9]+)")
game_id_REGEX = re.compile(r"/-/spiel/([A-Za-z0-9]+)")
STAFFEL_LINK_IN_HTML = re.compile(r"/-/staffel/([A-Za-z0-9\-]+)")
STAFFEL_ID_REGEX = re.compile(r"/-/staffel/([A-Za-z0-9\-]+)")


def _text_or_none(el):
    if not el:
        return None
    t = el.get_text(" ", strip=True)
    return t or None
