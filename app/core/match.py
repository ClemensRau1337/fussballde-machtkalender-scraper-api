import json
import re
from typing import Dict, Optional
import unicodedata
from bs4 import BeautifulSoup
from ..config import BASE, REQUEST_TIMEOUT, USE_CACHE_DEFAULT, CACHE_DIR
from .http import get_text, temp_headers, SESSION
from .utils import cache_path_for, abs_url, _text_or_none, game_id_IN_URL, STAFFEL_LINK_IN_HTML
from .obfuscation import _collect_obfuscation_maps_for_page, decode_all_obf_in
from datetime import datetime

_TIME_RX = re.compile(r"\b([0-2]\d:[0-5]\d)\b")
_DATE_RX = re.compile(r"\b([0-3]\d\.[01]\d\.\d{2,4})\b")
_ISO_RX  = re.compile(r"\b\d{4}-\d{2}-\d{2}T[0-2]\d:[0-5]\d(?::\d{2})?(?:Z|[+-][0-2]\d:[0-5]\d)?\b")
WEEKDAY_RX = re.compile(r"^\s*(?:Mo|Di|Mi|Do|Fr|Sa|So|Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)\s*,\s*", re.I)
ZWSP_RX = re.compile(r"[\u200b-\u200f\uFEFF]")

def _normalize_date_time_fields(d: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    raw_time = (d.get("time") or "")
    raw_time = unicodedata.normalize("NFKC", raw_time)
    raw_time = raw_time.replace("\u00A0", " ").replace("\u202F", " ")
    raw_time = ZWSP_RX.sub("", raw_time).strip()

    m_iso = _ISO_RX.search(raw_time)
    if m_iso:
        s = m_iso.group(0).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            d["time"] = dt.strftime("%H:%M")
            d.setdefault("date_label", dt.strftime("%d.%m.%Y"))
            d["datetime_iso"] = dt.isoformat()
        except Exception:
            pass

    m_time = _TIME_RX.search(raw_time)
    if m_time:
        d["time"] = m_time.group(1)

    if not d.get("date_label"):
        m_date = _DATE_RX.search(raw_time)
        if m_date:
            d["date_label"] = m_date.group(1)

    if d.get("date_label") and WEEKDAY_RX.search(d["date_label"]):
        dl = d["date_label"]
        d["date_label_long"] = dl
        only_date = _DATE_RX.search(dl)
        if only_date:
            d["date_label"] = only_date.group(1)

    return d

ED_VARS = {
    "home":            r"edHeimmannschaftName='([^']+)'",
    "away":            r"edGastmannschaftName='([^']+)'",
    "age_group":       r"edMannschaftsartName='([^']+)'",
    "league":          r"edSpielklasseName='([^']+)'",
    "wettbewerb_name": r"edWettbewerbName='([^']+)'",
    "wettbewerb_id":   r"edWettbewerbId='([^']+)'",
}

def _extract_ed_vars(html: str) -> dict:
    out = {}
    for k, rx in ED_VARS.items():
        m = re.search(rx, html)
        if m:
            out[k] = m.group(1).strip()
    return out

def _get_ok_html(url: str) -> Optional[str]:
    if not url:
        return None
    with temp_headers(accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                      **{"x-requested-with": None}, referer=BASE):
        return get_text(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)

def _extract_jsonld_event(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {}
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (tag.string or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        def walk(x):
            if isinstance(x, dict):
                yield x
                if "@graph" in x and isinstance(x["@graph"], list):
                    for n in x["@graph"]:
                        yield from walk(n)
                for v in x.values():
                    yield from walk(v)
            elif isinstance(x, list):
                for n in x:
                    yield from walk(n)

        for node in walk(data):
            t = node.get("@type") or node.get("type") or ""
            if isinstance(t, list):
                t = ",".join(t)
            if "SportsEvent" not in str(t):
                continue

            def _team_name(team):
                if isinstance(team, dict):
                    return team.get("name") or team.get("legalName")
                return None

            home = _team_name(node.get("homeTeam") or {})
            away = _team_name(node.get("awayTeam") or {})
            if home: out["home"] = home
            if away: out["away"] = away

            start = node.get("startDate")
            if start:
                out["time"] = start
                out["date_label"] = start

            comp = node.get("name")
            if comp:
                out["league"] = comp

            result = node.get("aggregateScore") or node.get("result") or {}
            if isinstance(result, dict):
                hg = result.get("homeTeamGoals") or result.get("homeScore")
                ag = result.get("awayTeamGoals") or result.get("awayScore")
                if hg is not None and ag is not None:
                    out["score"] = f"{hg}:{ag}"
            return out
    return out

def fetch_match_details(spiel_link: str, use_cache: bool = USE_CACHE_DEFAULT) -> Dict[str, Optional[str]]:
    url = abs_url(spiel_link or "")
    if not url:
        return {}
    m = game_id_IN_URL.search(url)
    sid_for_cache = (m.group(1) if m else re.sub(r"\W+", "_", url)) or "unknown"
    cache_file = cache_path_for("match", sid_for_cache) + ".html"

    html = None
    if use_cache:
        try:
            import os
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    html = f.read()
        except Exception:
            html = None

    if not html:
        html = _get_ok_html(url)
        if use_cache and html:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass

    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    staffel_id = None
    a_staffel = soup.find("a", href=STAFFEL_LINK_IN_HTML)
    if a_staffel and a_staffel.get("href"):
        mm = STAFFEL_LINK_IN_HTML.search(a_staffel["href"])
        if mm:
            staffel_id = mm.group(1)

    def _find_dt_dd(label_regex: str) -> Optional[str]:
        for dt in soup.find_all(["dt", "th"]):
            if re.search(label_regex, dt.get_text(" ", strip=True), flags=re.I):
                dd = dt.find_next_sibling(["dd", "td"])
                if dd:
                    return dd.get_text(" ", strip=True)
        return None

    spielnummer = _find_dt_dd(r"^Spiel(?:\-|\s*)?nummer")
    staffelnummer = _find_dt_dd(r"^Staffel(?:\-|\s*)?nummer")

    if not spielnummer:
        m = re.search(r"Spiel(?:\-|\s*)?nummer\s*[:\-]?\s*([A-Z0-9\-]+)", text, flags=re.I)
        if m:
            spielnummer = m.group(1).strip()

    if not staffelnummer:
        m = re.search(r"Staffel(?:\-|\s*)?nummer\s*[:\-]?\s*([A-Z0-9\-]+)", text, flags=re.I)
        if m:
            staffelnummer = m.group(1).strip()

    return {"spielnummer": spielnummer, "staffelnummer": staffelnummer, "staffel_id": staffel_id}

def fetch_match_full(match_link: str, use_cache: bool = USE_CACHE_DEFAULT) -> Dict[str, Optional[str]]:
    url = abs_url(match_link or "")
    if not url:
        return {}

    m = game_id_IN_URL.search(url)
    sid_for_cache = (m.group(1) if m else re.sub(r"\W+", "_", url)) or "unknown"
    cache_file = cache_path_for("match_full", f"full_{sid_for_cache}", CACHE_DIR) + ".html"

    html = None
    if use_cache:
        try:
            import os
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    html = f.read()
        except Exception:
            pass
    if not html:
        html = _get_ok_html(url)
        if use_cache and html:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    page_maps = _collect_obfuscation_maps_for_page(soup, use_cache=use_cache)

    canonical = None
    link_tag = soup.find("link", rel=lambda x: x and x.lower() == "canonical")
    if link_tag and link_tag.get("href"):
        canonical = link_tag["href"]
    og = soup.find("meta", attrs={"property": "og:url"})
    if not canonical and og and og.get("content"):
        canonical = og["content"]
    m = game_id_IN_URL.search(canonical or url)
    game_id = m.group(1) if m else None

    ed = _extract_ed_vars(html)

    age_group = ed.get("age_group")

    home = _text_or_none(soup.select_one(".stage .team-home .team-name a")) or ed.get("home")
    away = _text_or_none(soup.select_one(".stage .team-away .team-name a")) or ed.get("away")

    staffel_id = None
    comp_a = soup.select_one(".stage .stage-header a.competition[href*='/-/staffel/']")
    if comp_a and comp_a.has_attr("href"):
        mm = re.search(r"/-/staffel/([A-Z0-9\-]+)", comp_a["href"])
        if mm:
            staffel_id = mm.group(1)
    if not staffel_id:
        staffel_id = ed.get("wettbewerb_id")

    age_group = ed.get("age_group")
    league = ed.get("league")
    competition = ed.get("wettbewerb_name")

    venue = _text_or_none(soup.select_one(".stage .stage-header a.location"))

    title = soup.find("title")
    date_label = None
    if title and title.get_text(strip=True):
        md = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", title.get_text(strip=True))
        if md:
            date_label = md.group(1)

    time_val = None
    date_wrapper = soup.select_one(".stage .stage-header .date-wrapper .date")
    if date_wrapper:
        decoded_dt = decode_all_obf_in(date_wrapper, page_maps)
        mt = re.search(r"\b([0-2]\d:[0-5]\d)\b", decoded_dt)
        if mt:
            time_val = mt.group(1)
        md = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", decoded_dt)
        if md and not date_label:
            date_label = md.group(1)

    if not time_val:
        subj = soup.select_one('.contact-form-wrapper input[name="subject"]')
        sv = subj.get("value") if subj and subj.has_attr("value") else None
        if sv:
            mt = re.search(r"\b([0-2]\d:[0-5]\d)\b", sv)
            if mt:
                time_val = mt.group(1)
            md = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", sv)
            if md and not date_label:
                date_label = md.group(1)

    score = None
    end_result = soup.select_one(".stage .result .end-result")
    if end_result:
        decoded_score = decode_all_obf_in(end_result, page_maps)
        ms = re.search(r"\b(\d+)\s*:\s*(\d+)\b", decoded_score)
        if ms:
            score = f"{ms.group(1)}:{ms.group(2)}"

    sr = sra1 = sra2 = None
    for li in soup.select(".stage-meta-left li.row"):
        label = (li.find("span") or li).get_text(" ", strip=True).lower()
        if "schiedsrichter" in label:
            sr = decode_all_obf_in(li, page_maps)
            sr = re.sub(r"(?i)^schiedsrichter\s*:\s*", "", sr).strip() or None
        elif "assistenten" in label:
            texts = []
            for sp in li.find_all("span")[1:]:
                decoded = decode_all_obf_in(sp, page_maps).strip()
                if decoded:
                    parts = [p.strip() for p in decoded.split(",") if p.strip()]
                    texts.extend(parts)
            if texts:
                sra1 = texts[0] if len(texts) > 0 else None
                sra2 = texts[1] if len(texts) > 1 else None

    stage_meta_right = _text_or_none(soup.select_one(".stage .stage-meta-right")) or ""
    spielnummer = None
    staffelnummer = None
    ms = re.search(r"Spiel:\s*([0-9]{6,})\s*/", stage_meta_right)
    if ms:
        spielnummer = ms.group(1)
    mst = re.search(r"Staffel-ID:\s*([0-9]+)", stage_meta_right)
    if mst:
        staffelnummer = mst.group(1)

    out = {
        "game_id": game_id,
        "link": canonical or url,
        "date_label": date_label,
        "time": time_val,
        "age_group": age_group,
        "league": league,
        "competition": competition,
        "league_label": competition or league,
        "home": home,
        "away": away,
        "venue": venue,
        "score": score,
        "spielnummer": spielnummer,
        "staffelnummer": staffelnummer,
        "staffel_id": staffel_id,
        "referee": sr,
        "assistant_1": sra1,
        "assistant_2": sra2,
    }
    return _normalize_date_time_fields(out)
