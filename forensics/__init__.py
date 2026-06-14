"""TaloNet post-capture counter-UAS exploitation package.

Exploits the storage/logs of a hostile drone that has been **physically captured
and safely secured** (non-kinetically, by the TaloNet net interceptor) to produce
**counter-UAS target intelligence** — chiefly the hostile **launch site** — that
supports a proportionate, human-authorized **self-defence** response against the
source of the attack. The adversary struck first with hostile intent; TaloNet
only defended (capture, no first strike) and never jams or spoofs.

This is offline technical exploitation of secured hardware — NOT real-time
intrusion, jamming, or spoofing. It produces *intelligence only*; every
engagement decision remains with the authorized commander under the Rules of
Engagement and the Law of Armed Conflict (distinction, proportionality,
precautions; never civilians or civilian objects). See ``docs/08_사후_포렌식.md``
for the pipeline and provenance procedure, and ``docs/09``/``docs/10`` for the
ForensIQ-1 appliance that runs it.

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
