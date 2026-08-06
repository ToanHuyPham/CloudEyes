"""Models used by runtime dependency detection and installation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RuntimeDependencyReport:
    """Result of checking benchmark-related operating-system dependencies."""

    platform: str
    package_manager: str | None
    missing_commands: tuple[str, ...] = field(default_factory=tuple)
    packages: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        """Return whether every recommended command is available."""

        return not self.missing_commands
