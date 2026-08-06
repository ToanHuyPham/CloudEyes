"""Provider, product, and machine identity models."""

from __future__ import annotations

from dataclasses import dataclass


def _required(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    """Stable identity of a cloud or infrastructure provider."""

    provider_id: str
    name: str
    country_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _required(self.provider_id, "provider_id"))
        object.__setattr__(self, "name", _required(self.name, "name"))

        if self.country_code is not None:
            code = self.country_code.strip().upper()
            if len(code) != 2 or not code.isalpha():
                raise ValueError("country_code must be a 2-letter code")
            object.__setattr__(self, "country_code", code)


@dataclass(frozen=True, slots=True)
class ProductIdentity:
    """Product, plan, and location represented by a sample."""

    product: str | None = None
    plan: str | None = None
    region: str | None = None
    zone: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("product", "plan", "region", "zone"):
            object.__setattr__(self, field_name, _optional(getattr(self, field_name)))


@dataclass(frozen=True, slots=True)
class MachineIdentity:
    """Non-sensitive machine identity used for cohort compatibility."""

    machine_type: str
    cpu_count: int
    memory_bytes: int
    architecture: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "machine_type", _required(self.machine_type, "machine_type"))
        object.__setattr__(self, "architecture", _required(self.architecture, "architecture"))

        if isinstance(self.cpu_count, bool) or self.cpu_count <= 0:
            raise ValueError("cpu_count must be greater than zero")
        if isinstance(self.memory_bytes, bool) or self.memory_bytes <= 0:
            raise ValueError("memory_bytes must be greater than zero")
