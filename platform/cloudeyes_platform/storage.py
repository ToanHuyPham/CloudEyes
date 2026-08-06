"""Content-addressed local bundle storage."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path


class BundleStore:
    """Persist verified ZIP bytes under their SHA-256 digest."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def destination(self, digest: str) -> Path:
        return self.root / digest[:2] / f"{digest}.zip"

    def put(self, source: Path, digest: str) -> tuple[Path, bool]:
        """Store *source* atomically and return ``(path, created)``.

        The source is copied to a temporary file in the destination directory,
        flushed and fsynced through a writable descriptor, verified again by
        SHA-256, and then atomically moved into place.
        """
        destination = self.destination(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            current = hashlib.sha256(destination.read_bytes()).hexdigest()
            if current != digest:
                raise OSError("existing content-addressed bundle has an invalid digest")
            return destination, False

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{digest}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)

        try:
            with source.open("rb") as source_stream:
                with temporary.open("wb") as destination_stream:
                    shutil.copyfileobj(source_stream, destination_stream)
                    destination_stream.flush()
                    os.fsync(destination_stream.fileno())

            copied_digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
            if copied_digest != digest:
                raise OSError("copied bundle digest does not match expected digest")

            os.replace(temporary, destination)

            try:
                destination.chmod(0o600)
            except OSError:
                pass

            return destination, True
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


__all__ = ["BundleStore"]
