import unittest

from defense.gnss.raim import RaimMonitor, chi2_cdf, chi2_threshold

# 6-satellite design matrix: [-ux, -uy, -uz, 1] mapping (dx, dy, dz, c*dt).
GEOMETRY = [
    [0.10, 0.95, 0.30, 1.0],
    [0.80, -0.20, 0.55, 1.0],
    [-0.60, 0.50, 0.62, 1.0],
    [-0.30, -0.85, 0.43, 1.0],
    [0.55, 0.55, 0.63, 1.0],
    [-0.75, -0.10, 0.65, 1.0],
]
TRUE_STATE = [12.0, -7.0, 4.0, 2.5]


def synth_measurements(state, bias=None):
    meas = [sum(GEOMETRY[i][j] * state[j] for j in range(4)) for i in range(len(GEOMETRY))]
    if bias:
        for idx, b in bias.items():
            meas[idx] += b
    return meas


class Chi2Test(unittest.TestCase):
    def test_cdf_known_values(self):
        # Median of chi-square(dof=2) is 2*ln(2) ~= 1.386 -> CDF ~ 0.5
        self.assertAlmostEqual(chi2_cdf(1.3862943611, 2), 0.5, places=4)
        self.assertAlmostEqual(chi2_cdf(0.0, 5), 0.0, places=6)

    def test_threshold_inversion(self):
        for dof in (1, 2, 4, 8):
            t = chi2_threshold(0.05, dof)
            self.assertAlmostEqual(chi2_cdf(t, dof), 0.95, places=3)


class RaimTest(unittest.TestCase):
    def test_clean_solution_healthy(self):
        meas = synth_measurements(TRUE_STATE)
        res = RaimMonitor().check(GEOMETRY, meas)
        self.assertFalse(res.fault_detected)
        self.assertTrue(res.healthy)
        for est, truth in zip(res.solution, TRUE_STATE):
            self.assertAlmostEqual(est, truth, places=6)

    def test_single_fault_detected_and_excluded(self):
        meas = synth_measurements(TRUE_STATE, bias={2: 60.0})
        res = RaimMonitor().check(GEOMETRY, meas)
        self.assertTrue(res.fault_detected)
        self.assertEqual(res.excluded_index, 2)
        self.assertTrue(res.healthy)
        # After excluding the faulty satellite the solution recovers truth.
        for est, truth in zip(res.solution, TRUE_STATE):
            self.assertAlmostEqual(est, truth, places=4)

    def test_insufficient_redundancy(self):
        geo = GEOMETRY[:4]
        meas = [sum(geo[i][j] * TRUE_STATE[j] for j in range(4)) for i in range(4)]
        res = RaimMonitor().check(geo, meas)
        self.assertFalse(res.fault_detected)  # dof < 1, cannot detect


if __name__ == "__main__":
    unittest.main()
