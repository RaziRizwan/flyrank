"""
main.py -- ties every stage together: fetch -> extract -> normalize -> validate -> store -> report.
Run with:  python src/main.py
Add a fake URL to prove Stage 5's failure handling: python src/main.py --inject-broken-url
"""
import sys
import time
import os
from datetime import datetime, timezone

from pydantic import ValidationError

from fetch import fetch
from extract import extract_book_links, extract_next_page, extract_raw_book
from normalize import normalize_record
from schema import CleanBook
from store import write_books, write_errors, write_report

# Overridable only for local testing against a mock server (see tests/); in real use this
# is always the live site.
BASE_URL = os.environ.get("SCRAPER_BASE_URL", "https://books.toscrape.com/catalogue/page-1.html")
MAX_CATALOGUE_PAGES = 3


def discover_book_urls() -> tuple[list[str], dict]:
    """Stage 2: walk the catalogue's own 'next' links for up to 3 pages, collect every
    book link (deduplicated), and report how the pages themselves fared."""
    all_links: list[str] = []
    page_url = BASE_URL
    pages_fetched = 0
    cache_hits = 0

    for _ in range(MAX_CATALOGUE_PAGES):
        if page_url is None:
            break
        result = fetch(page_url)
        pages_fetched += 1
        if result.from_cache:
            cache_hits += 1
        if result.status_code != 200:
            print(f"  ! catalogue page failed ({result.status_code}): {page_url}")
            break

        links = extract_book_links(result.html, page_url)
        all_links.extend(links)
        page_url = extract_next_page(result.html, page_url)

    unique_links = list(dict.fromkeys(all_links))  # de-dupe, preserve order
    print(f"catalogue_pages={pages_fetched} discovered={len(all_links)} unique_urls={len(unique_links)}")
    return unique_links, {"pages_fetched": pages_fetched, "cache_hits": cache_hits}


def process_book(url: str, source_page: str) -> tuple[dict | None, dict | None, dict]:
    """Stage 3+4 for one book. Returns (clean_record_or_None, error_or_None, fetch_stats).
    Never raises -- a broken page must not take the whole run down."""
    stats = {"fetched": False, "from_cache": False, "failed": False}
    try:
        result = fetch(url)
    except Exception as e:
        return None, {"url": url, "reason": f"network error: {e}"}, {"failed": True}

    stats["from_cache"] = result.from_cache
    stats["fetched"] = True

    if result.status_code != 200:
        return None, {"url": url, "reason": f"fetch failed with status {result.status_code}"}, {**stats, "failed": True}

    try:
        raw = extract_raw_book(result.html, product_url=url, source_page=source_page)
        clean_dict = normalize_record(raw)
        clean = CleanBook(**clean_dict)
    except (ValidationError, ValueError, AttributeError) as e:
        return None, {"url": url, "reason": str(e)}, stats

    return clean.model_dump(mode="json"), None, stats


def run(inject_broken_url: bool = False) -> None:
    start = time.time()
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    book_urls, catalogue_stats = discover_book_urls()

    if inject_broken_url:
        from urllib.parse import urljoin
        fake_url = urljoin(BASE_URL, "this-book-does-not-exist_0/index.html")
        book_urls.append(fake_url)
        print(f"  (injected one deliberately broken URL to test failure handling: {fake_url})")

    books: list[dict] = []
    errors: list[dict] = []
    pages_fetched = catalogue_stats["pages_fetched"]
    cache_hits = catalogue_stats["cache_hits"]
    failed_pages = 0

    for i, url in enumerate(book_urls, start=1):
        source_page = BASE_URL  # simplification: fine-grained per-page provenance is set in extract_raw_book
        clean, error, stats = process_book(url, source_page)
        if stats.get("fetched"):
            pages_fetched += 1
        if stats.get("from_cache"):
            cache_hits += 1
        if stats.get("failed"):
            failed_pages += 1

        if clean is not None:
            books.append(clean)
        if error is not None:
            errors.append(error)
            print(f"  ! [{i}/{len(book_urls)}] skipped: {error['reason']}")

    write_books(books)
    write_errors(errors)

    duration_s = round(time.time() - start, 2)
    report = {
        "started_at": started_at,
        "duration_seconds": duration_s,
        "catalogue_pages_requested": MAX_CATALOGUE_PAGES,
        "book_urls_discovered": len(book_urls),
        "pages_fetched": pages_fetched,
        "cache_hits": cache_hits,
        "valid_records": len(books),
        "invalid_records": len(errors),
        "failed_pages": failed_pages,
    }
    write_report(report)

    print(f"\ndetail_pages={len(book_urls)}")
    print("Run report:", report)


if __name__ == "__main__":
    run(inject_broken_url="--inject-broken-url" in sys.argv)
