import unittest

from defense.gnss.spoof_detection import (
    ClockJumpDetector,
    Cn0Monitor,
    GpsGlitchGate,
    InnovationGate,
    MultiConstellationCrossCheck,
    SpoofingDetector,
)


class GlitchGateTest(unittest.TestCase):
    def test_consistent_motion_accepted(self):
        gate = GpsGlitchGate()
        gate.update(0.0, [0, 0, 0], [10, 0, 0])
        r = gate.update(1.0, [10, 0, 0], [10, 0, 0])  # exactly where velocity predicts
        self.assertFalse(r.suspicious)

    def test_teleport_rejected(self):
        gate = GpsGlitchGate()
        gate.update(0.0, [0, 0, 0], [0, 0, 0])
        r = gate.update(1.0, [500, 0, 0], [0, 0, 0])  # 500 m jump in 1 s
        self.assertTrue(r.suspicious)


class InnovationGateTest(unittest.TestCase):
    def test_small_innovation_ok(self):
        r = InnovationGate(gate_sigma=5.0).check([0.5, -0.3], [1.0, 1.0])
        self.assertFalse(r.suspicious)

    def test_large_innovation_flagged(self):
        r = InnovationGate(gate_sigma=5.0).check([50.0, 40.0], [1.0, 1.0])
        self.assertTrue(r.suspicious)


class Cn0Test(unittest.TestCase):
    def test_strong_uniform_flags_spoof(self):
        spoof, jam = Cn0Monitor().check([53.0, 53.2, 52.9, 53.1])
        self.assertTrue(spoof.suspicious)
        self.assertFalse(jam.suspicious)

    def test_collapse_flags_jam(self):
        spoof, jam = Cn0Monitor().check([20.0, 19.0, 22.0])
        self.assertTrue(jam.suspicious)
        self.assertFalse(spoof.suspicious)

    def test_normal_constellation_clean(self):
        spoof, jam = Cn0Monitor().check([45.0, 38.0, 50.0, 33.0, 47.0])
        self.assertFalse(spoof.suspicious)
        self.assertFalse(jam.suspicious)


class ClockJumpTest(unittest.TestCase):
    def test_jump_flagged(self):
        d = ClockJumpDetector(max_drift_mps=50.0)
        d.update(0.0, 0.0)
        r = d.update(1.0, 1000.0)
        self.assertTrue(r.suspicious)


class MultiConstellationTest(unittest.TestCase):
    def test_agreement_clean(self):
        r = MultiConstellationCrossCheck().check({"GPS": [0, 0, 0], "GAL": [1, 1, 1]})
        self.assertFalse(r.suspicious)

    def test_divergence_flagged(self):
        r = MultiConstellationCrossCheck().check({"GPS": [0, 0, 0], "GAL": [100, 0, 0]})
        self.assertTrue(r.suspicious)


class AggregateDetectorTest(unittest.TestCase):
    def _seed(self, det):
        det.evaluate(0.0, [0, 0, 0], [0, 0, 0], [0, 0], [1, 1], [45, 40, 48],
                     0.0, {"GPS": [0, 0, 0]})

    def test_clean_epoch_trusts_gnss(self):
        det = SpoofingDetector()
        self._seed(det)
        v = det.evaluate(1.0, [0, 0, 0], [0, 0, 0], [0.2, -0.1], [1, 1],
                         [45, 40, 48], 0.0, {"GPS": [0, 0, 0], "GAL": [1, 0, 0]})
        self.assertFalse(v.spoofing_suspected)
        self.assertEqual(v.recommended_action(), "TRUST_GNSS")

    def test_multi_flag_epoch_declares_spoof(self):
        det = SpoofingDetector()
        self._seed(det)
        v = det.evaluate(
            1.0,
            pos=[800, 0, 0],            # glitch
            vel=[0, 0, 0],
            innovation=[60, 60],        # innovation gate
            innovation_var=[1, 1],
            cn0_dbhz=[53, 53.1, 52.9],  # strong+uniform
            clock_bias_m=5000.0,        # clock jump
            fixes_by_constellation={"GPS": [0, 0, 0], "GAL": [200, 0, 0]},  # divergence
        )
        self.assertTrue(v.spoofing_suspected)
        self.assertEqual(v.recommended_action(), "REJECT_GNSS_DEADRECKON")


if __name__ == "__main__":
    unittest.main()
