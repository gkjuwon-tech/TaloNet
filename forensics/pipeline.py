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
        """Execute the full pipeline, integrity-gated and custody-logged.

        Fixed order:

        1. INTAKE      — record receipt in the custody log.
        2. IMAGING     — acquire a write-blocked image of the original.
        3. HASH_VERIFY — confirm original/image SHA-256 match (else IntegrityError).
        4. CONTENT     — filesystem/metadata analysis + log discovery on the image.
        5. FLIGHT_LOG  — parse each recovered log with the matching verified parser.
        6. TRAJECTORY  — reconstruct track, estimate launch/target, render map.
        7. REPORT      — assemble threat-intel report + custody appendix.
        """
        import os

        # 1. INTAKE
        custody.record(
            actor=item.seized_by or "operator", action=PipelineStage.INTAKE.value,
            detail=f"{item.device_description} (evidence {item.evidence_id})",
        )

        # 2. IMAGING
        image = self.imager.acquire(item, work_dir)
        custody.record(
            actor="appliance", action=PipelineStage.IMAGING.value,
            detail=f"{image.acquired_with}; write-blocker={image.write_blocker}; "
            f"{image.size_bytes} bytes; format={image.image_format}",
        )

        # 3. HASH_VERIFY — integrity gate
        if not image.verified():
            custody.record(
                actor="appliance", action=PipelineStage.HASH_VERIFY.value,
                detail="HASH MISMATCH original!=image -> STOP",
            )
            raise IntegrityError(
                f"acquisition hash mismatch for {item.evidence_id}: "
                f"original {image.original_hash.sha256[:16]} != "
                f"image {image.image_hash.sha256[:16]}"
            )
        custody.record(
            actor="appliance", action=PipelineStage.HASH_VERIFY.value,
            detail=f"SHA-256 verified original==image ({image.original_hash.sha256[:16]}...)",
        )

        # 4. CONTENT
        content_findings = self.content.analyze(image)
        logs = self.content.discover_logs(image)
        custody.record(
            actor="appliance", action=PipelineStage.CONTENT.value,
            detail=f"{len(content_findings.file_inventory)} files; {len(logs)} candidate logs",
        )

        # 5. FLIGHT_LOG
        tracks = []
        for log_path in logs:
            parser = self._select_parser(log_path)
            if parser is None:
                continue
            try:
                tracks.append(parser.parse(log_path))
            except Exception as exc:  # parser/library failure on one log
                content_findings.payload_assessment.append(
                    f"log {os.path.basename(log_path)} parse failed: {exc}"
                )
        custody.record(
            actor="appliance", action=PipelineStage.FLIGHT_LOG.value,
            detail=f"{len(tracks)} of {len(logs)} logs parsed by verified parsers",
        )

        # 6. TRAJECTORY
        traj_findings = self.trajectory.analyze(tracks)
        if tracks:
            try:
                map_path = self.trajectory.render_map(
                    tracks, os.path.join(work_dir, f"{item.evidence_id}_map.html")
                )
                traj_findings.map_html_path = map_path
            except Exception:  # optional map renderer (folium) unavailable
                pass
        custody.record(
            actor="appliance", action=PipelineStage.TRAJECTORY.value,
            detail=f"launch/target estimated (confidence {traj_findings.confidence:.2f})",
        )

        # 7. REPORT
        findings = content_findings.merge(traj_findings)
        custody.record(
            actor="appliance", action=PipelineStage.REPORT.value,
            detail="threat-intel report generated",
        )
        return self.reporter.build(item.evidence_id, findings, custody.to_log())
