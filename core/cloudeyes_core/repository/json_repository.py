"""Validated atomic JSON repository for CloudEyes samples."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Iterator

from ..models import Sample
from ..serialization import dumps, load_sample
from ..validation import ensure_valid_sample

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class JsonSampleRepository:
    """Store one sample per JSON file in a local directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, sample_id: str) -> Path:
        if not _SAFE_ID.fullmatch(sample_id):
            raise ValueError(
                "sample_id must contain only letters, numbers, dot, underscore, or hyphen"
            )
        return self.root / f"{sample_id}.json"

    def save(self, sample: Sample, *, overwrite: bool = False) -> Path:
        """Validate and atomically save a sample."""

        ensure_valid_sample(sample)
        destination = self._path(sample.sample_id)
        if destination.exists() and not overwrite:
            raise FileExistsError(f"sample already exists: {sample.sample_id}")

        text = dumps(sample) + "\n"
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.root,
                prefix=f".{sample.sample_id}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(text)
                handle.flush()
                temporary_name = handle.name
            Path(temporary_name).replace(destination)
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

        return destination

    def load(self, sample_id: str) -> Sample:
        """Load and validate a stored sample."""

        sample = load_sample(self._path(sample_id))
        ensure_valid_sample(sample)
        return sample

    def list_ids(self) -> tuple[str, ...]:
        """Return stored sample IDs in deterministic order."""

        return tuple(path.stem for path in sorted(self.root.glob("*.json")))

    def iter_samples(self) -> Iterator[Sample]:
        """Iterate through all stored samples in ID order."""

        for sample_id in self.list_ids():
            yield self.load(sample_id)

    def delete(self, sample_id: str) -> bool:
        """Delete a sample and return whether it existed."""

        path = self._path(sample_id)
        if not path.exists():
            return False
        path.unlink()
        return True
