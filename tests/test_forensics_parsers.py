"""Verified-OSS parser/report tests, skipped when the library is absent.

These exercise the real adapters (pymavlink, pynmea2, fpdf2). They are guarded
with ``skipUnless`` so CI (which installs no forensic deps) stays green while the
tests run fully wherever the libraries are present (e.g. the appliance image or
a dev box with ``requirements-forensics.txt`` installed).
"""

import importlib.util
import os
import struct
import tempfile
import unittest

from forensics.adapters.flightlog import (
    ArduPilotLogParser,
    LogParserRouter,
    NmeaLogParser,
)

HAVE_PYMAVLINK = importlib.util.find_spec("pymavlink") is not None
HAVE_PYNMEA2 = importlib.util.find_spec("pynmea2") is not None
HAVE_FPDF = importlib.util.find_spec("fpdf") is not None


def _write_nmea(path):
    lat0, lon0 = 37.5, 127.0
    with open(path, "w") as fh:
        for i in range(20):
            la = lat0 + 0.0008 * min(i, 12)
            lo = lon0 + 0.0010 * min(i, 12)
            lad, lam = int(la), (la - int(la)) * 60
            lod, lom = int(lo), (lo - int(lo)) * 60
            body = (f"GPGGA,12{i // 60:02d}{i % 60:02d}.00,"
                    f"{lad:02d}{lam:07.4f},N,{lod:03d}{lom:07.4f},E,1,09,0.9,120.0,M,0,M,,")
            cs = 0
            for ch in body:
                cs ^= ord(ch)
            fh.write(f"${body}*{cs:02X}\n")


def _write_tlog(path, rich=False):
    from pymavlink.dialects.v20 import common as mav2

    mav = mav2.MAVLink(None, srcSystem=1, srcComponent=1)
    base = 1_700_000_000_000_000
    with open(path, "wb") as fh:
        fh.write(struct.pack(">Q", base) + mav2.MAVLink_home_position_message(
            375000000, 1270000000, 120000, 0, 0, 0, [0] * 4, 0, 0, 0).pack(mav))
        if rich:
            fh.write(struct.pack(">Q", base) + mav2.MAVLink_statustext_message(
                6, b"ArduCopter V4.5.7 (e1b4f6c2)").pack(mav))
            for name, val in [(b"FENCE_RADIUS", 300.0), (b"BATT_CAPACITY", 22000.0),
                              (b"WPNAV_SPEED", 1200.0), (b"SYSID_MYGCS", 255.0)]:
                fh.write(struct.pack(">Q", base) + mav2.MAVLink_param_value_message(
                    name, val, 9, 4, 0).pack(mav))
            for seq, (la, lo, cmd) in enumerate(
                    [(375050000, 1270060000, 16), (375088000, 1270110000, 17)]):
                fh.write(struct.pack(">Q", base) + mav2.MAVLink_mission_item_int_message(
                    1, 1, seq, 0, cmd, 0, 1, 0, 0, 0, 0, la, lo, 120.0, 0).pack(mav))
        for i in range(30):
            lat, lon = 375000000 + i * 8000, 1270000000 + i * 10000
            fh.write(struct.pack(">Q", base + i * 1_000_000)
                     + mav2.MAVLink_gps_raw_int_message(
                         base + i * 1_000_000, 3, lat, lon, 120000,
                         100, 100, 500, 9000, 11).pack(mav))


class TestRouting(unittest.TestCase):
    def test_supports_dispatch(self):
        router = LogParserRouter()
        self.assertIsInstance(router.select("x.bin"), ArduPilotLogParser)
        self.assertTrue(ArduPilotLogParser().supports("a.tlog"))
        self.assertFalse(ArduPilotLogParser().supports("a.ulg"))

    def test_unsupported_raises(self):
        with self.assertRaises(ValueError):
            LogParserRouter([]).parse("x.unknown")


@unittest.skipUnless(HAVE_PYNMEA2, "pynmea2 not installed")
class TestNmea(unittest.TestCase):
    def test_parse_nmea(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "log.nmea")
            _write_nmea(p)
            track = NmeaLogParser().parse(p)
            self.assertEqual(track.source_format, "nmea-0183")
            self.assertGreaterEqual(len(track.points), 15)
            self.assertAlmostEqual(track.points[0].lat, 37.5, delta=1e-3)


@unittest.skipUnless(HAVE_PYMAVLINK, "pymavlink not installed")
class TestArduPilotTlog(unittest.TestCase):
    def test_parse_tlog(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.tlog")
            _write_tlog(p)
            track = ArduPilotLogParser().parse(p)
            self.assertEqual(track.source_format, "mavlink-tlog")
            self.assertEqual(len(track.points), 30)
            self.assertIsNotNone(track.home_position)
            self.assertAlmostEqual(track.home_position.lat, 37.5, delta=1e-4)
            self.assertTrue(track.points[0].t_utc)  # UTC derived from time_usec

    def test_expanded_intel_harvest(self):
        from forensics.adapters.trajectory import TrajectoryReconstructor

        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "rich.tlog")
            _write_tlog(p, rich=True)
            track = ArduPilotLogParser().parse(p)
            # parameters of interest, mission plan, firmware harvested
            self.assertEqual(track.params.get("FENCE_RADIUS"), "300")
            self.assertEqual(track.params.get("BATT_CAPACITY"), "22000")
            self.assertEqual(len(track.mission), 2)
            self.assertIn("banner", track.firmware)
            self.assertEqual(track.energy_mah, 22000.0)  # from BATT_CAPACITY fallback
            # synthesized into findings
            findings = TrajectoryReconstructor().analyze([track])
            self.assertEqual(len(findings.mission_plan), 2)
            self.assertIn("FENCE_RADIUS", findings.parameters_of_interest)
            self.assertTrue(findings.firmware)
            self.assertGreater(findings.operating_radius_m, 0)
            self.assertEqual(findings.timeline.get("sorties"), "1")


@unittest.skipUnless(HAVE_FPDF, "fpdf2 not installed")
class TestPdfReport(unittest.TestCase):
    def test_build_pdf(self):
        from forensics.adapters.report import PdfReportBuilder
        from forensics.interfaces import AnalysisFindings, TrackPoint

        with tempfile.TemporaryDirectory() as d:
            findings = AnalysisFindings(
                launch_estimate=TrackPoint("", 37.5, 127.0),
                target_estimate=TrackPoint("", 37.6, 127.1),
                confidence=0.7,
                evidence_basis=["primary track: nmea via pynmea2 (20 fixes)"],
            )
            report = PdfReportBuilder(out_dir=d).build(
                "EV-PDF", findings,
                [{"timestamp": "t", "action": "intake", "actor": "op", "detail": "x"}],
            )
            self.assertTrue(os.path.exists(report.pdf_path))
            self.assertGreater(os.path.getsize(report.pdf_path), 800)


if __name__ == "__main__":
    unittest.main()
