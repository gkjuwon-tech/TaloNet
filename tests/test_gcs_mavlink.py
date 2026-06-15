"""Real-MAVLink integration tests for the production cockpit link.

Exercises ``gcs.link.MavlinkLink`` against the bundled ``gcs.sim_vehicle`` over
real MAVLink 2 frames on loopback UDP — proving the cockpit drives a vehicle with
the actual wire protocol (arm, net-gimbal DO_SET_SERVO, fire relay) and reads
live telemetry. Guarded with skipUnless so CI stays green without pymavlink.
The payload-map tests are pure stdlib and always run.
"""

import importlib.util
import threading
import time
import unittest

from gcs import payload_map
from gcs.control import PAN_LIMITS, TILT_LIMITS

HAVE_PYMAVLINK = importlib.util.find_spec("pymavlink") is not None

# MAVLink command IDs used in assertions
_ARM = 400        # MAV_CMD_COMPONENT_ARM_DISARM
_SET_SERVO = 183  # MAV_CMD_DO_SET_SERVO
_SET_RELAY = 181  # MAV_CMD_DO_SET_RELAY


class TestPayloadMap(unittest.TestCase):
    def test_pwm_mapping_and_clamp(self):
        self.assertEqual(payload_map.NET_PAN.pwm_for(0), 1500)
        self.assertEqual(payload_map.NET_PAN.pwm_for(60), 2000)
        self.assertEqual(payload_map.NET_PAN.pwm_for(-60), 1000)
        self.assertEqual(payload_map.NET_PAN.pwm_for(999), 2000)   # clamps
        self.assertEqual(payload_map.NET_TILT.pwm_for(0), 1000)
        self.assertEqual(payload_map.NET_TILT.pwm_for(75), 2000)

    def test_limits_shared_with_control(self):
        # the cockpit control limits MUST come from the single source of truth
        self.assertEqual(PAN_LIMITS, (payload_map.NET_PAN.angle_min,
                                      payload_map.NET_PAN.angle_max))
        self.assertEqual(TILT_LIMITS, (payload_map.NET_TILT.angle_min,
                                       payload_map.NET_TILT.angle_max))


@unittest.skipUnless(HAVE_PYMAVLINK, "pymavlink not installed")
class TestMavlinkLink(unittest.TestCase):
    def _start_vehicle(self, port):
        from gcs.sim_vehicle import run as sim_run

        captured: list = []
        stop = threading.Event()
        th = threading.Thread(
            target=sim_run,
            kwargs=dict(connection=f"udpin:127.0.0.1:{port}", captured=captured,
                        stop=stop),
            daemon=True)
        th.start()
        time.sleep(0.3)
        return captured, stop

    def test_end_to_end_commands_and_telemetry(self):
        from gcs.link import MavlinkLink

        port = 14601
        captured, stop = self._start_vehicle(port)
        try:
            link = MavlinkLink(f"udpout:127.0.0.1:{port}")
            self.assertTrue(link.wait_heartbeat(timeout=6.0))
            link.send({"type": "ARM", "setpoint": {
                "roll": 0.2, "pitch": 0.1, "yaw": 0.0, "throttle": 0.5,
                "net_pan": 30, "net_tilt": 40}})
            link.send({"type": "FIRE_NET"})
            time.sleep(0.5)
            tlm = link.telemetry()
            self.assertIn("pitch", tlm)
            self.assertIn("alt", tlm)
            self.assertGreaterEqual(tlm.get("sats", 0), 1)

            cmds = [m for m in captured if m.get_type() == "COMMAND_LONG"]
            arms = [int(m.param1) for m in cmds if m.command == _ARM]
            servos = {int(m.param1): int(m.param2)
                      for m in cmds if m.command == _SET_SERVO}
            relays = [int(m.param1) for m in cmds if m.command == _SET_RELAY]
            self.assertIn(1, arms)                                  # armed
            self.assertEqual(servos.get(payload_map.NET_PAN.channel),
                             payload_map.NET_PAN.pwm_for(30))       # pan servo
            self.assertEqual(servos.get(payload_map.NET_TILT.channel),
                             payload_map.NET_TILT.pwm_for(40))      # tilt servo
            self.assertIn(payload_map.TRIGGER_RELAY, relays)        # net fire
            link.close()
        finally:
            stop.set()


if __name__ == "__main__":
    unittest.main()
