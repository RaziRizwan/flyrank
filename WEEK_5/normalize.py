"""
normalize.py -- Stage 4. Raw strings are ingredients; this turns them into the clean,
typed values the schema requires.
"""
import re

from extract import RATING_WORDS


def normalize_price(price_text: str) -> float:
    """'£51.77' -> 51.77. Strips any non-numeric currency symbol, keeps the digits."""
    match = re.search(r"[\d]+\.?\d*", price_text.replace(",", ""))
    if not match:
        raise ValueError(f"could not find a number in price text: {price_text!r}")
    return float(match.group())


def normalize_availability(availability_text: str) -> bool:
    """'In stock (22 available)' -> True. Anything not containing 'in stock' -> False."""
    return "in stock" in availability_text.lower()


def normalize_rating(rating_text: str) -> int:
    """'Three' -> 3. Raises if the word isn't one of the five known rating words --
    that's exactly the kind of record that should fail validation, not be guessed at."""
    if rating_text not in RATING_WORDS:
        raise ValueError(f"unrecognized rating word: {rating_text!r}")
    return RATING_WORDS[rating_text]


def normalize_record(raw: dict) -> dict:
    """Raw dict (schema.RawBook shape) -> clean dict (schema.CleanBook shape).
    Raises ValueError if any piece can't be normalized -- the caller is responsible for
    catching that and routing the record to errors.json instead of books.json."""
    return {
        "title": raw["title"],
        "product_url": raw["product_url"],
        "price_gbp": normalize_price(raw["price_text"]),
        "price_text": raw["price_text"],
        "in_stock": normalize_availability(raw["availability_text"]),
        "availability_text": raw["availability_text"],
        "rating": normalize_rating(raw["rating_text"]),
        "description": raw["description"],
        "source_page": raw["source_page"],
        "fetched_at": raw["fetched_at"],
    }
