"""Command link from the GCS cockpit to the vehicle.

Two links share one interface (``send(command) -> Ack``):

- ``LoopbackLink`` — in-process, HMAC-signed, anti-replay; for the offline
  cockpit and tests.
- ``MavlinkLink`` — the **real production link**: MAVLink 2 over serial/UDP to an
  ArduPilot/PX4 flight controller (or SITL / the bundled ``gcs.sim_vehicle``),
  with MAVLink 2 message signing. It translates cockpit commands into actual
  ``MANUAL_CONTROL`` + ``DO_SET_SERVO`` (net gimbal, via ``gcs.payload_map``) +
  arm/relay/RTL messages, and pulls live telemetry for the HUD.

``LoopbackLink`` is stdlib-only; ``MavlinkLink`` imports pymavlink lazily.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field

from . import payload_map


@dataclass
class Ack:
    ok: bool
    seq: int
    reason: str = ""


@dataclass
class LoopbackLink:
    """In-process, optionally-signed command link with anti-replay."""

    key: bytes | None = None          # set => sign + verify each frame
    seq: int = 0
    sent: list[dict] = field(default_factory=list)
    _last_seq_seen: int = -1

    def _sign(self, payload: dict) -> str:
        blob = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(self.key, blob, hashlib.sha256).hexdigest()[:16]

    def send(self, command: dict) -> Ack:
        self.seq += 1
        frame = {"seq": self.seq, "t": round(time.time(), 3), "cmd": command}
        if self.key is not None:
            frame["sig"] = self._sign({"seq": frame["seq"], "cmd": command})
        self.sent.append(frame)
        return self._vehicle_receive(frame)

    # --- vehicle side -------------------------------------------------------
    def _vehicle_receive(self, frame: dict) -> Ack:
        seq = frame["seq"]
        if self.key is not None:
            expect = self._sign({"seq": seq, "cmd": frame["cmd"]})
            if not hmac.compare_digest(expect, frame.get("sig", "")):
                return Ack(False, seq, "bad signature")
        if seq <= self._last_seq_seen:
            return Ack(False, seq, "replay/out-of-order")
        self._last_seq_seen = seq
        return Ack(True, seq)

    def last(self) -> dict | None:
        return self.sent[-1] if self.sent else None

    def telemetry(self) -> dict:
        return {}            # loopback has no vehicle telemetry

    def close(self) -> None:
        pass


# 32-byte derived signing key (MAVLink 2 message signing uses a 32-byte secret)
def _signing_key(secret: bytes) -> bytes:
    return hashlib.sha256(secret).digest()


class MavlinkLink:
    """Real MAVLink 2 command link to a flight controller / SITL / sim_vehicle.

    ``connection`` is any pymavlink string, e.g. ``udpout:127.0.0.1:14550`` (SITL
    / sim_vehicle), ``/dev/ttyACM0`` or ``COM5`` (USB Pixhawk), ``udp:0.0.0.0:14550``.
    Cockpit commands are translated to MAVLink and signed (MAVLink 2) when a key
    is given.
    """

    def __init__(self, connection: str = "udpout:127.0.0.1:14550",
                 key: bytes | None = None,
                 source_system: int = 255, source_component: int = 190,
                 baud: int = 115200) -> None:
        # MAVLink 2 message signing is opt-in (pass ``key``): both the GCS and the
        # flight controller must be provisioned with the same key. SITL and the
        # bundled sim_vehicle run unsigned, like a default ArduPilot setup.
        from pymavlink import mavutil

        self.mavutil = mavutil
        self.conn = mavutil.mavlink_connection(
            connection, source_system=source_system,
            source_component=source_component, baud=baud)
        self.seq = 0
        self.signing_enabled = False
        if key is not None:
            self.conn.setup_signing(_signing_key(key), sign_outgoing=True)
            self.signing_enabled = True
        self._t: dict = {}

    # -- lifecycle -----------------------------------------------------------
    def _gcs_heartbeat(self) -> None:
        # announce ourselves so a udpin/udpout endpoint learns our address
        self.conn.mav.heartbeat_send(
            self.mavutil.mavlink.MAV_TYPE_GCS,
            self.mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)

    def wait_heartbeat(self, timeout: float = 5.0) -> bool:
        self._gcs_heartbeat()
        hb = self.conn.wait_heartbeat(timeout=timeout)
        return hb is not None

    @property
    def _tsys(self) -> int:
        return self.conn.target_system or 1

    @property
    def _tcomp(self) -> int:
        return self.conn.target_component or 1

    # -- command translation -------------------------------------------------
    def send(self, command: dict) -> "Ack":
        self.seq += 1
        typ = command.get("type", "")
        sp = command.get("setpoint")
        if sp:
            self._send_setpoint(sp)
        if typ == "ARM":
            self._arm(True)
        elif typ in ("DISARM", "ESTOP"):
            self._arm(False)
        elif typ == "FIRE_NET":
            self._fire()
        elif typ == "CINCH_NET":
            self._servo(payload_map.CINCH, 100.0)
        elif typ == "RELEASE":
            self._servo(payload_map.RELEASE, 1.0)
        elif typ == "RTH":
            self._rtl()
        return Ack(True, self.seq)

    def _send_setpoint(self, sp: dict) -> None:
        # MANUAL_CONTROL: x=pitch, y=roll, z=throttle(0..1000), r=yaw, all int16
        self.conn.mav.manual_control_send(
            self._tsys,
            int(sp.get("pitch", 0.0) * 1000), int(sp.get("roll", 0.0) * 1000),
            int(sp.get("throttle", 0.0) * 1000), int(sp.get("yaw", 0.0) * 1000), 0)
        # net gimbal -> real servo outputs (single source: payload_map)
        self._servo(payload_map.NET_PAN, sp.get("net_pan", 0.0))
        self._servo(payload_map.NET_TILT, sp.get("net_tilt", 0.0))

    def _servo(self, spec, angle: float) -> None:
        self.conn.mav.command_long_send(
            self._tsys, self._tcomp, self.mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
            0, spec.channel, spec.pwm_for(angle), 0, 0, 0, 0, 0)

    def _arm(self, arm: bool) -> None:
        self.conn.mav.command_long_send(
            self._tsys, self._tcomp,
            self.mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1 if arm else 0, 0, 0, 0, 0, 0, 0)

    def _fire(self) -> None:
        self.conn.mav.command_long_send(
            self._tsys, self._tcomp, self.mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
            0, payload_map.TRIGGER_RELAY, 1, 0, 0, 0, 0, 0)

    def _rtl(self) -> None:
        self.conn.mav.command_long_send(
            self._tsys, self._tcomp,
            self.mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            0, 0, 0, 0, 0, 0, 0, 0)

    # -- telemetry for the HUD ----------------------------------------------
    def telemetry(self) -> dict:
        import math

        while True:
            m = self.conn.recv_match(blocking=False)
            if m is None:
                break
            mt = m.get_type()
            if mt == "ATTITUDE":
                self._t.update(roll=math.degrees(m.roll), pitch=math.degrees(m.pitch),
                               yaw=math.degrees(m.yaw) % 360)
            elif mt == "VFR_HUD":
                self._t.update(spd=m.groundspeed, alt=m.alt, hdg=m.heading)
            elif mt == "GPS_RAW_INT":
                self._t.update(lat=m.lat * 1e-7, lon=m.lon * 1e-7,
                               fix=m.fix_type, sats=m.satellites_visible)
            elif mt == "SYS_STATUS":
                self._t.update(batt=m.battery_remaining,
                               volt=m.voltage_battery / 1000.0)
            elif mt == "HEARTBEAT":
                self._t["armed"] = bool(
                    m.base_mode & self.mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        return dict(self._t)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
