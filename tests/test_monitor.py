import unittest

from defense.gnss.osnma_adapter import AuthResult
from defense.gnss.raim import RaimResult
from defense.gnss.spoof_detection import CheckResult, SpoofingVerdict
from defense.monitor import DefenseMonitor, NavMode


def good_raim():
    return RaimResult(solution=[0, 0, 0, 0], sse=1.0, threshold=10.0,
                      fault_detected=False, excluded_index=None)


def clean_spoof():
    return SpoofingVerdict(False, False, [CheckResult("x", False)])


def spoof_no_auth():
    return SpoofingVerdict(True, False, [CheckResult("x", True), CheckResult("y", True)])


class DefenseMonitorTest(unittest.TestCase):
    def setUp(self):
        self.mon = DefenseMonitor()

    def test_all_clean_trusts_gnss(self):
        st = self.mon.assess(AuthResult(True, "ok"), good_raim(), clean_spoof(), command_link_ok=True)
        self.assertEqual(st.mode, NavMode.TRUST_GNSS)
        self.assertTrue(st.gnss_authenticated)

    def test_spoof_without_osnma_deadreckons(self):
        st = self.mon.assess(AuthResult(False, "no lock"), good_raim(), spoof_no_auth(), True)
        self.assertEqual(st.mode, NavMode.DEADRECKON)
        self.assertTrue(st.spoofing_suspected)

    def test_spoof_with_osnma_only_degrades(self):
        # Cryptographic authentication rescues trust from consistency-only spoof flags.
        st = self.mon.assess(AuthResult(True, "ok"), good_raim(), spoof_no_auth(), True)
        self.assertEqual(st.mode, NavMode.GNSS_DEGRADED)

    def test_lost_command_link_and_nav_fails_to_rth(self):
        st = self.mon.assess(AuthResult(False, "no lock"), good_raim(), spoof_no_auth(),
                             command_link_ok=False)
        self.assertEqual(st.mode, NavMode.RETURN_TO_HOME)
        self.assertFalse(st.command_link_trusted)

    def test_jamming_deadreckons(self):
        jam = SpoofingVerdict(False, True, [CheckResult("cn0_jam", True)])
        st = self.mon.assess(AuthResult(True, "ok"), good_raim(), jam, True)
        self.assertEqual(st.mode, NavMode.DEADRECKON)


if __name__ == "__main__":
    unittest.main()
