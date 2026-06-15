"""Flight / GNSS log parsers backed by verified open-source libraries.

Each parser implements :class:`forensics.interfaces.FlightLogParser` and wraps a
real, audited parser — never a hand-rolled binary decoder:

- :class:`ArduPilotLogParser` — ArduPilot DataFlash ``.bin`` and MAVLink ``.tlog``
  via **pymavlink** (``ArduPilot/pymavlink``, LGPL-3.0).
- :class:`Px4UlogParser` — PX4 ULog ``.ulg`` via **pyulog** (``PX4/pyulog``, BSD-3).
- :class:`NmeaLogParser` — NMEA 0183 via **pynmea2** (``Knio/pynmea2``, MIT).
- :class:`DjiLogParser` — DJI flight records via the **dji-log-parser** CLI
  (``lvauvillier/dji-log-parser``, MIT); optional, sniffed + delegated.
- :class:`LogParserRouter` — dispatches a path to the first parser that supports it.

Heavy libs are imported lazily inside ``parse`` so importing this module costs
nothing. If a library is missing, ``parse`` raises a clear, actionable error.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

from ..interfaces import FlightTrack, TrackPoint

# GPS time -> UTC conversion (DataFlash GPS week/ms)
_GPS_EPOCH = datetime(1980, 1, 6, tzinfo=timezone.utc)
_GPS_LEAP_SECONDS = 18  # valid 2017-01 onward; recorded as an approximation


def _gps_to_utc(week: float, ms: float) -> str:
    t = _GPS_EPOCH + timedelta(weeks=week, milliseconds=ms)
    return (t - timedelta(seconds=_GPS_LEAP_SECONDS)).isoformat()


def _usec_to_utc(usec: int) -> str:
    return datetime.fromtimestamp(usec / 1e6, tz=timezone.utc).isoformat()


# Parameters worth pulling for counter-UAS intelligence (prefix match):
# geofence (their boundary / protected AO), failsafe/RTL behaviour, battery
# capacity (endurance -> range ring), airframe class, MAV/GCS network IDs, radio
# protocol, cruise speed. Matched case-insensitively by prefix.
_PARAM_INTEL_PREFIXES = (
    "FENCE", "RTL_ALT", "RTL_SPEED", "FS_", "BATT_CAPACITY", "BATT_LOW",
    "FRAME_CLASS", "FRAME_TYPE", "Q_ENABLE", "SYSID_THISMAV", "SYSID_MYGCS",
    "SERIAL1_PROTOCOL", "SERIAL2_PROTOCOL", "WPNAV_SPEED", "GPS_TYPE",
)


def _param_of_interest(name: str) -> bool:
    up = name.upper()
    return any(up.startswith(p) for p in _PARAM_INTEL_PREFIXES)


# ---------------------------------------------------------------------------
# ArduPilot — pymavlink
# ---------------------------------------------------------------------------
class ArduPilotLogParser:
    """ArduPilot DataFlash ``.bin`` / MAVLink ``.tlog`` via pymavlink."""

    exts = (".bin", ".tlog")

    def supports(self, log_path: str) -> bool:
        return log_path.lower().endswith(self.exts)

    def parse(self, log_path: str) -> FlightTrack:
        from pymavlink import mavutil  # lazy: LGPL-3.0 dependency

        is_tlog = log_path.lower().endswith(".tlog")
        mlog = mavutil.mavlink_connection(log_path, robust_parsing=True)
        track = FlightTrack(
            source_format="mavlink-tlog" if is_tlog else "ardupilot-bin",
            parser=f"pymavlink {getattr(mavutil, '__version__', '')}".strip(),
        )
        if is_tlog:
            self._parse_tlog(mlog, track)
        else:
            self._parse_dataflash(mlog, track)
        track.notes.append(f"{len(track.points)} fixes parsed via pymavlink")
        return track

    def _parse_dataflash(self, mlog, track: FlightTrack) -> None:
        while True:
            m = mlog.recv_match(
                type=["GPS", "ORGN", "PARM", "CMD", "MSG", "VER", "BAT"]
            )
            if m is None:
                break
            mtype = m.get_type()
            if mtype == "PARM":
                if _param_of_interest(m.Name):
                    track.params[m.Name] = f"{m.Value:g}"
                continue
            if mtype == "CMD":
                track.mission.append(
                    TrackPoint(
                        t_utc="", lat=m.Lat * 1e-7 if abs(m.Lat) > 1000 else float(m.Lat),
                        lon=m.Lng * 1e-7 if abs(m.Lng) > 1000 else float(m.Lng),
                        alt_m=float(getattr(m, "Alt", 0)),
                        fix_quality=f"cmd{getattr(m, 'CId', '?')}",
                    )
                )
                continue
            if mtype == "MSG":
                txt = str(getattr(m, "Message", ""))
                if any(k in txt for k in ("Ardu", "PX4", "ChibiOS", "FMUv", "CubeOrange")):
                    track.firmware.setdefault("banner", txt)
                continue
            if mtype == "VER":
                track.firmware["board"] = str(getattr(m, "BU", getattr(m, "board_type", "")))
                gh = getattr(m, "GH", getattr(m, "fw_hash", ""))
                if gh:
                    track.firmware["git"] = str(gh)
                continue
            if mtype == "BAT":
                used = getattr(m, "CurrTot", None)
                if used:
                    track.energy_mah = max(track.energy_mah or 0.0, float(used))
                continue
            if mtype == "ORGN":
                # Type 0 = origin, 1 = set-home
                pt = TrackPoint(
                    t_utc="", lat=m.Lat * 1e-7, lon=m.Lng * 1e-7,
                    alt_m=getattr(m, "Alt", 0) * 1e-2,
                )
                if getattr(m, "Type", 1) == 1 or track.home_position is None:
                    track.home_position = pt
                continue
            if getattr(m, "Status", 0) < 3:  # require 3D fix
                continue
            t = (
                _gps_to_utc(m.GWk, m.GMS)
                if getattr(m, "GWk", 0) else f"T+{m.TimeUS / 1e6:.3f}s"
            )
            track.points.append(
                TrackPoint(
                    t_utc=t, lat=m.Lat * 1e-7, lon=m.Lng * 1e-7, alt_m=float(m.Alt),
                    speed_ms=float(getattr(m, "Spd", 0.0)),
                    fix_quality=f"{getattr(m, 'Status', '')}D/{getattr(m, 'NSats', '?')}sat",
                )
            )
        if track.home_position is None and track.points:
            track.home_position = track.points[0]
        if track.energy_mah is None and "BATT_CAPACITY" in track.params:
            track.energy_mah = float(track.params["BATT_CAPACITY"])

    def _parse_tlog(self, mlog, track: FlightTrack) -> None:
        while True:
            m = mlog.recv_match(
                type=["GLOBAL_POSITION_INT", "GPS_RAW_INT", "HOME_POSITION",
                      "PARAM_VALUE", "MISSION_ITEM_INT", "MISSION_ITEM",
                      "STATUSTEXT", "AUTOPILOT_VERSION", "BATTERY_STATUS"]
            )
            if m is None:
                break
            mtype = m.get_type()
            if mtype == "HOME_POSITION":
                track.home_position = TrackPoint(
                    t_utc="", lat=m.latitude * 1e-7, lon=m.longitude * 1e-7,
                    alt_m=m.altitude * 1e-3,
                )
                continue
            if mtype == "PARAM_VALUE":
                name = m.param_id
                name = name.decode() if isinstance(name, bytes) else str(name)
                name = name.split("\x00")[0]
                if _param_of_interest(name):
                    track.params[name] = f"{m.param_value:g}"
                continue
            if mtype in ("MISSION_ITEM_INT", "MISSION_ITEM"):
                scale = 1e-7 if mtype == "MISSION_ITEM_INT" else 1.0
                track.mission.append(
                    TrackPoint(
                        t_utc="", lat=m.x * scale, lon=m.y * scale, alt_m=float(m.z),
                        fix_quality=f"cmd{getattr(m, 'command', '?')}",
                    )
                )
                continue
            if mtype == "STATUSTEXT":
                txt = str(getattr(m, "text", ""))
                if any(k in txt for k in ("Ardu", "PX4", "ChibiOS", "FMUv", "Cube")):
                    track.firmware.setdefault("banner", txt)
                continue
            if mtype == "AUTOPILOT_VERSION":
                track.firmware["flight_sw"] = str(getattr(m, "flight_sw_version", ""))
                track.firmware["board"] = str(getattr(m, "board_version", ""))
                continue
            if mtype == "BATTERY_STATUS":
                used = getattr(m, "current_consumed", None)
                if used and used > 0:
                    track.energy_mah = max(track.energy_mah or 0.0, float(used))
                continue
            if mtype == "GPS_RAW_INT":
                if getattr(m, "fix_type", 0) < 3:
                    continue
                t = _usec_to_utc(m.time_usec) if getattr(m, "time_usec", 0) else ""
                track.points.append(
                    TrackPoint(
                        t_utc=t, lat=m.lat * 1e-7, lon=m.lon * 1e-7, alt_m=m.alt * 1e-3,
                        speed_ms=getattr(m, "vel", 0) * 1e-2,
                        fix_quality=f"fix{m.fix_type}/{getattr(m, 'satellites_visible', '?')}sat",
                    )
                )
            else:  # GLOBAL_POSITION_INT
                track.points.append(
                    TrackPoint(
                        t_utc="", lat=m.lat * 1e-7, lon=m.lon * 1e-7, alt_m=m.alt * 1e-3,
                        fix_quality="global_position",
                    )
                )
        if track.home_position is None and track.points:
            track.home_position = track.points[0]
        if track.energy_mah is None and "BATT_CAPACITY" in track.params:
            track.energy_mah = float(track.params["BATT_CAPACITY"])


# ---------------------------------------------------------------------------
# PX4 — pyulog
# ---------------------------------------------------------------------------
class Px4UlogParser:
    """PX4 ULog ``.ulg`` via pyulog."""

    def supports(self, log_path: str) -> bool:
        return log_path.lower().endswith((".ulg", ".ulog"))

    def parse(self, log_path: str) -> FlightTrack:
        from pyulog import ULog  # lazy: BSD-3 dependency

        ulog = ULog(log_path)
        track = FlightTrack(source_format="px4-ulog", parser="pyulog")
        gps = self._dataset(ulog, "vehicle_gps_position")
        if gps is not None:
            self._from_gps(gps, track)
        else:
            glob = self._dataset(ulog, "vehicle_global_position")
            if glob is not None:
                self._from_global(glob, track)
        home = self._dataset(ulog, "home_position")
        if home is not None and len(home.data.get("lat", [])):
            track.home_position = TrackPoint(
                t_utc="", lat=float(home.data["lat"][0]),
                lon=float(home.data["lon"][0]),
                alt_m=float(home.data.get("alt", [0])[0]),
            )
        elif track.points:
            track.home_position = track.points[0]
        track.notes.append(f"{len(track.points)} fixes parsed via pyulog")
        return track

    @staticmethod
    def _dataset(ulog, name: str):
        for d in ulog.data_list:
            if d.name == name:
                return d
        return None

    def _from_gps(self, gps, track: FlightTrack) -> None:
        d = gps.data
        n = len(d.get("lat", []))
        for i in range(n):
            if int(d.get("fix_type", [0] * n)[i]) < 3:
                continue
            utc = d.get("time_utc_usec", [0] * n)[i]
            t = _usec_to_utc(int(utc)) if utc else f"T+{d['timestamp'][i] / 1e6:.3f}s"
            track.points.append(
                TrackPoint(
                    t_utc=t, lat=d["lat"][i] * 1e-7, lon=d["lon"][i] * 1e-7,
                    alt_m=d["alt"][i] * 1e-3,
                    speed_ms=float(d.get("vel_m_s", [0] * n)[i]),
                    fix_quality=f"fix{int(d.get('fix_type', [0] * n)[i])}/"
                    f"{int(d.get('satellites_used', [0] * n)[i])}sat",
                )
            )

    def _from_global(self, glob, track: FlightTrack) -> None:
        d = glob.data
        n = len(d.get("lat", []))
        for i in range(n):
            track.points.append(
                TrackPoint(
                    t_utc=f"T+{d['timestamp'][i] / 1e6:.3f}s",
                    lat=float(d["lat"][i]), lon=float(d["lon"][i]),
                    alt_m=float(d.get("alt", [0] * n)[i]),
                    fix_quality="global_position",
                )
            )


# ---------------------------------------------------------------------------
# NMEA 0183 — pynmea2
# ---------------------------------------------------------------------------
class NmeaLogParser:
    """NMEA 0183 sentences (GGA/RMC) via pynmea2."""

    def supports(self, log_path: str) -> bool:
        if log_path.lower().endswith(".nmea"):
            return True
        if log_path.lower().endswith((".log", ".txt")):
            return self._sniff(log_path)
        return False

    @staticmethod
    def _sniff(path: str) -> bool:
        try:
            with open(path, "r", errors="ignore") as fh:
                for _ in range(50):
                    line = fh.readline()
                    if not line:
                        break
                    if line.startswith(("$GP", "$GN", "$GL", "$GA")):
                        return True
        except OSError:
            return False
        return False

    def parse(self, log_path: str) -> FlightTrack:
        import pynmea2  # lazy: MIT dependency

        track = FlightTrack(
            source_format="nmea-0183", parser=f"pynmea2 {pynmea2.__version__}"
        )
        last_date = None
        with open(log_path, "r", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("$"):
                    continue
                try:
                    msg = pynmea2.parse(line)
                except pynmea2.ParseError:
                    continue
                stype = msg.sentence_type if hasattr(msg, "sentence_type") else ""
                if stype == "RMC" and getattr(msg, "datestamp", None):
                    last_date = msg.datestamp
                lat = getattr(msg, "latitude", None)
                lon = getattr(msg, "longitude", None)
                if not lat and not lon:
                    continue
                if stype == "GGA" and int(getattr(msg, "gps_qual", 0) or 0) == 0:
                    continue
                t = ""
                ts = getattr(msg, "timestamp", None)
                if ts is not None:
                    t = (
                        datetime.combine(last_date, ts, tzinfo=timezone.utc).isoformat()
                        if last_date else ts.isoformat()
                    )
                track.points.append(
                    TrackPoint(
                        t_utc=t, lat=float(lat), lon=float(lon),
                        alt_m=float(getattr(msg, "altitude", 0) or 0)
                        if stype == "GGA" else None,
                        speed_ms=(float(msg.spd_over_grnd) * 0.514444)
                        if stype == "RMC" and getattr(msg, "spd_over_grnd", None) else None,
                        fix_quality=stype,
                    )
                )
        if track.points:
            track.home_position = track.points[0]
        track.notes.append(f"{len(track.points)} fixes parsed via pynmea2")
        return track


# ---------------------------------------------------------------------------
# DJI — dji-log-parser CLI (optional)
# ---------------------------------------------------------------------------
class DjiLogParser:
    """DJI flight records via the dji-log-parser CLI (optional, sniffed)."""

    cli_names = ("dji-log", "dji-log-parser")

    def _cli(self) -> str | None:
        for name in self.cli_names:
            found = shutil.which(name)
            if found:
                return found
        return None

    def supports(self, log_path: str) -> bool:
        if not log_path.lower().endswith((".txt", ".dat")):
            return False
        try:
            with open(log_path, "rb") as fh:
                head = fh.read(16)
        except OSError:
            return False
        # DJI flight records start with a version/record header, not NMEA '$'
        return self._cli() is not None and not head.startswith(b"$")

    def parse(self, log_path: str) -> FlightTrack:
        cli = self._cli()
        if cli is None:
            raise RuntimeError(
                "DJI parsing requires the dji-log-parser CLI "
                "(github.com/lvauvillier/dji-log-parser). Install it and ensure "
                "'dji-log' is on PATH; newer encrypted logs also need a DJI API key."
            )
        res = subprocess.run(
            [cli, log_path, "--json"], capture_output=True, text=True, check=True
        )
        data = json.loads(res.stdout)
        track = FlightTrack(source_format="dji", parser=os.path.basename(cli))
        for rec in data.get("frames", data.get("records", [])):
            osd = rec.get("osd", rec)
            lat, lon = osd.get("latitude"), osd.get("longitude")
            if lat is None or lon is None:
                continue
            track.points.append(
                TrackPoint(
                    t_utc=str(rec.get("time", "")), lat=float(lat), lon=float(lon),
                    alt_m=osd.get("height"), speed_ms=osd.get("xSpeed"),
                    fix_quality=f"{osd.get('gpsLevel', '?')}gps",
                )
            )
        if track.points:
            track.home_position = track.points[0]
        track.notes.append(f"{len(track.points)} fixes parsed via {os.path.basename(cli)}")
        return track


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
class LogParserRouter:
    """Dispatch a log path to the first registered parser that supports it."""

    def __init__(self, parsers: list | None = None) -> None:
        self.parsers = parsers or [
            ArduPilotLogParser(),
            Px4UlogParser(),
            NmeaLogParser(),
            DjiLogParser(),
        ]

    def supports(self, log_path: str) -> bool:
        return any(p.supports(log_path) for p in self.parsers)

    def select(self, log_path: str):
        for p in self.parsers:
            if p.supports(log_path):
                return p
        return None

    def parse(self, log_path: str) -> FlightTrack:
        parser = self.select(log_path)
        if parser is None:
            raise ValueError(f"no verified parser supports {log_path}")
        return parser.parse(log_path)
