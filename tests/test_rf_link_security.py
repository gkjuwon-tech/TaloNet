import unittest

from defense.link.rf_link_security import (
    AuthenticatedChannel,
    LinkIntegrityMonitor,
    ReplayWindow,
)

KEY = b"shared-link-key-0123456789"


class ReplayWindowTest(unittest.TestCase):
    def test_fresh_accepted_duplicate_rejected(self):
        w = ReplayWindow(window_size=8)
        self.assertTrue(w.check_and_update(1))
        self.assertTrue(w.check_and_update(2))
        self.assertFalse(w.check_and_update(2))  # duplicate
        self.assertTrue(w.check_and_update(3))

    def test_reordering_within_window(self):
        w = ReplayWindow(window_size=8)
        self.assertTrue(w.check_and_update(5))
        self.assertTrue(w.check_and_update(3))  # late but within window
        self.assertFalse(w.check_and_update(3))

    def test_stale_outside_window_rejected(self):
        w = ReplayWindow(window_size=4)
        w.check_and_update(100)
        self.assertFalse(w.check_and_update(1))


class AuthenticatedChannelTest(unittest.TestCase):
    def test_roundtrip(self):
        tx = AuthenticatedChannel(KEY)
        rx = AuthenticatedChannel(KEY)
        frame = tx.wrap(b"hello-uav")
        out = rx.unwrap(frame)
        self.assertIsNotNone(out)
        self.assertEqual(out.payload, b"hello-uav")

    def test_forged_frame_rejected(self):
        rx = AuthenticatedChannel(KEY)
        tx = AuthenticatedChannel(KEY)
        frame = bytearray(tx.wrap(b"payload"))
        frame[10] ^= 0xFF
        self.assertIsNone(rx.unwrap(bytes(frame)))

    def test_wrong_key_rejected(self):
        tx = AuthenticatedChannel(KEY)
        rx = AuthenticatedChannel(b"different-key-aaaaaaaaaaaa")
        self.assertIsNone(rx.unwrap(tx.wrap(b"data")))

    def test_replayed_frame_rejected(self):
        tx = AuthenticatedChannel(KEY)
        rx = AuthenticatedChannel(KEY)
        frame = tx.wrap(b"data")
        self.assertIsNotNone(rx.unwrap(frame))
        self.assertIsNone(rx.unwrap(frame))  # replay


class LinkIntegrityMonitorTest(unittest.TestCase):
    def test_jamming_detected(self):
        mon = LinkIntegrityMonitor(crc_error_rate_threshold=0.3)
        st = mon.update(rssi_dbm=-80, crc_ok=2, crc_fail=8)
        self.assertTrue(st.jamming_suspected)

    def test_takeover_detected(self):
        mon = LinkIntegrityMonitor(rssi_step_db=12.0)
        for _ in range(10):
            mon.update(rssi_dbm=-85, crc_ok=10, crc_fail=0)
        st = mon.update(rssi_dbm=-60, crc_ok=10, crc_fail=0)  # +25 dB new emitter
        self.assertTrue(st.takeover_suspected)

    def test_healthy_link(self):
        mon = LinkIntegrityMonitor()
        st = mon.update(rssi_dbm=-85, crc_ok=10, crc_fail=0)
        self.assertFalse(st.jamming_suspected)
        self.assertFalse(st.takeover_suspected)


if __name__ == "__main__":
    unittest.main()
