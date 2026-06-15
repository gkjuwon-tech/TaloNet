"""Tests for the GCS manual teleop cockpit.

control/link are pure stdlib and always run; the camera test needs numpy and the
cockpit-render test needs pygame, both guarded with skipUnless so CI stays green.
"""

import importlib.util
import os
import unittest

from gcs.control import PAN_LIMITS, TILT_LIMITS, ControlState
from gcs.link import LoopbackLink

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None
HAVE_PYGAME = importlib.util.find_spec("pygame") is not None


class TestControl(unittest.TestCase):
    def test_flight_axes_from_held(self):
        s = ControlState()
        s.apply_held({"w", "d", "e"}, 0.1)
        self.assertEqual((s.pitch, s.roll, s.yaw), (1.0, 1.0, 1.0))
        s.apply_held({"s", "a", "q"}, 0.1)
        self.assertEqual((s.pitch, s.roll, s.yaw), (-1.0, -1.0, -1.0))
        s.apply_held(set(), 0.1)  # return to centre
        self.assertEqual((s.pitch, s.roll, s.yaw), (0.0, 0.0, 0.0))

    def test_throttle_integrates_and_clamps(self):
        s = ControlState(throttle_rate=1.0)
        for _ in range(5):
            s.apply_held({"r"}, 0.5)
        self.assertEqual(s.throttle, 1.0)  # clamped at 1
        for _ in range(10):
            s.apply_held({"f"}, 0.5)
        self.assertEqual(s.throttle, 0.0)  # clamped at 0

    def test_net_aim_slew_and_limits(self):
        s = ControlState(net_pan=0.0, net_tilt=16.0, aim_rate=100.0)
        for _ in range(10):
            s.apply_held({"l", "i"}, 0.5)
        self.assertEqual(s.net_pan, PAN_LIMITS[1])
        self.assertEqual(s.net_tilt, TILT_LIMITS[1])

    def test_arming_interlocks(self):
        s = ControlState()
        self.assertEqual(s.handle_key("space")["type"], "DENIED")  # unarmed
        self.assertEqual(s.handle_key("g")["type"], "ARM")
        self.assertEqual(s.handle_key("space")["type"], "FIRE_NET")
        self.assertEqual(s.handle_key("c")["type"], "CINCH_NET")

    def test_estop_latches_and_blocks(self):
        s = ControlState(armed=True, throttle=0.5)
        self.assertEqual(s.handle_key("b")["type"], "ESTOP")
        self.assertFalse(s.armed)
        self.assertEqual(s.throttle, 0.0)
        self.assertEqual(s.handle_key("g")["type"], "DENIED")  # cannot arm under e-stop
        self.assertEqual(s.handle_key("n")["type"], "ESTOP_RESET")
        self.assertEqual(s.handle_key("g")["type"], "ARM")     # arms after reset

    def test_unmapped_key_ignored(self):
        self.assertIsNone(ControlState().handle_key("z"))


class TestLink(unittest.TestCase):
    def test_loopback_ack_and_sequence(self):
        link = LoopbackLink()
        self.assertEqual(link.send({"type": "SETPOINT"}).seq, 1)
        self.assertTrue(link.send({"type": "FIRE_NET"}).ok)
        self.assertEqual(len(link.sent), 2)

    def test_signed_link_accepts_and_rejects_tamper(self):
        link = LoopbackLink(key=b"secret")
        ack = link.send({"type": "FIRE_NET"})
        self.assertTrue(ack.ok)
        # tamper a recorded frame's signature -> vehicle-side verify must fail
        bad = dict(link.sent[-1])
        bad["sig"] = "0" * 16
        self.assertFalse(link._vehicle_receive(bad).ok)

    def test_replay_rejected(self):
        link = LoopbackLink(key=b"secret")
        link.send({"type": "CINCH_NET"})
        replay = link.sent[-1]
        self.assertFalse(link._vehicle_receive(replay).ok)  # seq <= last seen


@unittest.skipUnless(HAVE_NUMPY, "numpy not installed")
class TestCamera(unittest.TestCase):
    def test_synthetic_frame(self):
        from gcs.camera import SyntheticCamera

        cam = SyntheticCamera(320, 180)
        frame = cam.frame(1.0, ControlState(roll=0.3, pitch=-0.2))
        self.assertEqual(frame.shape, (180, 320, 3))
        self.assertEqual(str(frame.dtype), "uint8")


@unittest.skipUnless(HAVE_PYGAME and HAVE_NUMPY, "pygame/numpy not installed")
class TestCockpit(unittest.TestCase):
    def test_headless_render(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        from gcs.app import run

        state = run(max_frames=2, window=(480, 270),
                    state=ControlState(armed=True, net_pan=20, net_tilt=30))
        self.assertIsInstance(state, ControlState)


if __name__ == "__main__":
    unittest.main()
