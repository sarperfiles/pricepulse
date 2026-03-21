from __future__ import annotations

from backend.worker.scrapers.extractors.base import BaseExtractor
from backend.worker.scrapers.extractors.generic import GenericExtractor
from backend.worker.scrapers.extractors.amazon import AmazonExtractor
from backend.worker.scrapers.extractors.getyourguide import GetYourGuideExtractor
from backend.worker.scrapers.extractors.hepsiburada import HepsiburadaExtractor

_REGISTRY: dict[str, BaseExtractor] = {
    "getyourguide": GetYourGuideExtractor(),
    "amazon": AmazonExtractor(),
    "hepsiburada": HepsiburadaExtractor(),
}

_GENERIC = GenericExtractor()


def get_extractor(platform: str | None) -> BaseExtractor:
    if platform is None:
        return _GENERIC
    return _REGISTRY.get(platform.lower(), _GENERIC)
