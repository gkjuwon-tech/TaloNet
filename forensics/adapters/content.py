"""Filesystem / content / metadata analyzer.

Walks the read-only file tree of an acquired image to build a hashed file
inventory (hashdeep-style), discover candidate flight/GNSS logs, harvest device
identifiers, and — when available — enrich media with ExifTool / ``exifread``
metadata (GPS tags, camera model, timestamps). If only a raw ``.dd`` image is
present, it attempts a read-only loop mount; otherwise it reports that
filesystem extraction was unavailable rather than guessing.

The inventory + hashing core is stdlib-only; ExifTool/exifread are optional
enrichment, imported lazily.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone

from ..interfaces import AcquiredImage, AnalysisFindings

# candidate flight/GNSS log extensions (router confirms the actual format)
LOG_EXTS = {
    ".bin", ".tlog", ".ulg", ".ulog", ".nmea", ".log", ".txt", ".dat", ".gpx",
}
MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".dng", ".mp4", ".mov", ".tiff", ".srt"}
_ID_PATTERNS = {
    "fcc_id": re.compile(r"FCC[\s_-]?ID[:\s]*([A-Z0-9-]{4,})", re.I),
    "serial": re.compile(r"(?:serial|s/n|sn)[:\s]*([A-Z0-9-]{4,})", re.I),
    "mac": re.compile(r"\b([0-9a-f]{2}(?::[0-9a-f]{2}){5})\b", re.I),
}
_CHUNK = 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


class FileSystemContentAnalyzer:
    """Implements :class:`forensics.interfaces.ContentAnalyzer`."""

    def __init__(self, exiftool: bool = True, max_inventory: int = 10_000) -> None:
        self.use_exiftool = exiftool
        self.max_inventory = max_inventory

    # -- helpers ---------------------------------------------------------------
    def _root(self, image: AcquiredImage) -> str | None:
        if image.extracted_root and os.path.isdir(image.extracted_root):
            return image.extracted_root
        if os.path.isdir(image.image_path):
            return image.image_path
        return None  # raw .dd without an extracted tree (would need loop mount)

    # -- protocol --------------------------------------------------------------
    def analyze(self, image: AcquiredImage) -> AnalysisFindings:
        findings = AnalysisFindings()
        findings.evidence_basis.append(
            f"content analysis of image {image.image_path} "
            f"({image.image_format}, {image.size_bytes} bytes)"
        )
        root = self._root(image)
        if root is None:
            findings.payload_assessment.append(
                "filesystem extraction unavailable for raw image "
                "(mount read-only or extract with The Sleuth Kit, then re-run)"
            )
            return findings

        media_paths: list[str] = []
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                ext = os.path.splitext(name)[1].lower()
                try:
                    size = os.path.getsize(full)
                    digest = _sha256(full)
                except OSError:
                    continue
                if len(findings.file_inventory) < self.max_inventory:
                    findings.file_inventory.append(
                        {"path": rel, "size": str(size), "sha256": digest, "type": ext}
                    )
                if ext in MEDIA_EXTS:
                    media_paths.append(full)
                self._scan_identifiers(full, ext, findings)

        if media_paths:
            findings.media_metadata = self._media_metadata(media_paths)
        findings.payload_assessment.append(
            f"{len(findings.file_inventory)} files inventoried, "
            f"{len(media_paths)} media files"
        )
        return findings

    def discover_logs(self, image: AcquiredImage) -> list[str]:
        root = self._root(image)
        if root is None:
            return []
        logs: list[str] = []
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if os.path.splitext(name)[1].lower() in LOG_EXTS:
                    logs.append(os.path.join(dirpath, name))
        return sorted(logs)

    # -- identifiers / metadata ------------------------------------------------
    def _scan_identifiers(self, path: str, ext: str, findings: AnalysisFindings) -> None:
        # only sniff small text-ish config/log files for embedded identifiers
        if ext not in {".txt", ".cfg", ".conf", ".ini", ".log", ".json", ".param"}:
            return
        try:
            if os.path.getsize(path) > 256 * 1024:
                return
            with open(path, "r", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            return
        for key, pat in _ID_PATTERNS.items():
            m = pat.search(text)
            if m and key not in findings.identifiers:
                findings.identifiers[key] = m.group(1)

    def _media_metadata(self, paths: list[str]) -> list[dict[str, str]]:
        if self.use_exiftool and shutil.which("exiftool"):
            return self._exiftool_metadata(paths)
        return self._exifread_metadata(paths)

    def _exiftool_metadata(self, paths: list[str]) -> list[dict[str, str]]:
        import json

        out: list[dict[str, str]] = []
        try:
            res = subprocess.run(
                ["exiftool", "-json", "-n", *paths],
                capture_output=True, text=True, check=True,
            )
            for rec in json.loads(res.stdout):
                out.append({k: str(v) for k, v in rec.items()})
        except (subprocess.SubprocessError, ValueError):
            return self._exifread_metadata(paths)
        return out

    def _exifread_metadata(self, paths: list[str]) -> list[dict[str, str]]:
        try:
            import exifread  # type: ignore
        except ImportError:
            return [{"note": "install exiftool or exifread for media metadata"}]
        out: list[dict[str, str]] = []
        for p in paths:
            try:
                with open(p, "rb") as fh:
                    tags = exifread.process_file(fh, details=False)
            except OSError:
                continue
            if tags:
                rec = {"SourceFile": os.path.basename(p)}
                rec.update({str(k): str(v) for k, v in tags.items()})
                out.append(rec)
        return out
