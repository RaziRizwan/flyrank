"""
Parser tests -- run entirely offline against the fixtures in tests/fixtures/, no network
needed. Run with:  pytest tests/ -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from extract import extract_book_links, extract_next_page, extract_raw_book
from normalize import normalize_price, normalize_availability, normalize_rating, normalize_record
from schema import CleanBook
from pydantic import ValidationError

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- 1. price normalization ---------------------------------------------------------
def test_price_normalization():
    assert normalize_price("£51.77") == 51.77
    assert normalize_price("£1,234.50") == 1234.50  # comma thousands separator


# --- 2. relative -> absolute URLs ----------------------------------------------------
def test_relative_to_absolute_urls():
    html = read_fixture("catalogue-page-1.html")
    page_url = "https://books.toscrape.com/catalogue/page-1.html"
    links = extract_book_links(html, page_url)
    assert len(links) == 2
    for link in links:
        assert link.startswith("https://books.toscrape.com/catalogue/")
        assert ".." not in link  # relative segments were resolved, not glued


# --- 3. missing description --------------------------------------------------------
def test_missing_description_is_null_not_invented():
    html = read_fixture("detail-no-description.html")
    raw = extract_raw_book(html, product_url="https://example.com/x", source_page="https://example.com")
    assert raw["description"] is None
    # and a record with a null description must still validate -- description is optional
    clean_dict = normalize_record(raw)
    clean = CleanBook(**clean_dict)
    assert clean.description is None


# --- 4. duplicate URLs get removed --------------------------------------------------
def test_duplicate_urls_are_removed():
    page1 = extract_book_links(read_fixture("catalogue-page-1.html"), "https://books.toscrape.com/catalogue/page-1.html")
    page3 = extract_book_links(read_fixture("catalogue-page-3.html"), "https://books.toscrape.com/catalogue/page-3.html")
    combined = page1 + page3  # page 3's fixture deliberately repeats page 1's first book
    unique = list(dict.fromkeys(combined))
    assert len(combined) == 3
    assert len(unique) == 2


# --- 5. one malformed fixture --------------------------------------------------------
def test_malformed_price_fails_validation_not_the_program():
    raw = {
        "title": "Broken Record",
        "product_url": "https://books.toscrape.com/catalogue/broken_1/index.html",
        "price_text": "contact us for pricing",  # no number in it at all
        "availability_text": "In stock",
        "rating_text": "Three",
        "description": None,
        "source_page": "https://books.toscrape.com/catalogue/page-1.html",
        "fetched_at": "2026-09-04T00:00:00Z",
    }
    with pytest.raises(ValueError):
        normalize_record(raw)  # must raise cleanly -- never crash the whole run


# --- a few extra checks worth having, since they're nearly free ----------------------
def test_availability_normalization():
    assert normalize_availability("In stock (22 available)") is True
    assert normalize_availability("Out of stock") is False


def test_rating_word_to_number():
    assert normalize_rating("Three") == 3
    with pytest.raises(ValueError):
        normalize_rating("Bazillion")


def test_pagination_stops_when_no_next_link():
    html = read_fixture("catalogue-page-3.html")
    next_page = extract_next_page(html, "https://books.toscrape.com/catalogue/page-3.html")
    assert next_page is None


def test_pagination_follows_next_link():
    html = read_fixture("catalogue-page-1.html")
    next_page = extract_next_page(html, "https://books.toscrape.com/catalogue/page-1.html")
    assert next_page == "https://books.toscrape.com/catalogue/page-2.html"


def test_extreme_whitespace_is_collapsed():
    html = read_fixture("detail-with-description.html")
    raw = extract_raw_book(html, product_url="https://example.com/x", source_page="https://example.com")
    assert "  " not in raw["description"]  # no doubled-up whitespace survives
