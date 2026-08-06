"""Identity models used across CloudEyes."""

from __future__ import annotations

from dataclasses import dataclass


def _required(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    """Identity of a cloud or infrastructure provider."""

    provider_id: str
    name: str
    country_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _required(self.provider_id, "provider_id"))
        object.__setattr__(self, "name", _required(self.name, "name"))

        if self.country_code is not None:
            code = self.country_code.strip().upper()
            if len(code) != 2:
                raise ValueError("country_code must be a 2-letter ISO code")
            object.__setattr__(self, "country_code", code)


@dataclass(frozen=True, slots=True)
class ProductIdentity:
    """Provider product, plan, and location represented by a sample."""

    product: str | None = None
    plan: str | None = None
    region: str | None = None
    zone: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("product", "plan", "region", "zone"):
            value = getattr(self, field_name)
            if value is not None:
                cleaned = value.strip()
                object.__setattr__(self, field_name, cleaned or None)


@dataclass(frozen=True, slots=True)
class MachineIdentity:
    """Basic machine identity without sensitive host information."""

    machine_type: str
    cpu_count: int
    memory_bytes: int
    architecture: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "machine_type", _required(self.machine_type, "machine_type"))
        object.__setattr__(self, "architecture", _required(self.architecture, "architecture"))

        if self.cpu_count <= 0:
            raise ValueError("cpu_count must be greater than zero")

        if self.memory_bytes <= 0:
            raise ValueError("memory_bytes must be greater than zero")
