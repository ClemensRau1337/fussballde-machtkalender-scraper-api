import re
import time
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from ..config import BASE, REQUEST_TIMEOUT, SLEEP_SEC, USE_CACHE_DEFAULT
from .http import get_text, temp_headers
from .utils import cache_path_for, game_id_REGEX, STAFFEL_ID_REGEX
from .postal import _resolve_plz_inputs
from .match import _normalize_date_time_fields


def fetch_calendar_page(
    plz: str,
    date_from: str,
    date_to: str,
    offset: int,
    max_results: int,
    use_cache: bool = USE_CACHE_DEFAULT,
) -> Dict:
    url = (
        f"{BASE}/ajax.match.calendar.loadmore/-/datum-bis/{date_to}"
        f"/datum-von/{date_from}/mime-type/JSON/plz/{plz}"
        f"/max/{max_results}/offset/{offset}"
    )
    cache_file = (
        cache_path_for(
            "calendar", f"{plz}_{date_from}_{date_to}_{offset}_{max_results}.json"
        )
        + ".json"
    )

    if use_cache:
        try:
            import json
            import os

            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

    referer = (
        f"{BASE}/matchkalender/-/plz/{plz}/datum-von/{date_from}"
        f"/datum-bis/{date_to}/wettkampftyp/-1/mannschaftsart/-1"
    )

    with temp_headers(accept="application/json, text/plain, */*", referer=referer):
        text = get_text(url, timeout=REQUEST_TIMEOUT)
    if not text:
        return {"html": "", "final": True, "lastIndex": offset}

    import json

    data = json.loads(text)
    if use_cache:
        try:
            import os

            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass
    return data


def _extract_link_and_ids(row) -> Dict[str, Optional[str]]:
    game_id = None
    staffel_id = None
    href = ""
    for a in row.find_all("a", href=True):
        h = a["href"]
        m = game_id_REGEX.search(h)
        if m:
            game_id = m.group(1)
            href = h
            break
    if not game_id:
        for a in row.find_all("a", href=True):
            h = a["href"]
            g = STAFFEL_ID_REGEX.search(h)
            if g:
                staffel_id = g.group(1)
                href = h
                break
    return {"href": href, "game_id": game_id, "staffel_id": staffel_id}


def parse_matches(html: str) -> List[Dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    matches: List[Dict] = []
    current_date_text: Optional[str] = None

    for row in soup.find_all("tr"):
        classes = row.get("class") or []
        if "row-headline" in classes:
            current_date_text = row.get_text(" ", strip=True)
            continue

        tds = row.find_all("td")
        if not tds:
            continue

        time_txt = tds[0].get_text(" ", strip=True) if len(tds) > 0 else ""
        age_group = tds[1].get_text(" ", strip=True) if len(tds) > 1 else ""
        league = tds[2].get_text(" ", strip=True) if len(tds) > 2 else ""

        clubs = row.find_all("td", class_="column-club")
        home_team = clubs[0].get_text(" ", strip=True) if len(clubs) > 0 else ""
        away_team = clubs[1].get_text(" ", strip=True) if len(clubs) > 1 else ""

        score_cell = row.find("td", class_="column-score")
        score_txt = score_cell.get_text(" ", strip=True) if score_cell else ""
        m_score = re.search(r"(\d+)\s*:\s*(\d+)", score_txt)
        score_clean = f"{m_score.group(1)}:{m_score.group(2)}" if m_score else None

        linkbits = _extract_link_and_ids(row)
        href = linkbits["href"]
        game_id = linkbits["game_id"]

        detail = {
            "date_label": current_date_text,
            "time": time_txt,
            "age_group": age_group,
            "league": league,
            "home": home_team,
            "away": away_team,
            "score": score_clean,
            "game_id": game_id,
            "link": href,
        }
        detail = _normalize_date_time_fields(detail)

        if home_team or away_team or game_id:
            matches.append(detail)

    return matches


def iter_matches_for_plz(
    plz: str,
    date_from: str,
    date_to: str,
    page_size: int = 50,
    sleep_sec: float = SLEEP_SEC,
    use_cache: bool = USE_CACHE_DEFAULT,
):
    offset = 0
    last_seen_lastindex = -1
    while True:
        data = fetch_calendar_page(
            plz, date_from, date_to, offset, page_size, use_cache=use_cache
        )
        html = data.get("html") or ""
        if not html.strip():
            break

        matches = parse_matches(html)
        for m in matches:
            yield m

        final = data.get("final")
        last_index = data.get("lastIndex", 0)
        if final or last_index == last_seen_lastindex:
            break
        last_seen_lastindex = last_index
        offset = last_index + 1
        time.sleep(sleep_sec)


def collect_matches_for_area(
    date_from: str, date_to: str, plz_query: str, use_cache: bool = USE_CACHE_DEFAULT
) -> List[Dict]:
    plzs = _resolve_plz_inputs(plz_query)
    all_matches: List[Dict] = []
    for plz in plzs:
        for m in iter_matches_for_plz(
            plz, date_from, date_to, page_size=50, use_cache=use_cache
        ):
            all_matches.append(m)
    return all_matches
