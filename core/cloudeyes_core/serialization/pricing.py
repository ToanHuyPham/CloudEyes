"""Pricing catalog JSON deserialization."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import (
    PriceQuote,
    PricingCatalog,
    PricingCommitment,
    PricingOperatingSystem,
    PricingSource,
    PricingSourceTier,
)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _sequence(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be an array")
    return value


def _datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a date-time string")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} is not a valid ISO date-time") from error
    if result.tzinfo is None:
        raise ValueError(f"{field_name} must contain timezone information")
    return result


def pricing_catalog_from_dict(data: Mapping[str, Any]) -> PricingCatalog:
    """Create a validated pricing catalog from decoded JSON data."""

    quotes: list[PriceQuote] = []
    for index, raw_quote in enumerate(_sequence(data.get("quotes"), "quotes")):
        quote_data = _mapping(raw_quote, f"quotes[{index}]")
        source_data = _mapping(quote_data.get("source"), f"quotes[{index}].source")
        valid_until_raw = quote_data.get("valid_until")
        tax_included = quote_data.get("tax_included")
        if tax_included is not None and not isinstance(tax_included, bool):
            raise ValueError(f"quotes[{index}].tax_included must be boolean or null")
        quotes.append(
            PriceQuote(
                quote_id=quote_data["quote_id"],
                provider_id=quote_data["provider_id"],
                product=quote_data["product"],
                plan=quote_data["plan"],
                region=quote_data.get("region"),
                zone=quote_data.get("zone"),
                observed_at=_datetime(quote_data["observed_at"], "observed_at"),
                valid_from=_datetime(quote_data["valid_from"], "valid_from"),
                valid_until=(
                    None if valid_until_raw is None else _datetime(valid_until_raw, "valid_until")
                ),
                commitment=PricingCommitment(quote_data["commitment"]),
                operating_system=PricingOperatingSystem(quote_data["operating_system"]),
                amount=quote_data["amount"],
                currency=quote_data["currency"],
                billing_period=quote_data["billing_period"],
                billing_period_hours=quote_data["billing_period_hours"],
                fx_to_usd=quote_data["fx_to_usd"],
                tax_included=tax_included,
                source=PricingSource(
                    tier=PricingSourceTier(source_data["tier"]),
                    reference=source_data["reference"],
                ),
            )
        )
    return PricingCatalog(schema_version=data["schema_version"], quotes=tuple(quotes))


def loads_pricing_catalog(text: str) -> PricingCatalog:
    """Deserialize one pricing catalog from JSON text."""

    data = json.loads(text)
    return pricing_catalog_from_dict(_mapping(data, "pricing catalog"))


def load_pricing_catalog(path: str | Path) -> PricingCatalog:
    """Deserialize one pricing catalog from a UTF-8 JSON file."""

    return loads_pricing_catalog(Path(path).read_text(encoding="utf-8"))
