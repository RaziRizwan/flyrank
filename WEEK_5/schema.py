"""
schema.py -- the recipe. Every field a record must have, and its type, lives here and
only here. Both the raw extractor and the normalizer import from this file so there is
exactly one definition of what a "book record" is.
"""
from typing import Optional
from pydantic import BaseModel, HttpUrl, field_validator


class RawBook(BaseModel):
    """Exactly what Stage 3 (extract) collects -- untouched strings, straight off the page."""
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str


class CleanBook(BaseModel):
    """What Stage 4 (validate) requires before a record is allowed into books.json."""
    title: str
    product_url: HttpUrl          # canonical identity -- must be a real absolute URL
    price_gbp: float
    price_text: str               # the original text, kept side by side with the clean value
    in_stock: bool
    availability_text: str
    rating: int                   # 1-5, converted from the word ("Three" -> 3)
    description: Optional[str] = None
    source_page: str
    fetched_at: str

    @field_validator("price_gbp")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price_gbp must not be negative")
        return v

    @field_validator("rating")
    @classmethod
    def rating_must_be_in_range(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("rating must be between 1 and 5")
        return v
