"""TaloNet post-capture forensics package.

Analyses the storage/logs of an enemy drone that has been **physically captured
and safely secured** by the TaloNet net interceptor. This is legal post-incident
forensics on seized property — NOT real-time intrusion, jamming, or spoofing.
See ``docs/08_사후_포렌식.md`` for the pipeline, integrity / chain-of-custody
procedure and the verified open-source parsers each adapter wraps, and
``docs/09``/``docs/10`` for the ForensIQ-1 appliance that runs it.

The public surface is the stage interfaces (:mod:`forensics.interfaces`), the
chain-of-custody log, the ``ForensicPipeline`` orchestrator, the concrete
verified-OSS adapters (:mod:`forensics.adapters`), the printer sinks
(:mod:`forensics.printing`) and the high-level ``ForensicAppliance``. Heavy
third-party libraries are imported lazily inside adapters, so ``import
forensics`` works with zero dependencies installed.
"""

from .appliance import ForensicAppliance
from .chain_of_custody import ChainOfCustody, CustodyEvent
from .interfaces import (
    AcquiredImage,
    AnalysisFindings,
    ContentAnalyzer,
    EvidenceItem,
    FlightLogParser,
    FlightTrack,
    ForensicReport,
    HashRecord,
    HashVerifier,
    Imager,
    ReportBuilder,
    TrackPoint,
    TrajectoryAnalyzer,
)
from .pipeline import ForensicPipeline, IntegrityError, PipelineStage

__all__ = [
    "AcquiredImage",
    "AnalysisFindings",
    "ChainOfCustody",
    "ContentAnalyzer",
    "CustodyEvent",
    "EvidenceItem",
    "FlightLogParser",
    "FlightTrack",
    "ForensicAppliance",
    "ForensicPipeline",
    "ForensicReport",
    "HashRecord",
    "HashVerifier",
    "Imager",
    "IntegrityError",
    "PipelineStage",
    "ReportBuilder",
    "TrackPoint",
    "TrajectoryAnalyzer",
]
