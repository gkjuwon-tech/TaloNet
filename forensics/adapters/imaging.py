"""Read-only forensic acquisition (imaging) adapter.

Two acquisition modes, both never writing to the source:

- **Physical (raw .dd):** when the source is a device node or image file, stream
  it byte-for-byte into a raw image, hashing source and image independently so
  the copy can be proven faithful (``AcquiredImage.verified()``). Optionally
  shells out to ``dc3dd`` (forensic dd with built-in hashing) when present.
- **Logical:** when the source is an already write-blocked read-only mount
  (a directory), copy the file tree and fingerprint it with a deterministic
  per-file SHA-256 manifest, exposing the copy as ``extracted_root``.

Stdlib only. The write-blocker is a *precondition* enforced operationally (a
hardware blocker or ``blockdev --setro`` / ``mount -o ro``); this module assumes
read-only source access and records which blocker was declared.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from datetime import datetime, timezone

from ..interfaces import AcquiredImage, EvidenceItem, HashRecord

_CHUNK = 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_file(path: str) -> tuple[str, str, int]:
    sha, blake, size = hashlib.sha256(), hashlib.blake2b(), 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            sha.update(chunk)
            blake.update(chunk)
            size += len(chunk)
    return sha.hexdigest(), blake.hexdigest(), size


def folder_manifest_hash(root: str) -> tuple[str, int]:
    """Deterministic SHA-256 over ``relpath\\0<sha256>`` lines + total size.

    Order-independent across runs (paths sorted), so two faithful copies of the
    same tree produce the same fingerprint.
    """
    manifest = hashlib.sha256()
    total = 0
    entries = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            digest, _b, size = _hash_file(full)
            entries.append((rel.replace(os.sep, "/"), digest, size))
    for rel, digest, size in sorted(entries):
        manifest.update(f"{rel}\0{digest}\n".encode("utf-8"))
        total += size
    return manifest.hexdigest(), total


class DiskImager:
    """Implements :class:`forensics.interfaces.Imager`."""

    def __init__(
        self,
        write_blocker: str = "software RO (blockdev --setro / mount -o ro)",
        use_dc3dd: bool = False,
    ) -> None:
        self.write_blocker = write_blocker
        self.use_dc3dd = use_dc3dd

    # -- public ----------------------------------------------------------------
    def acquire(self, item: EvidenceItem, dest_dir: str) -> AcquiredImage:
        if not item.source_path:
            raise ValueError("EvidenceItem.source_path is required for imaging")
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.isdir(item.source_path):
            return self._acquire_logical(item, dest_dir)
        return self._acquire_raw(item, dest_dir)

    # -- modes -----------------------------------------------------------------
    def _acquire_raw(self, item: EvidenceItem, dest_dir: str) -> AcquiredImage:
        src = item.source_path
        img_path = os.path.join(dest_dir, f"{item.evidence_id}.dd")
        tool = "python stdlib stream copy"
        if self.use_dc3dd and shutil.which("dc3dd"):
            subprocess.run(
                ["dc3dd", f"if={src}", f"of={img_path}", "hash=sha256"],
                check=True,
            )
            tool = "dc3dd (hash=sha256)"
        else:
            with open(src, "rb") as r, open(img_path, "wb") as w:
                for chunk in iter(lambda: r.read(_CHUNK), b""):
                    w.write(chunk)
        s_sha, s_blake, s_size = _hash_file(src)
        i_sha, i_blake, _i_size = _hash_file(img_path)
        return AcquiredImage(
            evidence_id=item.evidence_id,
            image_path=img_path,
            image_format="raw",
            original_hash=HashRecord(s_sha, s_blake, _utc_now(), tool),
            image_hash=HashRecord(i_sha, i_blake, _utc_now(), "hashlib (verify)"),
            acquired_with=tool,
            write_blocker=self.write_blocker,
            size_bytes=s_size,
        )

    def _acquire_logical(self, item: EvidenceItem, dest_dir: str) -> AcquiredImage:
        src = item.source_path
        extracted = os.path.join(dest_dir, f"{item.evidence_id}.extracted")
        if os.path.exists(extracted):
            shutil.rmtree(extracted)
        shutil.copytree(src, extracted)
        s_hash, s_size = folder_manifest_hash(src)
        i_hash, _i_size = folder_manifest_hash(extracted)
        return AcquiredImage(
            evidence_id=item.evidence_id,
            image_path=extracted,
            image_format="logical-tree",
            original_hash=HashRecord(s_hash, None, _utc_now(), "manifest sha256"),
            image_hash=HashRecord(i_hash, None, _utc_now(), "manifest sha256 (verify)"),
            acquired_with="logical copy (read-only file tree)",
            write_blocker=self.write_blocker,
            extracted_root=extracted,
            size_bytes=s_size,
        )
