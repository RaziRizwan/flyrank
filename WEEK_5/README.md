# The polite scraper — Books to Scrape

FlyRank Internship · Backend Track · W5 · A9. A small, polite scraping pipeline: downloads
the first 3 catalogue pages of [Books to Scrape](https://books.toscrape.com/), visits all
60 book pages, turns messy HTML into clean, checked JSON, survives a broken page, and ends
every run with an honest report.

## Target classification (Stage 0)

- **Site:** [books.toscrape.com](https://books.toscrape.com/) — its own homepage states
  it is *"a fictional bookstore that desperately wants to be scraped... a safe place for
  beginners learning web scraping."* It exists for exactly this purpose.
- **Scope:** the first 3 catalogue pages only (`page-1.html` → `page-3.html`, following the
  site's own "next" link), and the ~60 book detail pages those 3 pages link to. No other
  pages, no other site.
- **robots.txt:** `GET https://books.toscrape.com/robots.txt` → **404**. No robots file
  found. A missing file is not permission — it's just a missing file — so scope is kept
  deliberately narrow (3 pages, not all 1000 books) and every request stays polite
  regardless.
- **Data collected:** book title, price, stock status, star rating, description, and each
  record's source page and fetch time. No account data, no personal data — this site has
  none.
- **Why this is appropriate here:** the site explicitly invites scraping, the data is
  public product-listing content already sent to any visitor's browser, and the scrape is
  small, slow, and clearly identified (see Politeness below).

**I will not reuse this code on another site without checking its rules and terms first.**

## Setup & run

```bash
pip install -r requirements.txt
python src/main.py
```

Cached pages live in `cache/` (git-ignored) — delete it for a truly fresh run. Add
`--inject-broken-url` to see the Stage 5 failure-handling checkpoint for yourself:

```bash
python src/main.py --inject-broken-url
```

Run the parser test suite (offline, no network — uses `tests/fixtures/`):
```bash
pytest tests/ -v
```

## Politeness rules this scraper follows

| Rule | Value |
|---|---|
| User-agent | `FlyRankInternshipA9/1.0 (+link-to-your-repo)` — identifies the bot and gives a contact link |
| Timeout | 10 seconds — a request never waits forever |
| Delay | 0.5 seconds between real requests — cache hits wait 0 seconds |
| Retries | once, only on a timeout or 5xx; a 404 or 403 is never retried |
| Cache | every page saved to `cache/` on first fetch; re-runs during development read the cache, never the network |

## Record schema

```jsonc
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_gbp": 51.77,
  "price_text": "£51.77",
  "in_stock": true,
  "availability_text": "In stock (22 available)",
  "rating": 3,
  "description": "...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-09-04T10:00:00Z"
}
```
`product_url` is each record's canonical identity. A record missing a required field, or
with a price/rating that can't be parsed, fails validation and lands in `errors.json`
with a reason — it never reaches `books.json`.

## Sample run-report.json

The report below is from a **local integration test** (a mock HTTP server standing in for
the real site, used to prove the fetch → extract → normalize → validate → store → report
pipeline end-to-end without hitting the live site during development). Run
`python src/main.py` yourself for the real 60-record report and paste that here before you
publish — the shape will be identical, just with real numbers:

```json
{
  "started_at": "2026-09-04T03:58:03Z",
  "duration_seconds": 3.54,
  "catalogue_pages_requested": 3,
  "book_urls_discovered": 4,
  "pages_fetched": 7,
  "cache_hits": 0,
  "valid_records": 3,
  "invalid_records": 1,
  "failed_pages": 1
}
```
(Small numbers because the mock server served 3 fixture books + 1 deliberately broken
URL, not the real site's 60 — see `OTHER_SETUP_REQUIRED.md` for why, and the one command
that gets you the real numbers.)

## Why this assignment needed no browser

The data is already present in the HTML the server sends on the very first response — a
plain `requests.get()` and BeautifulSoup can read title, price, availability, rating, and
description directly, with nothing rendered client-side afterward. A browser (Playwright,
Selenium) would only add startup cost and memory for zero additional data.

## Ethics note

Use an official API when one exists instead of scraping. Never bypass a login, a paywall,
or an explicit block — a site saying no is the end of the conversation, not a puzzle to
solve. Collect only the fields actually needed, not everything reachable. This project
touches exactly one site, built and maintained for the purpose of being scraped by people
learning to do this respectfully.

## One honest limitation

This scraper's retry logic is intentionally simple: one retry, no backoff delay curve, no
`Retry-After` header handling. That's deliberate — the brief explicitly says not to
gold-plate Stage 5. Real production scraping (next week's A16) adds exponential backoff,
`Retry-After` handling, and structured logs; this version is the simple, working
foundation that one builds on top of, not a finished production scraper.

## AI vs me

(Fill this in after you complete the bonus stage yourself — write your own prompt from
memory, run it, and compare against this code.)
