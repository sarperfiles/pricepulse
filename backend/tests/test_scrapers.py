from __future__ import annotations

from decimal import Decimal

import pytest

from backend.worker.scrapers.extractors.getyourguide import (
    GetYourGuideExtractor,
    _detect_currency,
    _parse_price,
)


class TestParsePrice:
    def test_us_format(self):
        assert _parse_price("29.99") == Decimal("29.99")

    def test_us_format_with_commas(self):
        assert _parse_price("1,299.99") == Decimal("1299.99")

    def test_eu_format(self):
        assert _parse_price("29,99") == Decimal("29.99")

    def test_eu_format_with_dots(self):
        assert _parse_price("1.299,99") == Decimal("1299.99")

    def test_currency_symbol_dollar(self):
        assert _parse_price("$29.99") == Decimal("29.99")

    def test_currency_symbol_euro(self):
        assert _parse_price("€49,50") == Decimal("49.50")

    def test_currency_symbol_pound(self):
        assert _parse_price("£100.00") == Decimal("100.00")

    def test_empty_string(self):
        assert _parse_price("") is None

    def test_no_digits(self):
        assert _parse_price("abc") is None

    def test_large_number_no_decimals(self):
        assert _parse_price("1,000,000") == Decimal("1000000")


class TestDetectCurrency:
    def test_dollar_sign(self):
        assert _detect_currency("$29.99") == "USD"

    def test_euro_sign(self):
        assert _detect_currency("€49.99") == "EUR"

    def test_pound_sign(self):
        assert _detect_currency("£19.99") == "GBP"

    def test_iso_code(self):
        assert _detect_currency("USD 29.99") == "USD"

    def test_iso_code_eur(self):
        assert _detect_currency("EUR 49.99") == "EUR"

    def test_no_currency(self):
        assert _detect_currency("29.99") == "EUR"


class TestGetYourGuideExtractor:
    @pytest.mark.asyncio
    async def test_run_strategies_json_ld(self):
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "City Tour",
                "offers": {
                    "@type": "Offer",
                    "price": "45.00",
                    "priceCurrency": "EUR"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        extractor = GetYourGuideExtractor()
        price, currency = extractor._run_strategies(html)
        assert price == Decimal("45.00")
        assert currency == "EUR"

    @pytest.mark.asyncio
    async def test_run_strategies_json_ld_usd(self):
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "name": "NYC Tour",
                "offers": {
                    "@type": "Offer",
                    "price": "89.00",
                    "priceCurrency": "USD"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        extractor = GetYourGuideExtractor()
        price, currency = extractor._run_strategies(html)
        assert price == Decimal("89.00")
        assert currency == "USD"

    @pytest.mark.asyncio
    async def test_run_strategies_no_price(self):
        html = "<html><head></head><body><p>No price here</p></body></html>"
        extractor = GetYourGuideExtractor()
        price, currency = extractor._run_strategies(html)
        assert price is None

    @pytest.mark.asyncio
    async def test_run_strategies_meta_tag_fallback(self):
        html = """
        <html>
        <head>
            <meta property="og:price:amount" content="35.50">
            <meta property="og:price:currency" content="GBP">
        </head>
        <body></body>
        </html>
        """
        extractor = GetYourGuideExtractor()
        price, currency = extractor._run_strategies(html)
        assert price == Decimal("35.50")
        assert currency == "GBP"
