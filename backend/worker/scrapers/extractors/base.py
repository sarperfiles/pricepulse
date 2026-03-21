from __future__ import annotations

from decimal import Decimal
from abc import ABC, abstractmethod
from typing import Any


class BaseExtractor(ABC):
    @abstractmethod
    async def extract_from_html(
        self, html: str, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]: ...

    @abstractmethod
    async def extract_from_page(
        self, page: Any, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]: ...
