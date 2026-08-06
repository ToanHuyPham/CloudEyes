"""Versioned benchmark protocol identity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProtocolIdentity:
    """Identity of the protocol used to create a sample."""

    profile: str
    version: str
    fingerprint: str

    def __post_init__(self) -> None:
        for field_name in ("profile", "version", "fingerprint"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)

    @property
    def key(self) -> str:
        """Return a deterministic human-readable protocol key."""

        return f"{self.profile}:{self.version}:{self.fingerprint}"
