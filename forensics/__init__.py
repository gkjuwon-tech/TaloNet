"""TaloNet post-capture forensics — architecture & interfaces (planning stage).

This package defines the *interfaces* for analysing the storage/logs of an
enemy drone that has been **physically captured and safely secured** by the
TaloNet net interceptor. It is legal post-incident forensics on seized
property — NOT real-time intrusion, jamming, or spoofing. See
``docs/08_사후_포렌식.md`` for the full pipeline, integrity / chain-of-custody
procedure, and the list of verified open-source parsers each adapter wraps.

Status: **interfaces and pipeline skeleton only.** Concrete acquisition and
parsing logic (pymavlink / pyulog / The Sleuth Kit / dc3dd adapters) lands in
the next step. Nothing here boots, transmits to, or attacks any device.
"""

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
from .pipeline import ForensicPipeline, PipelineStage

__all__ = [
    "AcquiredImage",
    "AnalysisFindings",
    "ChainOfCustody",
    "ContentAnalyzer",
    "CustodyEvent",
    "EvidenceItem",
    "FlightLogParser",
    "FlightTrack",
    "ForensicPipeline",
    "ForensicReport",
    "HashRecord",
    "HashVerifier",
    "Imager",
    "PipelineStage",
    "ReportBuilder",
    "TrackPoint",
    "TrajectoryAnalyzer",
]
