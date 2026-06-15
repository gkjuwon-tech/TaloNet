"""SHA-256 (+ optional BLAKE2b) integrity verifier — stdlib only."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ..interfaces import HashRecord

_CHUNK = 1024 * 1024  # 1 MiB streaming reads


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Sha256Verifier:
    """Stream a file through SHA-256 (and BLAKE2b) without loading it all in RAM.

    Implements the :class:`forensics.interfaces.HashVerifier` protocol.
    """

    def __init__(self, with_blake2b: bool = True) -> None:
        self.with_blake2b = with_blake2b

    def hash_artifact(self, path: str) -> HashRecord:
        sha = hashlib.sha256()
        blake = hashlib.blake2b() if self.with_blake2b else None
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(_CHUNK), b""):
                sha.update(chunk)
                if blake is not None:
                    blake.update(chunk)
        return HashRecord(
            sha256=sha.hexdigest(),
            blake2b=blake.hexdigest() if blake is not None else None,
            computed_at=_utc_now(),
            tool=f"hashlib/{hashlib.__name__} (Python stdlib)",
        )

    def verify(self, expected: HashRecord, path: str) -> bool:
        """Recompute and compare against an expected SHA-256 fingerprint."""
        actual = self.hash_artifact(path)
        return actual.sha256 == expected.sha256
