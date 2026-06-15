"""Data contracts and stage interfaces for the post-capture forensic pipeline.

Every stage is a :class:`typing.Protocol`, so a concrete implementation is just
an *adapter* around a verified open-source tool (e.g. ``Imager`` -> dc3dd,
``FlightLogParser`` -> pymavlink / pyulog / pynmea2). Keeping the contracts here
lets the pipeline enforce ordering and integrity without depending on any
particular parser. See ``docs/08_사후_포렌식.md`` §5 for the verified-OSS list.

This module defines **types only** — no acquisition, parsing, or I/O is
performed here. Concrete adapters arrive in the next implementation step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------


@dataclass
class EvidenceItem:
    """A seized storage device under chain-of-custody.

    The original is read-only/sealed; analysis only ever touches a copy.
    """

    evidence_id: str
    seized_at: str  # ISO-8601 UTC, links to capture mission ID/coords/time
    seized_by: str
    device_description: str  # e.g. "32GB microSD, SanDisk, s/n ..."
    source_path: Optional[str] = None  # path to the write-blocked device node
    identifiers: dict[str, str] = field(default_factory=dict)  # FCC ID, MAC, ...


@dataclass
class HashRecord:
    """Integrity fingerprints of an artifact, recomputed at each checkpoint."""

    sha256: str
    blake2b: Optional[str] = None
    computed_at: str = ""  # ISO-8601 UTC
    tool: str = ""  # e.g. "sha256sum (coreutils 9.4)"


@dataclass
class AcquiredImage:
    """A forensic image produced behind a write-blocker (raw .dd or E01)."""

    evidence_id: str
    image_path: str
    image_format: str  # "raw" | "ewf-e01"
    original_hash: HashRecord
    image_hash: HashRecord
    acquired_with: str  # e.g. "dc3dd 7.2.646" / "ewfacquire (libewf 20240506)"
    write_blocker: str  # hardware model or "blockdev --setro"
    # read-only directory view of the recovered files (mount/extract), if any
    extracted_root: Optional[str] = None
    size_bytes: int = 0

    def verified(self) -> bool:
        """True iff the image faithfully reproduces the original (hash match)."""
        return self.original_hash.sha256 == self.image_hash.sha256


@dataclass
class TrackPoint:
    """One time-stamped GNSS fix extracted from a flight log."""

    t_utc: str
    lat: float
    lon: float
    alt_m: Optional[float] = None
    speed_ms: Optional[float] = None
    fix_quality: Optional[str] = None  # e.g. "3D", "RTK_FIXED"


@dataclass
class FlightTrack:
    """A parsed trajectory plus the provenance of the parser used."""

    source_format: str  # "ardupilot-bin" | "px4-ulog" | "nmea" | "dji" | ...
    parser: str  # e.g. "pymavlink DFReader 2.4.x"
    points: list[TrackPoint] = field(default_factory=list)
    home_position: Optional[TrackPoint] = None
    waypoints: list[TrackPoint] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # --- richer exploitation harvest (filled when the log format carries it) ---
    params: dict[str, str] = field(default_factory=dict)  # curated intel parameters
    mission: list[TrackPoint] = field(default_factory=list)  # planned waypoints/targets
    firmware: dict[str, str] = field(default_factory=dict)  # autopilot/version/board/hwid
    energy_mah: Optional[float] = None  # battery capacity used -> endurance/range


@dataclass
class AnalysisFindings:
    """Human-reviewable conclusions; every estimate carries a confidence."""

    # Hostile launch/origin site — the COUNTER-UAS interest (where the attack
    # came from). This is the actionable geolocation for a proportionate,
    # human-authorized self-defence response under ROE/LOAC.
    launch_estimate: Optional[TrackPoint] = None
    launch_radius_m: Optional[float] = None  # geolocation uncertainty radius (CEP-like)
    # Intended target — the friendly/defended asset the hostile UAS was aimed at.
    target_estimate: Optional[TrackPoint] = None
    confidence: float = 0.0  # 0..1 geolocation confidence, NEVER a certainty
    media_metadata: list[dict[str, str]] = field(default_factory=list)
    payload_assessment: list[str] = field(default_factory=list)
    identifiers: dict[str, str] = field(default_factory=dict)  # IFF / attribution
    evidence_basis: list[str] = field(default_factory=list)  # cited log/tool refs
    file_inventory: list[dict[str, str]] = field(default_factory=list)  # path/size/sha256
    map_html_path: Optional[str] = None  # rendered folium/Leaflet trajectory map
    # --- expanded counter-UAS intelligence harvest ---
    launch_sites: list[TrackPoint] = field(default_factory=list)  # per-sortie origins
    operating_radius_m: Optional[float] = None  # range-ring constraint on the base
    recurring_origin: bool = False  # >=2 sorties from the same area (base candidate)
    mission_plan: list[TrackPoint] = field(default_factory=list)  # planned waypoints/targets
    parameters_of_interest: dict[str, str] = field(default_factory=dict)  # fence/failsafe/radio
    firmware: dict[str, str] = field(default_factory=dict)  # autopilot/version/board/hwid
    timeline: dict[str, str] = field(default_factory=dict)  # first/last UTC, duration, sorties
    imaged_locations: list[dict[str, str]] = field(default_factory=list)  # geotagged ISR media

    def merge(self, other: "AnalysisFindings") -> "AnalysisFindings":
        """Combine two findings (e.g. content + trajectory) into one."""
        return AnalysisFindings(
            launch_estimate=self.launch_estimate or other.launch_estimate,
            launch_radius_m=self.launch_radius_m
            if self.launch_radius_m is not None else other.launch_radius_m,
            target_estimate=self.target_estimate or other.target_estimate,
            confidence=max(self.confidence, other.confidence),
            media_metadata=self.media_metadata + other.media_metadata,
            payload_assessment=self.payload_assessment + other.payload_assessment,
            identifiers={**self.identifiers, **other.identifiers},
            evidence_basis=self.evidence_basis + other.evidence_basis,
            file_inventory=self.file_inventory + other.file_inventory,
            map_html_path=self.map_html_path or other.map_html_path,
            launch_sites=self.launch_sites or other.launch_sites,
            operating_radius_m=self.operating_radius_m
            if self.operating_radius_m is not None else other.operating_radius_m,
            recurring_origin=self.recurring_origin or other.recurring_origin,
            mission_plan=self.mission_plan or other.mission_plan,
            parameters_of_interest={
                **self.parameters_of_interest, **other.parameters_of_interest},
            firmware={**self.firmware, **other.firmware},
            timeline={**self.timeline, **other.timeline},
            imaged_locations=self.imaged_locations + other.imaged_locations,
        )


@dataclass
class ForensicReport:
    """Final threat-intel report bundled with its chain-of-custody appendix."""

    evidence_id: str
    findings: AnalysisFindings
    map_html_path: Optional[str] = None  # folium/Leaflet map
    pdf_path: Optional[str] = None
    custody_log: list[dict[str, str]] = field(default_factory=list)
    tool_versions: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Stage interfaces (Protocols) — concrete impls wrap verified OSS tools
# ---------------------------------------------------------------------------


@runtime_checkable
class Imager(Protocol):
    """Bit-for-bit acquisition behind a write-blocker (dc3dd / ewfacquire)."""

    def acquire(self, item: EvidenceItem, dest_dir: str) -> AcquiredImage: ...


@runtime_checkable
class HashVerifier(Protocol):
    """SHA-256 (+ optional BLAKE2) computation and cross-checking."""

    def hash_artifact(self, path: str) -> HashRecord: ...

    def verify(self, expected: HashRecord, path: str) -> bool: ...


@runtime_checkable
class ContentAnalyzer(Protocol):
    """Filesystem / carving / metadata analysis (TSK, binwalk, ExifTool)."""

    def analyze(self, image: AcquiredImage) -> AnalysisFindings: ...

    def discover_logs(self, image: AcquiredImage) -> list[str]:
        """Return candidate flight/GNSS log file paths found on the image."""
        ...


@runtime_checkable
class FlightLogParser(Protocol):
    """Parse a flight/GNSS log via a verified parser into a FlightTrack.

    Implementations dispatch by format to pymavlink (.bin/.tlog), pyulog
    (.ulg), pynmea2 (NMEA), or dji-log-parser (DJI).
    """

    def supports(self, log_path: str) -> bool: ...

    def parse(self, log_path: str) -> FlightTrack: ...


@runtime_checkable
class TrajectoryAnalyzer(Protocol):
    """Reconstruct trajectory, estimate launch/target, render a map."""

    def analyze(self, tracks: list[FlightTrack]) -> AnalysisFindings: ...

    def render_map(self, tracks: list[FlightTrack], out_html: str) -> str: ...


@runtime_checkable
class ReportBuilder(Protocol):
    """Assemble the threat-intel report + chain-of-custody appendix."""

    def build(
        self,
        evidence_id: str,
        findings: AnalysisFindings,
        custody_log: list[dict[str, str]],
    ) -> ForensicReport: ...
