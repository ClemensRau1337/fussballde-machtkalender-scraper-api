from contextlib import contextmanager
from typing import Optional, Any
import requests
from ..config import USER_AGENT, REQUEST_TIMEOUT

SESSION = requests.Session()
SESSION.headers.update(
    {
        "accept": "application/json, text/plain, */*",
        "user-agent": USER_AGENT,
        "x-requested-with": "XMLHttpRequest",
    }
)


@contextmanager
def temp_headers(**headers: str):
    backup = dict(SESSION.headers)
    try:
        # Remove keys with None to allow deletion
        for k, v in headers.items():
            if v is None and k in SESSION.headers:
                del SESSION.headers[k]
        # Add/override the rest
        for k, v in headers.items():
            if v is not None:
                SESSION.headers[k] = v
        yield
    finally:
        SESSION.headers.clear()
        SESSION.headers.update(backup)


def get_json(url: str, *, timeout: float = REQUEST_TIMEOUT) -> Any:
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def get_text(
    url: str, *, timeout: float = REQUEST_TIMEOUT, allow_redirects: bool = True
) -> Optional[str]:
    r = SESSION.get(url, timeout=timeout, allow_redirects=allow_redirects)
    if r.status_code == 200 and (r.text or "").strip():
        return r.text
    return None
