import re
from typing import Dict, Optional, List
from io import BytesIO
from bs4 import BeautifulSoup

try:
    from fontTools.ttLib import TTFont
except Exception:
    TTFont = None  # optional

from ..config import BASE, REQUEST_TIMEOUT, CACHE_DIR
from .http import get_text, temp_headers
from .utils import cache_path_for

_OBF_CACHE: Dict[str, Dict[int, str]] = {}

_ENTITY_HEX_RX = re.compile(r"&#x([0-9A-Fa-f]{4,6});")


def _fetch_obfuscation_css(
    obf_id: str, css_tpl_url: str, use_cache: bool = True
) -> Optional[str]:
    url = (css_tpl_url or "").replace("%ID%", obf_id)
    if not url:
        return None
    cache_file = cache_path_for("obfcss", f"{obf_id}.css", CACHE_DIR) + ".css"
    if use_cache:
        try:
            import os

            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception:
            pass
    with temp_headers(accept="text/css,*/*;q=0.1", referer=BASE):
        css = get_text(
            url if url.startswith("http") else ("https:" + url),
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    if css and use_cache:
        try:
            import os

            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(css)
        except Exception:
            pass
    return css


def _build_obfuscation_map_from_css(css: str) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    for m in re.finditer(
        r"\.c([0-9A-Fa-f]{4,6})::?before\s*{[^}]*content\s*:\s*['\"](.*?)['\"]", css
    ):
        try:
            cp = int(m.group(1), 16)
            ch = m.group(2)[:1]
            mapping[cp] = ch
        except Exception:
            continue
    for m in re.finditer(
        r'data-c=["\']([0-9A-Fa-f]{4,6})["\'][^{]+content\s*:\s*["\'](.*?)["\']', css
    ):
        try:
            cp = int(m.group(1), 16)
            ch = m.group(2)[:1]
            mapping[cp] = ch
        except Exception:
            continue
    return mapping


def _fetch_obfuscation_font(obf_id: str, use_cache: bool = True) -> Optional[bytes]:
    url = f"https://www.fussball.de/export.fontface/-/format/woff/id/{obf_id}/type/font"
    cache_file = cache_path_for("obfcss", f"{obf_id}.woff", CACHE_DIR) + ".woff"
    if use_cache:
        try:
            import os

            if os.path.exists(cache_file):
                with open(cache_file, "rb") as f:
                    return f.read()
        except Exception:
            pass
    with temp_headers(accept="font/woff,*/*;q=0.1", referer=BASE):
        import requests

        r = requests.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and r.content:
            data = r.content
            if use_cache:
                try:
                    import os

                    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                    with open(cache_file, "wb") as f:
                        f.write(data)
                except Exception:
                    pass
            return data
    return None


def _build_obfuscation_map_from_font(woff_bytes: bytes) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    if not TTFont:
        return mapping
    try:
        font = TTFont(BytesIO(woff_bytes))
        cmap = font.getBestCmap() or {}
        for cp, glyph_name in cmap.items():
            if (
                isinstance(glyph_name, str)
                and glyph_name.startswith("uni")
                and len(glyph_name) == 7
            ):
                try:
                    real_cp = int(glyph_name[3:], 16)
                    mapping[cp] = chr(real_cp)
                    continue
                except Exception:
                    pass
            if isinstance(glyph_name, str) and len(glyph_name) == 1:
                mapping[cp] = glyph_name
            else:
                mapping[cp] = chr(cp)
    except Exception:
        pass
    return mapping


def _collect_obfuscation_maps_for_page(
    soup: BeautifulSoup, use_cache: bool = True
) -> Dict[str, Dict[int, str]]:
    maps: Dict[str, Dict[int, str]] = {}
    body = soup.find("body")
    css_tpl = body.get("data-obfuscation-stylesheet") if body else None

    ids = {
        el.get("data-obfuscation")
        for el in soup.find_all(attrs={"data-obfuscation": True})
        if el.get("data-obfuscation")
    }

    for obf_id in sorted(ids or []):
        if obf_id in _OBF_CACHE:
            maps[obf_id] = _OBF_CACHE[obf_id]
            continue

        obf_map: Dict[int, str] = {}
        if css_tpl:
            css = _fetch_obfuscation_css(obf_id, css_tpl, use_cache=use_cache)
            if css:
                obf_map = _build_obfuscation_map_from_css(css)

        if not obf_map:
            woff_bytes = _fetch_obfuscation_font(obf_id, use_cache=use_cache)
            if woff_bytes:
                obf_map = _build_obfuscation_map_from_font(woff_bytes)

        _OBF_CACHE[obf_id] = obf_map
        maps[obf_id] = obf_map

    return maps


def _decode_obfuscated_text(raw_html_or_text: str, obf_map: Dict[int, str]) -> str:
    if not raw_html_or_text:
        return ""

    def _ent_repl(m):
        cp = int(m.group(1), 16)
        return obf_map.get(cp, "?")

    s = _ENTITY_HEX_RX.sub(_ent_repl, raw_html_or_text)

    def _map_chars(txt: str) -> str:
        if not any(0xE000 <= ord(c) <= 0xF8FF for c in txt):
            return txt
        return "".join(obf_map.get(ord(c), c) for c in txt)

    s = _map_chars(s)
    s = BeautifulSoup(s, "html.parser").get_text(" ", strip=True)

    return re.sub(r"\s+", " ", s).strip()


def _find_ancestor_obf_id(node) -> Optional[str]:
    cur = getattr(node, "parent", None)
    while cur is not None and getattr(cur, "name", "").lower() not in ("html", "body"):
        if hasattr(cur, "get") and cur.get("data-obfuscation"):
            return cur.get("data-obfuscation")
        cur = getattr(cur, "parent", None)
    return None


def decode_all_obf_in(el, page_maps: Dict[str, Dict[int, str]]) -> str:
    pieces: List[str] = []
    for txt in el.strings:
        obf_id = _find_ancestor_obf_id(txt)
        if obf_id and (page_maps.get(obf_id) or {}):
            pieces.append(_decode_obfuscated_text(str(txt), page_maps[obf_id]))
        else:
            pieces.append(str(txt))
    out = "".join(pieces)
   

    return re.sub(r"\s+", " ", out).strip()


__all__ = [
    "_collect_obfuscation_maps_for_page",
    "decode_all_obf_in",
]
