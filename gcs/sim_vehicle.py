"""Minimal MAVLink vehicle emulator for the TaloNet cockpit prototype.

Speaks real MAVLink 2 over UDP: streams HEARTBEAT / ATTITUDE / VFR_HUD /
GPS_RAW_INT / SYS_STATUS and accepts the cockpit's commands (arm/disarm,
DO_SET_SERVO for the net gimbal, DO_SET_RELAY fire, RTL). Run it next to the
cockpit to fly the whole loop with no hardware, then point the cockpit at a real
Pixhawk or ArduPilot SITL instead — same protocol, same code.

    python -m gcs.sim_vehicle                 # listens on udpin:127.0.0.1:14550
    python -m gcs --connect udpout:127.0.0.1:14550

This is NOT flight dynamics — it is a protocol/telemetry stand-in so the cockpit,
signing, servo mapping and HUD can be exercised against the real wire format.
"""

from __future__ import annotations

import math
import time


def run(connection: str = "udpin:127.0.0.1:14550", key: bytes | None = None,
        duration: float | None = None, stop=None, captured: list | None = None,
        verbose: bool = False) -> None:
    """Emulate a vehicle endpoint. ``stop`` is an optional threading.Event."""
    from pymavlink import mavutil

    mav = mavutil.mavlink_connection(connection, source_system=1, source_component=1)
    if key is not None:
        import hashlib
        mav.setup_signing(hashlib.sha256(key).digest(), sign_outgoing=True)

    armed = False
    t0 = time.time()
    last_tlm = 0.0
    while True:
        if stop is not None and stop.is_set():
            break
        now = time.time() - t0
        if duration is not None and now >= duration:
            break

        if now - last_tlm >= 0.1:                       # 10 Hz telemetry
            last_tlm = now
            base = (mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED if armed else 0)
            mav.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_OCTOROTOR,
                mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                base, 0, mavutil.mavlink.MAV_STATE_ACTIVE)
            mav.mav.attitude_send(int(now * 1000), math.sin(now * 0.3) * 0.12,
                                  math.cos(now * 0.4) * 0.10, (now * 0.1) % (2 * math.pi),
                                  0, 0, 0)
            mav.mav.vfr_hud_send(12.0, 12.6, int((now * 5) % 360), 55, 118.0, 0.45)
            mav.mav.gps_raw_int_send(int(now * 1e6), 3, 375012000, 1270431000,
                                     120000, 100, 100, 500, 9000, 14)
            mav.mav.sys_status_send(0, 0, 0, 250, 22000, -1, 92, 0, 0, 0, 0, 0, 0)

        msg = mav.recv_match(blocking=True, timeout=0.05)
        if msg is None:
            continue
        if captured is not None:
            captured.append(msg)
        mt = msg.get_type()
        if mt == "COMMAND_LONG":
            cmd = msg.command
            if cmd == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                armed = bool(msg.param1)
                if verbose:
                    print("ARMED" if armed else "DISARMED")
            elif cmd == mavutil.mavlink.MAV_CMD_DO_SET_SERVO and verbose:
                print(f"SERVO ch{int(msg.param1)} -> {int(msg.param2)}us")
            elif cmd == mavutil.mavlink.MAV_CMD_DO_SET_RELAY and verbose:
                print(f"RELAY {int(msg.param1)} -> {int(msg.param2)} (NET FIRE)")
            mav.mav.command_ack_send(cmd, mavutil.mavlink.MAV_RESULT_ACCEPTED)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="TaloNet MAVLink vehicle emulator")
    ap.add_argument("--connect", default="udpin:127.0.0.1:14550")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    print(f"[sim_vehicle] MAVLink on {a.connect} (Ctrl-C to stop)")
    run(a.connect, duration=a.duration, verbose=not a.quiet)
