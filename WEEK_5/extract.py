"""
extract.py -- Stage 2 & 3. Turns saved HTML into raw fields. Selectors are aimed at the
product area specifically (article.product_pod, div.product_main), never "the first thing
that looks like a price" on the whole document.
"""
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def extract_book_links(catalogue_html: str, page_url: str) -> list[str]:
    """Every book link on a catalogue page, as absolute URLs. Never string-glued."""
    soup = BeautifulSoup(catalogue_html, "html.parser")
    links = []
    for article in soup.select("article.product_pod"):
        a = article.select_one("h3 a")
        if a and a.get("href"):
            links.append(urljoin(page_url, a["href"]))
    return links


def extract_next_page(catalogue_html: str, page_url: str) -> str | None:
    """The catalogue's own 'next' link, or None if this is the last page."""
    soup = BeautifulSoup(catalogue_html, "html.parser")
    next_link = soup.select_one("li.next a")
    if next_link and next_link.get("href"):
        return urljoin(page_url, next_link["href"])
    return None


def extract_raw_book(detail_html: str, product_url: str, source_page: str) -> dict:
    """The eight raw fields for one book detail page. Selectors target div.product_main
    and the description block specifically -- not the whole document."""
    soup = BeautifulSoup(detail_html, "html.parser")
    main = soup.select_one("div.product_main")

    title = main.select_one("h1").get_text(strip=True) if main else ""
    price_text = main.select_one("p.price_color").get_text(strip=True) if main else ""
    availability_text = " ".join(
        main.select_one("p.availability").get_text().split()
    ) if main and main.select_one("p.availability") else ""
    rating_tag = main.select_one("p.star-rating") if main else None
    rating_text = next(
        (c for c in (rating_tag.get("class") or []) if c in RATING_WORDS), ""
    ) if rating_tag else ""

    # Description: the paragraph right after the #product_description heading.
    # Some books genuinely have none -- store null, never invent text.
    desc_heading = soup.select_one("#product_description")
    description = None
    if desc_heading:
        desc_p = desc_heading.find_next_sibling("p")
        if desc_p:
            description = " ".join(desc_p.get_text().split())

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
