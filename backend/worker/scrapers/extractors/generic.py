from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation
from collections import Counter
from typing import Any

from backend.worker.scrapers.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)

_CURRENCY_SYMBOLS: dict[str, str] = {
    "₺": "TRY",
    "R$": "BRL",
    "A$": "AUD",
    "C$": "CAD",
    "US$": "USD",
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "CHF": "CHF",
    "kr": "SEK",
    "zł": "PLN",
    "Kč": "CZK",
}

_CURRENCY_CODE_RE = re.compile(
    r"\b(USD|EUR|GBP|JPY|INR|BRL|CAD|AUD|CHF|TRY|TL|SEK|NOK|DKK|PLN|CZK|MXN|KRW|SGD|HKD|NZD|ZAR|RUB)\b",
    re.IGNORECASE,
)

_PRICE_CLASS_KEYWORDS = (
    "price", "fiyat", "preis", "prix", "precio", "cost", "amount",
    "sale", "offer", "onsale", "product-price", "current-price",
)

_PRICE_NUMBER_RE = re.compile(
    r"(?:US\$|₺|R\$|A\$|C\$|€|£|\$|¥|₹|CHF|kr|zł|Kč)\s*([\d]{1,7}(?:[.,]\d{1,3})*)"
    r"|([\d]{1,7}(?:[.,]\d{1,3})*)\s*(?:₺|€|£|\$|¥|CHF|kr|zł|Kč|TL|TRY)",
    re.UNICODE,
)

_PRICE_RANGE = (Decimal("0.01"), Decimal("9999999"))


def _parse_price(raw: str) -> Decimal | None:
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
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        val = Decimal(cleaned)
        if _PRICE_RANGE[0] <= val <= _PRICE_RANGE[1]:
            return val
        return None
    except (InvalidOperation, ValueError):
        return None


def _detect_currency(text: str) -> str:
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in text:
            return code
    match = _CURRENCY_CODE_RE.search(text)
    if match:
        code = match.group(1).upper()
        if code == "TL":
            return "TRY"
        return code
    return "USD"


class GenericExtractor(BaseExtractor):

    async def extract_from_html(
        self, html: str, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]:
        strategies = (
            self._from_json_ld,
            self._from_meta_tags,
            self._from_microdata,
            self._from_price_classes,
            self._from_data_attributes,
            self._from_regex,
        )
        for strat in strategies:
            try:
                price, currency = strat(html)
                if price is not None:
                    return price, currency
            except Exception:
                continue
        return None, "USD"

    async def extract_from_page(
        self, page: Any, url: str, custom_selector: str | None = None
    ) -> tuple[Decimal | None, str]:
        if custom_selector:
            try:
                el = await page.query_selector(custom_selector)
                if el:
                    text = await el.text_content()
                    if text:
                        price = _parse_price(text)
                        if price is not None:
                            return price, _detect_currency(text)
                    content = await el.get_attribute("content")
                    if content:
                        price = _parse_price(content)
                        if price is not None:
                            return price, _detect_currency(content)
            except Exception:
                logger.debug("Custom selector %r failed", custom_selector)

        result = await self._extract_via_js(page)
        if result[0] is not None:
            return result

        selectors = [
            '[itemprop="price"]',
            'meta[property="product:price:amount"]',
            'meta[property="og:price:amount"]',
            '[data-testid*="price" i]',
            '[data-price]',
            '[data-product-price]',
            '.price',
            '.product-price',
            '.current-price',
            '#price',
            '.sale-price',
            '.offer-price',
            'span[class*="price" i]',
            'div[class*="price" i]',
            'span[class*="fiyat" i]',
            'div[class*="fiyat" i]',
            'span[class*="preis" i]',
            'span[class*="prix" i]',
            'span[class*="precio" i]',
        ]

        for sel in selectors:
            try:
                elements = await page.query_selector_all(sel)
                for el in elements:
                    content = await el.get_attribute("content")
                    if content:
                        price = _parse_price(content)
                        if price is not None:
                            tag = await el.evaluate("el => el.tagName")
                            if tag == "META":
                                currency_meta = await page.query_selector(
                                    'meta[property="product:price:currency"], '
                                    'meta[property="og:price:currency"]'
                                )
                                if currency_meta:
                                    cur_val = await currency_meta.get_attribute("content")
                                    if cur_val:
                                        return price, cur_val.strip().upper()
                            return price, _detect_currency(content)

                    data_price = await el.get_attribute("data-price")
                    if data_price:
                        price = _parse_price(data_price)
                        if price is not None:
                            return price, _detect_currency(data_price)

                    text = await el.text_content()
                    if text:
                        price = _parse_price(text)
                        if price is not None:
                            return price, _detect_currency(text)
            except Exception:
                continue

        html = await page.content()
        return await self.extract_from_html(html, url, custom_selector)

    async def _extract_via_js(self, page: Any) -> tuple[Decimal | None, str]:
        try:
            result = await page.evaluate("""() => {
                function parseJsonLd() {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const s of scripts) {
                        try {
                            const data = JSON.parse(s.textContent);
                            const items = Array.isArray(data) ? data : [data];
                            const queue = [...items];
                            while (queue.length > 0) {
                                const item = queue.shift();
                                if (!item || typeof item !== 'object') continue;
                                if (item['@graph'] && Array.isArray(item['@graph'])) {
                                    queue.push(...item['@graph']);
                                }
                                const offers = item.offers;
                                if (offers) {
                                    const offerList = Array.isArray(offers) ? offers : [offers];
                                    for (const o of offerList) {
                                        const p = o.price || o.lowPrice || o.highPrice;
                                        if (p !== undefined && p !== null) {
                                            return { price: String(p), currency: o.priceCurrency || '' };
                                        }
                                    }
                                }
                            }
                        } catch {}
                    }
                    return null;
                }

                function parseMeta() {
                    const priceEl = document.querySelector(
                        'meta[property="product:price:amount"], meta[property="og:price:amount"]'
                    );
                    if (priceEl && priceEl.content) {
                        const curEl = document.querySelector(
                            'meta[property="product:price:currency"], meta[property="og:price:currency"]'
                        );
                        return {
                            price: priceEl.content,
                            currency: curEl ? curEl.content : ''
                        };
                    }
                    const itemPrice = document.querySelector('[itemprop="price"]');
                    if (itemPrice) {
                        const val = itemPrice.content || itemPrice.textContent;
                        if (val) {
                            const curEl = document.querySelector('[itemprop="priceCurrency"]');
                            return {
                                price: val.trim(),
                                currency: curEl ? (curEl.content || curEl.textContent || '') : ''
                            };
                        }
                    }
                    return null;
                }

                function parseDom() {
                    const keywords = [
                        'price', 'fiyat', 'preis', 'prix', 'precio'
                    ];
                    const selectors = [
                        '[data-testid*="price"]',
                        '[data-price]',
                        '[data-product-price]',
                    ];
                    for (const kw of keywords) {
                        selectors.push(
                            `span[class*="${kw}"]`,
                            `div[class*="${kw}"]`,
                            `p[class*="${kw}"]`,
                            `[id*="${kw}"]`
                        );
                    }

                    const priceRe = /[\\d][\\d.,]*[\\d]/;
                    const currencyRe = /[\\$\\€\\£\\¥\\₹\\₺]|USD|EUR|GBP|TRY|TL/;

                    let best = null;
                    let bestLen = Infinity;

                    for (const sel of selectors) {
                        try {
                            const els = document.querySelectorAll(sel);
                            for (const el of els) {
                                const dp = el.getAttribute('data-price') || el.getAttribute('data-product-price');
                                if (dp && priceRe.test(dp)) {
                                    return { price: dp, currency: '' };
                                }
                                const text = (el.textContent || '').trim();
                                if (text && priceRe.test(text) && text.length < bestLen) {
                                    if (currencyRe.test(text) || text.length < 30) {
                                        best = text;
                                        bestLen = text.length;
                                    }
                                }
                            }
                        } catch {}
                    }
                    if (best) return { price: best, currency: '' };
                    return null;
                }

                const jsonLd = parseJsonLd();
                if (jsonLd) return jsonLd;
                const meta = parseMeta();
                if (meta) return meta;
                const dom = parseDom();
                if (dom) return dom;
                return null;
            }""")

            if result and result.get("price"):
                raw = result["price"]
                price = _parse_price(raw)
                if price is not None:
                    currency = result.get("currency", "").strip().upper()
                    if not currency or len(currency) != 3:
                        currency = _detect_currency(raw)
                    if currency == "TL":
                        currency = "TRY"
                    return price, currency
        except Exception:
            logger.debug("JS price extraction failed")

        return None, "USD"

    def _from_json_ld(self, html: str) -> tuple[Decimal | None, str]:
        pattern = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            try:
                data = json.loads(match.group(1).strip())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    result = self._walk_json_ld(item)
                    if result[0] is not None:
                        return result
            except (json.JSONDecodeError, ValueError):
                continue
        return None, "USD"

    def _walk_json_ld(self, item: Any, depth: int = 0) -> tuple[Decimal | None, str]:
        if depth > 10 or not isinstance(item, dict):
            return None, "USD"

        result = self._extract_offer_price(item)
        if result[0] is not None:
            return result

        offers = item.get("offers")
        if offers:
            offer_list = offers if isinstance(offers, list) else [offers]
            for o in offer_list:
                if isinstance(o, dict):
                    result = self._extract_offer_price(o)
                    if result[0] is not None:
                        return result
                    inner = o.get("offers")
                    if inner:
                        inner_list = inner if isinstance(inner, list) else [inner]
                        for io in inner_list:
                            result = self._extract_offer_price(io)
                            if result[0] is not None:
                                return result

        graph = item.get("@graph")
        if isinstance(graph, list):
            for node in graph:
                result = self._walk_json_ld(node, depth + 1)
                if result[0] is not None:
                    return result

        return None, "USD"

    def _extract_offer_price(self, offer: Any) -> tuple[Decimal | None, str]:
        if not isinstance(offer, dict):
            return None, "USD"
        currency = offer.get("priceCurrency", "USD")
        if isinstance(currency, str) and currency.upper() == "TL":
            currency = "TRY"

        for key in ("price", "lowPrice", "highPrice"):
            raw = offer.get(key)
            if raw is not None:
                price = _parse_price(str(raw))
                if price is not None:
                    return price, currency

        spec = offer.get("priceSpecification")
        if isinstance(spec, dict):
            cur = spec.get("priceCurrency", currency)
            raw = spec.get("price")
            if raw is not None:
                price = _parse_price(str(raw))
                if price is not None:
                    return price, cur

        return None, currency

    def _from_meta_tags(self, html: str) -> tuple[Decimal | None, str]:
        price_pats = [
            r'<meta[^>]*(?:property|name)=["\'](?:og:price:amount|product:price:amount)["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:price:amount|product:price:amount)["\']',
        ]
        currency_pats = [
            r'<meta[^>]*(?:property|name)=["\'](?:og:price:currency|product:price:currency)["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:price:currency|product:price:currency)["\']',
        ]

        price = None
        currency = "USD"

        for pat in price_pats:
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                price = _parse_price(match.group(1))
                if price is not None:
                    break

        if price is None:
            return None, "USD"

        for pat in currency_pats:
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                currency = match.group(1).strip().upper()
                if currency == "TL":
                    currency = "TRY"
                break

        return price, currency

    def _from_microdata(self, html: str) -> tuple[Decimal | None, str]:
        price_pats = [
            r'<[^>]*itemprop=["\']price["\'][^>]*content=["\']([^"\']+)["\']',
            r'<[^>]*itemprop=["\']price["\'][^>]*>([^<]+)<',
        ]
        currency_pats = [
            r'<[^>]*itemprop=["\']priceCurrency["\'][^>]*content=["\']([^"\']+)["\']',
            r'<[^>]*itemprop=["\']priceCurrency["\'][^>]*>([^<]+)<',
        ]

        price = None
        currency = "USD"

        for pat in price_pats:
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                price = _parse_price(match.group(1))
                if price is not None:
                    break

        if price is None:
            return None, "USD"

        for pat in currency_pats:
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                cur = match.group(1).strip().upper()
                if cur == "TL":
                    cur = "TRY"
                if len(cur) == 3:
                    currency = cur
                break

        return price, currency

    def _from_price_classes(self, html: str) -> tuple[Decimal | None, str]:
        class_re = "|".join(re.escape(kw) for kw in _PRICE_CLASS_KEYWORDS)
        patterns = [
            rf'class="[^"]*(?:{class_re})[^"]*"[^>]*>([^<]*(?:₺|\$|€|£|¥|₹|TL|TRY)\s*[\d.,]+[^<]*)<',
            rf'class="[^"]*(?:{class_re})[^"]*"[^>]*>([^<]*[\d.,]+\s*(?:₺|\$|€|£|¥|₹|TL|TRY)[^<]*)<',
            rf'class="[^"]*(?:{class_re})[^"]*"[^>]*>([^<]*[\d][\d.,]*[\d][^<]*)<',
            rf'id="[^"]*(?:{class_re})[^"]*"[^>]*>([^<]*[\d][\d.,]*[^<]*)<',
        ]

        candidates: list[tuple[Decimal, str, int]] = []
        for pat in patterns:
            for match in re.finditer(pat, html, re.IGNORECASE):
                raw = match.group(1).strip()
                if not raw:
                    continue
                price = _parse_price(raw)
                if price is not None:
                    candidates.append((price, _detect_currency(raw), len(raw)))

        if candidates:
            candidates.sort(key=lambda c: c[2])
            return candidates[0][0], candidates[0][1]

        return None, "USD"

    def _from_data_attributes(self, html: str) -> tuple[Decimal | None, str]:
        patterns = [
            r'data-testid="[^"]*price[^"]*"[^>]*>([^<]+)<',
            r'data-price=["\']([^"\']+)["\']',
            r'data-product-price=["\']([^"\']+)["\']',
            r'data-price-amount=["\']([^"\']+)["\']',
            r'data-current-price=["\']([^"\']+)["\']',
        ]
        for pat in patterns:
            for match in re.finditer(pat, html, re.IGNORECASE):
                raw = match.group(1).strip()
                price = _parse_price(raw)
                if price is not None:
                    return price, _detect_currency(raw)

        return None, "USD"

    def _from_regex(self, html: str) -> tuple[Decimal | None, str]:
        candidates: list[tuple[Decimal, str]] = []
        for match in _PRICE_NUMBER_RE.finditer(html):
            raw = match.group(1) or match.group(2)
            price = _parse_price(raw)
            if price is not None:
                start = max(0, match.start() - 30)
                end = min(len(html), match.end() + 30)
                ctx = html[start:end]
                candidates.append((price, _detect_currency(ctx)))

        if not candidates:
            tl_re = re.compile(
                r"([\d]{1,7}(?:[.,]\d{1,3})*)\s*(?:TL|TRY)",
                re.IGNORECASE | re.UNICODE,
            )
            for match in tl_re.finditer(html):
                price = _parse_price(match.group(1))
                if price is not None:
                    candidates.append((price, "TRY"))

        if candidates:
            price_counts = Counter(c[0] for c in candidates)
            most_common = price_counts.most_common(1)[0][0]
            for p, c in candidates:
                if p == most_common:
                    return p, c

        return None, "USD"
