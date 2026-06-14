"""Concrete forensic stage adapters.

Each adapter implements a stage ``Protocol`` from :mod:`forensics.interfaces`,
wrapping a verified open-source tool or a dependency-free reference routine:

- :class:`~forensics.adapters.imaging.DiskImager` — read-only bit copy + SHA-256
  (stdlib; optionally shells out to ``dc3dd`` when present).
- :class:`~forensics.adapters.hashing.Sha256Verifier` — stdlib ``hashlib``.
- :class:`~forensics.adapters.content.FileSystemContentAnalyzer` — file inventory,
  hashing, log discovery, optional ExifTool/exifread metadata.
- :mod:`~forensics.adapters.flightlog` — pymavlink (ArduPilot ``.bin``/``.tlog``),
  pyulog (PX4 ``.ulg``), pynmea2 (NMEA), dji-log-parser (DJI).
- :class:`~forensics.adapters.trajectory.TrajectoryReconstructor` — launch/target
  estimation + folium map.
- :class:`~forensics.adapters.report.PdfReportBuilder` — fpdf2 threat-intel PDF.

Heavy third-party libraries are imported lazily inside methods so ``import
forensics`` works with zero dependencies installed.
"""

from .content import FileSystemContentAnalyzer
from .flightlog import (
    ArduPilotLogParser,
    DjiLogParser,
    LogParserRouter,
    NmeaLogParser,
    Px4UlogParser,
)
from .hashing import Sha256Verifier
from .imaging import DiskImager
from .report import PdfReportBuilder
from .trajectory import TrajectoryReconstructor

__all__ = [
    "ArduPilotLogParser",
    "DiskImager",
    "DjiLogParser",
    "FileSystemContentAnalyzer",
    "LogParserRouter",
    "NmeaLogParser",
    "PdfReportBuilder",
    "Px4UlogParser",
    "Sha256Verifier",
    "TrajectoryReconstructor",
]
