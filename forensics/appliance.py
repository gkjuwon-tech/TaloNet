"""High-level appliance workflow for the TaloNet ForensIQ-1 kiosk.

Ties the default verified-OSS adapters into one call the operator UI invokes
after a captured hostile card is inserted into the write-blocked slot:

    insert card -> image + SHA-256 verify -> content/log analysis ->
    launch-site geolocation + intent -> counter-UAS target-intel report ->
    print (built-in printer) + archive PDF/map/text to the write-once
    Evidence USB -> eject + seal.

Everything runs read-only on the captured media and is provenance-logged. The
product is target INTELLIGENCE for a proportionate, human-authorized self-defence
response under ROE/LOAC — not a fire order. ``process_card`` returns the built
report and its provenance chain.
"""

from __future__ import annotations

import os
import shutil
from importlib import metadata

from .adapters.content import FileSystemContentAnalyzer
from .adapters.flightlog import (
    ArduPilotLogParser,
    DjiLogParser,
    NmeaLogParser,
    Px4UlogParser,
)
from .adapters.hashing import Sha256Verifier
from .adapters.imaging import DiskImager
from .adapters.report import PdfReportBuilder
from .adapters.trajectory import TrajectoryReconstructor
from .chain_of_custody import ChainOfCustody
from .interfaces import EvidenceItem, ForensicReport
from .pipeline import ForensicPipeline
from .printing import TextReportPrinter

_TOOL_PACKAGES = ["pymavlink", "pyulog", "pynmea2", "gpxpy", "folium", "fpdf2"]


def _tool_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pkg in _TOOL_PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = "not installed"
    return versions


class ForensicAppliance:
    """Default-wired forensic kiosk workflow."""

    def __init__(
        self,
        work_dir: str,
        evidence_usb: str | None = None,
        printer=None,
        write_blocker: str = "hardware write-blocker (read-only)",
    ) -> None:
        self.work_dir = work_dir
        self.evidence_usb = evidence_usb
        self.printer = printer or TextReportPrinter()
        self.tool_versions = _tool_versions()
        os.makedirs(work_dir, exist_ok=True)
        self.pipeline = ForensicPipeline(
            imager=DiskImager(write_blocker=write_blocker),
            hasher=Sha256Verifier(),
            content=FileSystemContentAnalyzer(),
            log_parsers=[
                ArduPilotLogParser(),
                Px4UlogParser(),
                NmeaLogParser(),
                DjiLogParser(),
            ],
            trajectory=TrajectoryReconstructor(),
            reporter=PdfReportBuilder(out_dir=work_dir, tool_versions=self.tool_versions),
        )

    def process_card(
        self,
        evidence_id: str,
        source_path: str,
        seized_by: str,
        device_description: str,
        witness: str = "",
        seized_at: str = "",
        identifiers: dict[str, str] | None = None,
    ) -> tuple[ForensicReport, ChainOfCustody]:
        """Run the full workflow on a freshly inserted, write-blocked card."""
        custody = ChainOfCustody(evidence_id)
        item = EvidenceItem(
            evidence_id=evidence_id,
            seized_at=seized_at,
            seized_by=seized_by,
            device_description=device_description,
            source_path=source_path,
            identifiers=identifiers or {},
        )
        report = self.pipeline.run(item, custody, self.work_dir)

        if self.evidence_usb:
            self._archive(report)
        self.printer.print_report(report)
        custody.record(
            actor=seized_by or "operator", action="seal",
            detail="card ejected; tamper seal applied; case closed", witness=witness,
        )
        return report, custody

    # -- write-once archival ---------------------------------------------------
    def _archive(self, report: ForensicReport) -> None:
        dest = os.path.join(self.evidence_usb, report.evidence_id)
        os.makedirs(dest, exist_ok=True)
        for path in (report.pdf_path, report.map_html_path):
            if path and os.path.exists(path):
                shutil.copy2(path, dest)
