"""
fetch.py -- Stage 1 & 5. Every network request in this whole project goes through here,
so politeness (user-agent, timeout, delay) and the cache-first rule only have to be right
in one place.
"""
import hashlib
import time
from pathlib import Path

import requests

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/razirizwan/flyrank)"
TIMEOUT_SECONDS = 10
DELAY_SECONDS = 0.5
CACHE_DIR = Path("cache")


class FetchResult:
    def __init__(self, html: str, status_code: int, from_cache: bool, url: str):
        self.html = html
        self.status_code = status_code
        self.from_cache = from_cache
        self.url = url

    def __repr__(self):
        source = "CACHE HIT" if self.from_cache else "FETCH"
        return f"<FetchResult {source} {self.status_code} {len(self.html)} bytes {self.url}>"


def _cache_path(url: str) -> Path:
    # A short, filesystem-safe name derived from the URL -- collisions are astronomically
    # unlikely for 60-ish pages, and this keeps cache/ readable rather than one giant hash soup.
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    safe_tail = "".join(c if c.isalnum() else "-" for c in url.rstrip("/").rsplit("/", 1)[-1])[-40:]
    return CACHE_DIR / f"{safe_tail}-{digest}.html"


def fetch(url: str, *, use_cache: bool = True, max_retries: int = 1) -> FetchResult:
    """Politely GET a page, caching it to disk. Reads from cache on a hit -- the site
    is asked at most once per URL during development. Retries once on a timeout or 5xx;
    never retries a 404 or 403 (see stage_5_report.py for how the caller handles those)."""
    CACHE_DIR.mkdir(exist_ok=True)
    path = _cache_path(url)

    if use_cache and path.exists():
        html = path.read_text(encoding="utf-8")
        return FetchResult(html=html, status_code=200, from_cache=True, url=url)

    headers = {"User-Agent": USER_AGENT}
    attempt = 0
    last_exception = None
    while attempt <= max_retries:
        attempt += 1
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as e:
            last_exception = e
            if attempt <= max_retries:
                time.sleep(1)
                continue
            raise

        if response.status_code == 200:
            # Force UTF-8 rather than trusting requests' encoding guess, which falls back
            # to ISO-8859-1 when a server doesn't declare a charset -- that silently
            # mangles non-ASCII characters like the £ sign.
            html_text = response.content.decode("utf-8", errors="replace")
            path.write_text(html_text, encoding="utf-8")
            time.sleep(DELAY_SECONDS)  # only real requests wait -- cache hits never do
            return FetchResult(html=html_text, status_code=200, from_cache=False, url=url)

        if response.status_code >= 500 and attempt <= max_retries:
            time.sleep(1)
            continue

        # 404, 403, or any other non-200 after retries are exhausted: hand it back as-is,
        # the caller decides what to do (log + skip, never crash the whole run).
        time.sleep(DELAY_SECONDS)
        return FetchResult(html="", status_code=response.status_code, from_cache=False, url=url)

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Fetch failed without an HTTP response or exception")
