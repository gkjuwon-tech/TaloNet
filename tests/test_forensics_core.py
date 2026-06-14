"""Stdlib-only forensics tests: imaging, hashing, content, custody, pipeline.

These run with zero third-party dependencies installed (the pipeline test uses a
fake parser and a fake report builder), so they always execute in CI.
"""

import os
import tempfile
import unittest

from forensics import (
    AnalysisFindings,
    ChainOfCustody,
    EvidenceItem,
    FlightTrack,
    ForensicPipeline,
    ForensicReport,
    IntegrityError,
    TrackPoint,
)
from forensics.adapters.content import FileSystemContentAnalyzer
from forensics.adapters.hashing import Sha256Verifier
from forensics.adapters.imaging import DiskImager
from forensics.adapters.report import format_text_report
from forensics.adapters.trajectory import TrajectoryReconstructor


def _make_card(root):
    """A synthetic SD card: an NMEA-named log + a config file with identifiers."""
    with open(os.path.join(root, "GPSLOG.nmea"), "w") as fh:
        fh.write("$GPGGA,120000.00,3730.0000,N,12700.0000,E,1,09,0.9,120.0,M,0,M,,*5C\n")
    with open(os.path.join(root, "config.txt"), "w") as fh:
        fh.write("serial: ABCD1234\nFCC ID: 2AXYZ-DRONE9\n")


class TestHashing(unittest.TestCase):
    def test_hash_and_verify(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f.bin")
            with open(p, "wb") as fh:
                fh.write(b"taloNet" * 1000)
            v = Sha256Verifier()
            rec = v.hash_artifact(p)
            self.assertEqual(len(rec.sha256), 64)
            self.assertTrue(v.verify(rec, p))
            with open(p, "ab") as fh:
                fh.write(b"x")
            self.assertFalse(v.verify(rec, p))


class TestImaging(unittest.TestCase):
    def test_raw_image_verified(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "device.img")
            with open(src, "wb") as fh:
                fh.write(os.urandom(4096))
            img = DiskImager().acquire(
                EvidenceItem("EV1", "", "op", "4K device", source_path=src),
                os.path.join(d, "work"),
            )
            self.assertEqual(img.image_format, "raw")
            self.assertTrue(img.verified())
            self.assertEqual(img.size_bytes, 4096)

    def test_logical_image_verified_with_extracted_root(self):
        with tempfile.TemporaryDirectory() as d:
            card = os.path.join(d, "card")
            os.makedirs(card)
            _make_card(card)
            img = DiskImager().acquire(
                EvidenceItem("EV2", "", "op", "card", source_path=card),
                os.path.join(d, "work"),
            )
            self.assertEqual(img.image_format, "logical-tree")
            self.assertTrue(img.verified())
            self.assertTrue(os.path.isdir(img.extracted_root))


class TestContentAnalyzer(unittest.TestCase):
    def test_inventory_logs_and_identifiers(self):
        with tempfile.TemporaryDirectory() as d:
            card = os.path.join(d, "card")
            os.makedirs(card)
            _make_card(card)
            img = DiskImager().acquire(
                EvidenceItem("EV3", "", "op", "card", source_path=card),
                os.path.join(d, "work"),
            )
            analyzer = FileSystemContentAnalyzer(exiftool=False)
            findings = analyzer.analyze(img)
            self.assertEqual(len(findings.file_inventory), 2)
            self.assertEqual(findings.identifiers.get("serial"), "ABCD1234")
            self.assertEqual(findings.identifiers.get("fcc_id"), "2AXYZ-DRONE9")
            logs = analyzer.discover_logs(img)
            self.assertTrue(any(p.endswith(".nmea") for p in logs))


class TestChainOfCustody(unittest.TestCase):
    def test_append_verify_and_tamper(self):
        coc = ChainOfCustody("EV4")
        coc.record("op-A", "intake", "card recovered", witness="op-B")
        coc.record("examiner", "imaging", "dc3dd raw + sha256")
        self.assertTrue(coc.verify())
        self.assertEqual(len(coc.events), 2)
        coc.events[0].detail = "TAMPERED"
        self.assertFalse(coc.verify())


class TestTextReport(unittest.TestCase):
    def test_text_report_sections(self):
        findings = AnalysisFindings(
            launch_estimate=TrackPoint("", 37.5, 127.0),
            target_estimate=TrackPoint("", 37.6, 127.1),
            confidence=0.7,
            identifiers={"serial": "ABCD1234"},
        )
        text = format_text_report("EV5", findings, [{"timestamp": "t", "action": "intake",
                                  "actor": "op", "detail": "x"}])
        self.assertIn("COUNTER-UAS TARGET INTEL", text)
        self.assertIn("HOSTILE LAUNCH SITE", text)
        self.assertIn("INTELLIGENCE PROVENANCE", text)
        self.assertIn("ABCD1234", text)
        self.assertIn("Geo conf", text)


# -- fakes for a dependency-free end-to-end pipeline run ----------------------
class _FakeNmeaParser:
    def supports(self, log_path):
        return log_path.endswith(".nmea")

    def parse(self, log_path):
        pts = [TrackPoint("", 37.5 + 0.001 * i, 127.0) for i in range(10)]
        pts += [TrackPoint("", 37.51, 127.0)] * 8  # loiter
        tr = FlightTrack("nmea-0183", "fake")
        tr.points = pts
        tr.home_position = pts[0]
        return tr


class _FakeReporter:
    def build(self, evidence_id, findings, custody_log):
        return ForensicReport(evidence_id, findings, custody_log=custody_log)


class TestPipeline(unittest.TestCase):
    def test_end_to_end_with_fakes(self):
        with tempfile.TemporaryDirectory() as d:
            card = os.path.join(d, "card")
            os.makedirs(card)
            _make_card(card)
            coc = ChainOfCustody("EV6")
            pipeline = ForensicPipeline(
                imager=DiskImager(),
                hasher=Sha256Verifier(),
                content=FileSystemContentAnalyzer(exiftool=False),
                log_parsers=[_FakeNmeaParser()],
                trajectory=TrajectoryReconstructor(),
                reporter=_FakeReporter(),
            )
            item = EvidenceItem("EV6", "", "op-A", "card", source_path=card)
            report = pipeline.run(item, coc, os.path.join(d, "work"))
            self.assertEqual(report.evidence_id, "EV6")
            self.assertIsNotNone(report.findings.launch_estimate)
            self.assertIsNotNone(report.findings.target_estimate)
            self.assertGreater(report.findings.confidence, 0.0)
            steps = [e["action"] for e in coc.to_log()]
            self.assertEqual(
                steps,
                ["intake", "imaging", "hash_verify", "content",
                 "flight_log", "trajectory", "report"],
            )
            self.assertTrue(coc.verify())

    def test_integrity_gate_stops_on_hash_mismatch(self):
        from forensics.interfaces import AcquiredImage, HashRecord

        class _BadImager:
            def acquire(self, item, dest):
                return AcquiredImage(item.evidence_id, "x.dd", "raw",
                                     HashRecord("aaaa"), HashRecord("bbbb"),
                                     "fake", "none")

        class _Content:
            def analyze(self, image):
                return AnalysisFindings()

            def discover_logs(self, image):
                return []

        class _NoReport:
            def build(self, *a):
                raise AssertionError("report must not run after integrity failure")

        pipeline = ForensicPipeline(_BadImager(), Sha256Verifier(), _Content(),
                                    [], TrajectoryReconstructor(), _NoReport())
        with self.assertRaises(IntegrityError):
            with tempfile.TemporaryDirectory() as d:
                pipeline.run(EvidenceItem("EV7", "", "op", "d", source_path="/x"),
                             ChainOfCustody("EV7"), d)


if __name__ == "__main__":
    unittest.main()
