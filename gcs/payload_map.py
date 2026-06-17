"""Single source of truth for the TaloNet payload hardware interface.

These channel / PWM / angle-limit definitions are shared by BOTH the software
(the cockpit sends ``DO_SET_SERVO`` to exactly these flight-controller outputs)
AND the hardware/CAD/circuit docs (``cad/talonet_frame.scad`` net_pan/net_tilt
limits, ``docs/06`` AIM-PAN/AIM-TILT pin map) — so the model is not "clay", it
matches what the firmware actually drives. Change a limit here and the cockpit,
the gimbal range, and the docs all refer to the same numbers.

One aiming turret (pan/tilt), TWO munitions sharing it:

- CRADLE  — the small self-cinching recovery net (RELAY 0): used to take a
  RECON / surveillance drone ALIVE and intact (fire -> cinch -> winch -> RTL).
- TRAWLER — the large stand-off net (RELAY 1) + cord-cutter (RELAY 2): used on a
  KAMIKAZE / attack drone WITHOUT ever closing to contact. Fire the big net from
  a safe distance to tangle its rotors, then sever the tether (burn-wire) and let
  net+drone fall away. Nothing dangerous is ever hauled back to the mothership.

Mapping (ArduPilot SERVOn outputs / relays):
    SERVO 9  AIM-PAN    net gimbal pan      -60..+60 deg -> 1000..2000 us
    SERVO 10 AIM-TILT   net gimbal tilt       0..75  deg -> 1000..2000 us
    SERVO 11 CINCH      mouth cinch driver    0..100 %   -> 1000..2000 us  (CRADLE)
    SERVO 12 RELEASE    quick-release          0..1       -> 1000..2000 us  (CRADLE)
    RELAY 0  TRIGGER    CRADLE  net-launcher fire (CO2 solenoid / igniter)
    RELAY 1  TRAWLER    TRAWLER stand-off net-launcher fire (large charge)
    RELAY 2  CORD-CUT   TRAWLER tether burn-wire / cutter (jettison the catch)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServoSpec:
    """One flight-controller servo output with its calibration + travel limits."""

    name: str
    channel: int       # ArduPilot SERVOn output (DO_SET_SERVO param1)
    pwm_min: int
    pwm_max: int
    angle_min: float
    angle_max: float

    def clamp(self, angle: float) -> float:
        return min(max(angle, self.angle_min), self.angle_max)

    def pwm_for(self, angle: float) -> int:
        """Linear angle -> microseconds across the calibrated travel."""
        a = self.clamp(angle)
        f = (a - self.angle_min) / (self.angle_max - self.angle_min)
        return int(round(self.pwm_min + f * (self.pwm_max - self.pwm_min)))


# Net-launcher gimbal + payload actuators (must match cad + docs/06)
NET_PAN = ServoSpec("AIM-PAN", 9, 1000, 2000, -60.0, 60.0)
NET_TILT = ServoSpec("AIM-TILT", 10, 1000, 2000, 0.0, 75.0)
CINCH = ServoSpec("CINCH", 11, 1000, 2000, 0.0, 100.0)
RELEASE = ServoSpec("RELEASE", 12, 1000, 2000, 0.0, 1.0)

# MAV_CMD_DO_SET_RELAY indices (each net system fires fire-and-forget, never a
# servo — pulse on, mechanism does the rest; safer in front of a live warhead).
TRIGGER_RELAY = 0          # CRADLE recovery-net launcher fire
TRAWLER_TRIGGER_RELAY = 1  # TRAWLER stand-off net launcher fire
CORD_CUTTER_RELAY = 2      # TRAWLER tether burn-wire / cutter -> jettison the catch

# Travel limits re-exported so gcs.control and cad stay in lock-step
PAN_LIMITS = (NET_PAN.angle_min, NET_PAN.angle_max)
TILT_LIMITS = (NET_TILT.angle_min, NET_TILT.angle_max)
