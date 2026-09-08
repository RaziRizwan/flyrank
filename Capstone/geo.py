"""
services/geo.py -- IP -> country/city, trying provider A then provider B. Degrade, never
fail: if every provider is down, enrichment returns (None, None) and the caller stores the
submission anyway.

Providers are small, swappable objects specifically so a test can inject one that always
succeeds and one that always fails -- proving the fallback chain deterministically,
exactly as the brief asks for, without depending on two real external services being up
at test time.
"""
from dataclasses import dataclass
from typing import Optional, Protocol

import httpx


@dataclass
class GeoResult:
    country: Optional[str]
    city: Optional[str]


class GeoProviderError(Exception):
    pass


class GeoProvider(Protocol):
    name: str

    def lookup(self, ip: str) -> GeoResult:
        ...


class IpApiComProvider:
    """ip-api.com -- free, no key, 45 req/min."""
    name = "ip-api.com"

    def lookup(self, ip: str) -> GeoResult:
        try:
            r = httpx.get(f"http://ip-api.com/json/{ip}", timeout=3)
        except httpx.HTTPError as e:
            raise GeoProviderError(str(e))
        if r.status_code != 200:
            raise GeoProviderError(f"status {r.status_code}")
        data = r.json()
        if data.get("status") != "success":
            raise GeoProviderError(data.get("message", "lookup failed"))
        return GeoResult(country=data.get("country"), city=data.get("city"))


class IpApiCoProvider:
    """ipapi.co -- fallback, free tier ~1,000 lookups/day, no key."""
    name = "ipapi.co"

    def lookup(self, ip: str) -> GeoResult:
        try:
            r = httpx.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        except httpx.HTTPError as e:
            raise GeoProviderError(str(e))
        if r.status_code != 200:
            raise GeoProviderError(f"status {r.status_code}")
        data = r.json()
        if data.get("error"):
            raise GeoProviderError(data.get("reason", "lookup failed"))
        return GeoResult(country=data.get("country_name"), city=data.get("city"))


class AlwaysFailsProvider:
    """Test double: simulates a provider that is down."""
    def __init__(self, name: str = "mock-down"):
        self.name = name

    def lookup(self, ip: str) -> GeoResult:
        raise GeoProviderError("simulated outage")


class AlwaysSucceedsProvider:
    """Test double: simulates a provider that answers reliably."""
    def __init__(self, country: str = "Testland", city: str = "Testville", name: str = "mock-up"):
        self.name = name
        self._country = country
        self._city = city

    def lookup(self, ip: str) -> GeoResult:
        return GeoResult(country=self._country, city=self._city)


def enrich_with_fallback(ip: str, providers: list[GeoProvider]) -> tuple[Optional[GeoResult], Optional[str]]:
    """Try each provider in order. First one to succeed wins. If every provider raises,
    return (None, None) -- the caller must still store the submission."""
    for provider in providers:
        try:
            result = provider.lookup(ip)
            return result, provider.name
        except GeoProviderError:
            continue
    return None, None
