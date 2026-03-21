from __future__ import annotations

import json
import re
import logging
from collections import Counter
from decimal import Decimal
from typing import Any

from backend.worker.scrapers.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


def _parse_amazon_price(raw: str) -> Decimal | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d.,]", "", raw.strip())
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rindex(",") > cleaned.rindex("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def _detect_amazon_currency(html: str) -> str:
    # might break if url is weird
    patterns = [
        (r'["\']\$[\d]', "USD"),
        (r'€[\d]', "EUR"),
        (r'£[\d]', "GBP"),
        (r'₹[\d]', "INR"),
        (r'CDN\$', "CAD"),
        (r'A\$', "AUD"),
    ]
    for pat, cur in patterns:
        if re.search(pat, html):
            return cur
    return "USD"


class AmazonExtractor(BaseExtractor):

    async def extract_from_html(
        self, html: str, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]:
        currency = _detect_amazon_currency(html)

        for strategy in (self._from_json_ld, self._from_known_elements, self._from_regex):
            price = strategy(html)
            if price is not None:
                return price, currency

        return None, currency

    async def extract_from_page(
        self, page: Any, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]:
        html = await page.content()
        currency = _detect_amazon_currency(html)

        selectors = [
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#priceblock_saleprice",
            "span.a-price > span.a-offscreen",
            "#corePrice_feature_div span.a-offscreen",
            "#corePriceDisplay_desktop_feature_div span.a-offscreen",
            "#apex_offerDisplay_desktop span.a-offscreen",
            ".a-price .a-offscreen",
            "#price_inside_buybox",
            "#newBuyBoxPrice",
        ]

        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    text = await el.text_content()
                    price = _parse_amazon_price(text)
                    if price is not None:
                        return price, currency
            except Exception:
                continue

        return await self.extract_from_html(html, url, custom_selector)

    def _from_json_ld(self, html: str) -> Decimal | None:
        pattern = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            try:
                data = json.loads(match.group(1).strip())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    price_str = offers.get("price") or offers.get("lowPrice")
                    if price_str:
                        return _parse_amazon_price(str(price_str))
            except (json.JSONDecodeError, ValueError, AttributeError):
                continue
        return None

    def _from_known_elements(self, html: str) -> Decimal | None:
        patterns = [
            r'id="priceblock_ourprice"[^>]*>([^<]+)<',
            r'id="priceblock_dealprice"[^>]*>([^<]+)<',
            r'id="priceblock_saleprice"[^>]*>([^<]+)<',
            r'class="a-offscreen"[^>]*>([^<]+)<',
            r'id="price_inside_buybox"[^>]*>([^<]+)<',
            r'id="newBuyBoxPrice"[^>]*>([^<]+)<',
        ]
        for pat in patterns:
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                price = _parse_amazon_price(match.group(1))
                if price is not None:
                    return price
        return None

    def _from_regex(self, html: str) -> Decimal | None:
        pat = re.compile(r'\$\s*([\d,]+\.?\d*)')
        candidates = []
        for match in pat.findall(html):
            p = _parse_amazon_price(match)
            if p is not None and Decimal("0.01") <= p <= Decimal("99999"):
                candidates.append(p)

        if len(candidates) > 0:
            counts = Counter(candidates)
            return counts.most_common(1)[0][0]
        return None
