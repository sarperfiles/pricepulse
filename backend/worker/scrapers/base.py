from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ScrapeResult:
    price: Decimal | None
    currency: str
    status: str
    error_message: str | None = None
    page_title: str | None = None


class BaseScraper(ABC):
    @abstractmethod
    async def scrape(
        self,
        url: str,
        platform: str | None = None,
        custom_selector: str | None = None,
    ) -> ScrapeResult: ...
