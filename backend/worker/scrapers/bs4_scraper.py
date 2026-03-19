from __future__ import annotations

import json
import logging
import re

import httpx
from bs4 import BeautifulSoup

from backend.worker.scrapers.base import BaseScraper, ScrapeResult
from backend.worker.scrapers.extractors import get_extractor

logger = logging.getLogger(__name__)

_TIMEOUT = 20.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    'Accept-Encoding': 'gzip, deflate, br',
}


def _extract_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    name = item.get("name")
                    if name and isinstance(name, str) and len(name) > 3:
                        return name.strip()[:255]
        except (json.JSONDecodeError, ValueError):
            continue

    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return str(og["content"]).strip()[:255]

    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        if len(text) > 3:
            return re.sub(r"\s+", " ", text)[:255]

    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        for sep in [" | ", " - ", " – ", " — ", " :: "]:
            if sep in title:
                title = title.split(sep)[0].strip()
                break
        if len(title) > 3:
            return title[:255]

    return None


class BS4Scraper(BaseScraper):

    async def scrape(
        self,
        url: str,
        platform: str | None = None,
        custom_selector: str | None = None,
    ) -> ScrapeResult:
        extractor = get_extractor(platform)

        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT,
                follow_redirects=True,
                headers=_HEADERS,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

        except httpx.HTTPStatusError as exc:
            logger.warning("HTTP %s for %s", exc.response.status_code, url)
            return ScrapeResult(
                price=None,
                currency="USD",
                status="error",
                error_message=f"HTTP {exc.response.status_code}",
            )
        except httpx.RequestError as exc:
            logger.warning("Request error for %s: %s", url, exc)
            return ScrapeResult(
                price=None,
                currency="USD",
                status="error",
                error_message=str(exc)[:500],
            )

        try:
            price, currency = await extractor.extract_from_html(
                html, url, custom_selector
            )

            page_title = _extract_title(html)

            if price is not None:
                return ScrapeResult(price=price, currency=currency, status="success", page_title=page_title)
            return ScrapeResult(
                price=None,
                currency=currency,
                status="not_found",
                error_message="Price not found in static HTML",
                page_title=page_title,
            )

        except Exception as exc:
            logger.exception("Extraction failed for %s", url)
            return ScrapeResult(
                price=None,
                currency="USD",
                status="error",
                error_message=str(exc)[:500],
            )
