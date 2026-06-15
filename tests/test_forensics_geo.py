"""Tests for the dependency-free geospatial helpers (always run)."""

import unittest

from forensics import geo


class TestGeo(unittest.TestCase):
    def test_haversine_one_degree_latitude(self):
        # one degree of latitude is ~111.2 km anywhere
        d = geo.haversine_m(0.0, 0.0, 1.0, 0.0)
        self.assertAlmostEqual(d, 111195, delta=200)

    def test_haversine_zero(self):
        self.assertEqual(geo.haversine_m(37.5, 127.0, 37.5, 127.0), 0.0)

    def test_bearing_cardinal(self):
        self.assertAlmostEqual(geo.bearing_deg(0, 0, 1, 0), 0.0, delta=0.5)  # north
        self.assertAlmostEqual(geo.bearing_deg(0, 0, 0, 1), 90.0, delta=0.5)  # east

    def test_bounding_box_and_center(self):
        bb = geo.bounding_box([(1.0, 2.0), (3.0, 6.0), (2.0, 4.0)])
        self.assertEqual((bb.min_lat, bb.max_lat, bb.min_lon, bb.max_lon), (1.0, 3.0, 2.0, 6.0))
        self.assertEqual(bb.center, (2.0, 4.0))

    def test_bounding_box_empty(self):
        self.assertIsNone(geo.bounding_box([]))

    def test_path_length_monotonic(self):
        pts = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]
        self.assertAlmostEqual(geo.path_length_m(pts), 2 * geo.haversine_m(0, 0, 0, 1), delta=1)

    def test_longest_dwell_detects_loiter(self):
        moving = [(0.0 + 0.01 * i, 0.0) for i in range(10)]
        loiter = [(0.2, 0.2)] * 8  # 8 samples clustered tightly
        d = geo.longest_dwell(moving + loiter, radius_m=60.0)
        self.assertIsNotNone(d)
        self.assertGreaterEqual(d.sample_count, 8)
        self.assertAlmostEqual(d.lat, 0.2, delta=1e-6)
        self.assertAlmostEqual(d.lon, 0.2, delta=1e-6)

    def test_longest_dwell_too_few_points(self):
        self.assertIsNone(geo.longest_dwell([(0.0, 0.0)]))


if __name__ == "__main__":
    unittest.main()
