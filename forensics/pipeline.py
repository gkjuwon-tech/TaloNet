"""Seven-stage forensic pipeline orchestration (skeleton).

``ForensicPipeline`` wires the stage adapters together and *enforces order and
integrity*: nothing is parsed before the image is hash-verified against the
original, and every stage is recorded to the chain-of-custody log. The stage
adapters themselves (Imager, parsers, ...) are injected and remain
interface-only at this planning stage, so :meth:`run` raises
``NotImplementedError`` until concrete verified-OSS adapters are supplied.

Pipeline (see ``docs/08_사후_포렌식.md`` §2):
    intake -> imaging -> hash -> content -> flightlog -> trajectory -> report
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from .chain_of_custody import ChainOfCustody
from .interfaces import (
    ContentAnalyzer,
    EvidenceItem,
    FlightLogParser,
    ForensicReport,
    HashVerifier,
    Imager,
    ReportBuilder,
    TrajectoryAnalyzer,
)


class PipelineStage(Enum):
    """Ordered stages of the forensic pipeline."""

    INTAKE = "intake"
    IMAGING = "imaging"
    HASH_VERIFY = "hash_verify"
    CONTENT = "content"
    FLIGHT_LOG = "flight_log"
    TRAJECTORY = "trajectory"
    REPORT = "report"


class IntegrityError(RuntimeError):
    """Raised when an integrity gate fails (e.g. original/image hash mismatch)."""


class ForensicPipeline:
    """Orchestrates the seven stages under chain-of-custody and integrity gates.

    Adapters are injected so each stage can wrap a verified OSS tool. The
    pipeline owns ordering + the integrity checks; it never writes to the
    original evidence.
    """

    def __init__(
        self,
        imager: Imager,
        hasher: HashVerifier,
        content: ContentAnalyzer,
        log_parsers: list[FlightLogParser],
        trajectory: TrajectoryAnalyzer,
        reporter: ReportBuilder,
    ) -> None:
        self.imager = imager
        self.hasher = hasher
        self.content = content
        self.log_parsers = log_parsers
        self.trajectory = trajectory
        self.reporter = reporter

    def _select_parser(self, log_path: str) -> Optional[FlightLogParser]:
        """Pick the first verified parser that supports this log format."""
        for parser in self.log_parsers:
            if parser.supports(log_path):
                return parser
        return None

    def run(
        self,
        item: EvidenceItem,
        custody: ChainOfCustody,
        work_dir: str,
    ) -> ForensicReport:
        """Execute the full pipeline.

        Order is fixed and integrity-gated:

        1. INTAKE     — record receipt + sealing in the custody log.
        2. IMAGING    — acquire a write-blocked image of the original.
        3. HASH_VERIFY— confirm original/image SHA-256 match (else IntegrityError).
        4. CONTENT    — filesystem/carving/metadata analysis on the image.
        5. FLIGHT_LOG — parse recovered logs with the matching verified parser.
        6. TRAJECTORY — reconstruct track, estimate launch/target, render map.
        7. REPORT     — assemble threat-intel report + custody appendix.

        Concrete adapters are not yet implemented (planning stage), so this
        raises ``NotImplementedError``. The control/integrity flow above is the
        contract the adapters must satisfy.
        """
        raise NotImplementedError(
            "ForensicPipeline.run is a planning-stage skeleton; inject concrete "
            "verified-OSS adapters (dc3dd/pymavlink/pyulog/TSK/folium) to enable. "
            "See docs/08_사후_포렌식.md."
        )
