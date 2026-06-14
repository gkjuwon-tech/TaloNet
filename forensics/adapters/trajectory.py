"""Trajectory reconstruction + hostile launch-site geolocation.

Consumes parsed :class:`~forensics.interfaces.FlightTrack` objects from a
non-kinetically captured hostile UAS and produces explainable
:class:`~forensics.interfaces.AnalysisFindings` for **counter-UAS target
intelligence** (proportionate self-defence against the source of the attack):

- **Hostile launch site (counter-UAS origin):** the recorded home/origin, else
  the first valid fix — the actionable geolocation of where the attack came from,
  with a CEP-like **uncertainty radius** so the authorized commander can apply
  distinction/proportionality and avoid collateral damage.
- **Intended target:** the centroid of the longest loiter/dwell (the defended
  asset the hostile UAS was aimed at), else the last fix.
- **Confidence:** a transparent geolocation heuristic — NEVER a certainty — with
  contributing factors recorded in ``evidence_basis``.

The analysis core is dependency-free (uses :mod:`forensics.geo`); only the
optional HTML map renderer pulls in **folium** (Leaflet/OSM), imported lazily.

This module produces *intelligence only*. Every engagement decision remains with
the authorized commander under the Rules of Engagement and the Law of Armed
Conflict (distinction, proportionality, precautions). Not for use against
civilians or civilian objects.
"""

from __future__ import annotations

from .. import geo
from ..interfaces import AnalysisFindings, FlightTrack, TrackPoint


class TrajectoryReconstructor:
    """Implements :class:`forensics.interfaces.TrajectoryAnalyzer`."""

    def __init__(self, loiter_radius_m: float = 60.0) -> None:
        self.loiter_radius_m = loiter_radius_m

    # -- protocol --------------------------------------------------------------
    def analyze(self, tracks: list[FlightTrack]) -> AnalysisFindings:
        findings = AnalysisFindings()
        primary = self._primary(tracks)
        if primary is None or not primary.points:
            findings.payload_assessment.append("no positional fixes recovered")
            return findings

        pts = [(p.lat, p.lon) for p in primary.points]
        launch = primary.home_position or primary.points[0]
        dwell = geo.longest_dwell(pts, self.loiter_radius_m)
        target = (
            TrackPoint(t_utc="", lat=dwell.lat, lon=dwell.lon)
            if dwell else primary.points[-1]
        )

        length_m = geo.path_length_m(pts)
        bbox = geo.bounding_box(pts)
        straight = geo.haversine_m(launch.lat, launch.lon, target.lat, target.lon)
        course = geo.bearing_deg(launch.lat, launch.lon, target.lat, target.lon)
        launch_radius = self._launch_radius_m(launch, primary.points)

        findings.launch_estimate = launch
        findings.launch_radius_m = launch_radius
        findings.target_estimate = target
        findings.confidence = self._confidence(primary, dwell is not None)
        findings.evidence_basis.extend(
            [
                f"primary track: {primary.source_format} via {primary.parser} "
                f"({len(primary.points)} fixes)",
                f"HOSTILE LAUNCH SITE (counter-UAS origin) = "
                f"{'home/origin' if primary.home_position else 'first fix'} "
                f"@ {launch.lat:.6f},{launch.lon:.6f} "
                f"(uncertainty ~{launch_radius:.0f} m)",
                f"intended target (defended asset) = {'longest loiter' if dwell else 'last fix'} "
                f"@ {target.lat:.6f},{target.lon:.6f}"
                + (f" ({dwell.sample_count} samples loitering)" if dwell else ""),
                f"ingress path ~{length_m / 1000:.2f} km; "
                f"launch->target straight-line ~{straight / 1000:.2f} km "
                f"on bearing ~{course:.0f}deg (back-azimuth ~{(course + 180) % 360:.0f}deg)",
                "correlate launch site with prior captures for recurring origin "
                "(enemy basing / pattern of life)",
            ]
        )
        if bbox:
            findings.evidence_basis.append(
                f"operating area bbox: ({bbox.min_lat:.5f},{bbox.min_lon:.5f}) "
                f"-> ({bbox.max_lat:.5f},{bbox.max_lon:.5f})"
            )
        self._altitude_note(primary, findings)
        return findings

    def render_map(self, tracks: list[FlightTrack], out_html: str) -> str:
        import folium  # lazy: MIT dependency (Leaflet/OSM)

        primary = self._primary(tracks)
        if primary is None or not primary.points:
            raise ValueError("no track points to render")
        pts = [(p.lat, p.lon) for p in primary.points]
        bbox = geo.bounding_box(pts)
        center = bbox.center if bbox else pts[0]
        fmap = folium.Map(location=list(center), zoom_start=14, tiles="OpenStreetMap")
        folium.PolyLine(pts, weight=3, opacity=0.8, color="#86855F").add_to(fmap)

        launch = primary.home_position or primary.points[0]
        radius = self._launch_radius_m(launch, primary.points)
        folium.Circle(
            [launch.lat, launch.lon], radius=radius, color="#b02828",
            fill=True, fill_opacity=0.15, tooltip="Launch-site uncertainty",
        ).add_to(fmap)
        folium.Marker(
            [launch.lat, launch.lon], tooltip="HOSTILE LAUNCH SITE (counter-UAS origin)",
            icon=folium.Icon(color="red", icon="flag"),
        ).add_to(fmap)
        dwell = geo.longest_dwell(pts, self.loiter_radius_m)
        target = (dwell.lat, dwell.lon) if dwell else (pts[-1][0], pts[-1][1])
        folium.Marker(
            list(target), tooltip="Intended target (defended asset)",
            icon=folium.Icon(color="blue", icon="screenshot"),
        ).add_to(fmap)
        if bbox:
            fmap.fit_bounds([[bbox.min_lat, bbox.min_lon], [bbox.max_lat, bbox.max_lon]])
        fmap.save(out_html)
        return out_html

    # -- helpers ---------------------------------------------------------------
    @staticmethod
    def _primary(tracks: list[FlightTrack]) -> FlightTrack | None:
        usable = [t for t in tracks if t.points]
        return max(usable, key=lambda t: len(t.points)) if usable else None

    @staticmethod
    def _launch_radius_m(launch: TrackPoint, points: list[TrackPoint]) -> float:
        """CEP-like uncertainty radius for the launch-site geolocation.

        Dispersion of the first samples about the launch estimate (the drone is
        still near its origin at takeoff). A larger radius => less precise origin
        => the commander must widen precautions / hold for better data.
        """
        head = points[: min(8, len(points))]
        spread = max(
            (geo.haversine_m(launch.lat, launch.lon, p.lat, p.lon) for p in head),
            default=0.0,
        )
        return round(max(spread, 15.0), 1)  # floor at GNSS-grade ~15 m

    @staticmethod
    def _confidence(track: FlightTrack, has_dwell: bool) -> float:
        c = 0.2
        if track.home_position is not None:
            c += 0.3
        if len(track.points) > 100:
            c += 0.2
        elif len(track.points) > 20:
            c += 0.1
        if has_dwell:
            c += 0.2
        if any(p.fix_quality for p in track.points[:5]):
            c += 0.1
        return round(min(c, 0.95), 2)  # never asserted as certainty

    @staticmethod
    def _altitude_note(track: FlightTrack, findings: AnalysisFindings) -> None:
        alts = [p.alt_m for p in track.points if p.alt_m is not None]
        if alts:
            findings.payload_assessment.append(
                f"altitude range ~{min(alts):.0f}..{max(alts):.0f} m "
                "(profile consistent with cruise+descent if a dwell/target is present)"
            )
