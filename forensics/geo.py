"""Pure-stdlib geospatial helpers for trajectory analysis.

No third-party dependency: great-circle distance, bearing, bounding box, total
path length, and a simple loiter/dwell detector used to estimate the intended
target area from a recovered flight track. Kept dependency-free so it runs on
the embedded appliance and is unit-testable without a GIS stack.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_008.8  # IUGG mean Earth radius


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points, in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great-circle bearing from point 1 to point 2, degrees [0,360)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


@dataclass
class BoundingBox:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.min_lat + self.max_lat) / 2, (self.min_lon + self.max_lon) / 2)


def bounding_box(points: list[tuple[float, float]]) -> BoundingBox | None:
    """Axis-aligned WGS84 bounding box of (lat, lon) points."""
    if not points:
        return None
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return BoundingBox(min(lats), min(lons), max(lats), max(lons))


def path_length_m(points: list[tuple[float, float]]) -> float:
    """Total great-circle path length over an ordered list of (lat, lon)."""
    return sum(
        haversine_m(*points[i], *points[i + 1]) for i in range(len(points) - 1)
    )


@dataclass
class Dwell:
    """A region where the track lingered (candidate loiter / target area)."""

    lat: float
    lon: float
    start_index: int
    end_index: int
    span: int  # number of consecutive samples in the dwell

    @property
    def sample_count(self) -> int:
        return self.span


def longest_dwell(
    points: list[tuple[float, float]], radius_m: float = 60.0, min_span: int = 3
) -> Dwell | None:
    """Find the longest run of consecutive samples staying within ``radius_m``.

    A simple, explainable loiter detector: slides an anchor and counts how long
    the track remains within ``radius_m`` of it. The longest such run is the
    strongest "hovered here" signal — a candidate target/observation point.
    Returns ``None`` if there are too few points or no run reaches ``min_span``
    (so a steadily-moving track is not mistaken for a loiter).
    """
    if len(points) < 3:
        return None
    best: Dwell | None = None
    i = 0
    n = len(points)
    while i < n:
        anchor = points[i]
        j = i + 1
        while j < n and haversine_m(*anchor, *points[j]) <= radius_m:
            j += 1
        span = j - i
        if best is None or span > best.span:
            # centroid of the dwell run
            run = points[i:j]
            clat = sum(p[0] for p in run) / len(run)
            clon = sum(p[1] for p in run) / len(run)
            best = Dwell(clat, clon, i, j - 1, span)
        i = j if j > i + 1 else i + 1
    return best if best is not None and best.span >= min_span else None
