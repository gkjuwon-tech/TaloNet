"""Keyboard control mapping + manual control state (dependency-free).

This is the heart of the manual teleoperation cockpit: it turns held/pressed
keys into a flight + net-launcher control state and discrete command events. It
has no GUI/transport dependency so it is fully unit-testable; the pygame app
(:mod:`gcs.app`) and the command link (:mod:`gcs.link`) sit on top.

Speed-first design: there is NO onboard VLM in the control loop — a human flies
and aims, which is faster and keeps the engagement decision squarely with the
operator. The net is software-AIMED (pan/tilt) and fired on command, not dropped.

Two engagement nets share one aiming turret (see gcs/payload_map.py):
    CRADLE  — small self-cinching net: take a RECON drone alive (fire->cinch->
              winch->RTL). C cinch + V release belong to this mode.
    TRAWLER — large stand-off net + cord-cutter: neutralise a KAMIKAZE drone from
              a safe distance (fire->tangle->cut tether->jettison). X cuts the
              cord. Never closes to contact, never hauls the catch home.
SPACE is mode-aware: it fires whichever net is selected. M toggles the mode.

Key map (held = analogue axes / aim slew; pressed = discrete actions):
    flight : W/S pitch, A/D roll, Q/E yaw, R/F throttle up/down
    net aim: I/K tilt up/down, J/L pan left/right
    actions: SPACE fire(selected net), M net-mode toggle, C cinch (CRADLE),
             X cord-cut/jettison (TRAWLER), V release(drop), G arm-toggle,
             B E-STOP, N estop-reset, H return-to-home
"""

from __future__ import annotations

from dataclasses import dataclass

# Single source of truth for the gimbal travel (shared with the firmware servo
# map and the CAD model): see gcs/payload_map.py.
from .payload_map import PAN_LIMITS, TILT_LIMITS


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


# held-key flight-axis bindings: (positive_key, negative_key), return-to-centre
_AXES = {"roll": ("d", "a"), "pitch": ("w", "s"), "yaw": ("e", "q")}

# pressed-key discrete actions ("space"->FIRE is resolved per engagement mode)
_EVENTS = {
    "g": "ARM_TOGGLE", "b": "ESTOP", "n": "ESTOP_RESET",
    "space": "FIRE", "m": "MODE_TOGGLE", "c": "CINCH_NET", "x": "CORD_CUT",
    "v": "RELEASE", "h": "RTH",
}

# Selectable engagement nets (see gcs/payload_map.py); the aiming turret is shared.
CRADLE, TRAWLER = "CRADLE", "TRAWLER"


@dataclass
class ControlState:
    """Live manual-control state, updated each frame from the keyboard."""

    roll: float = 0.0       # [-1,1]
    pitch: float = 0.0      # [-1,1]
    yaw: float = 0.0        # [-1,1]
    throttle: float = 0.0   # [0,1] level (integrates while held)
    net_pan: float = 0.0    # deg, software aim
    net_tilt: float = 16.0  # deg, software aim
    armed: bool = False
    estop: bool = False
    mode: str = "MANUAL"
    engagement_mode: str = CRADLE   # CRADLE (recon, recover) | TRAWLER (kamikaze, jettison)
    last_action: str = ""
    throttle_rate: float = 0.6   # per second
    aim_rate: float = 45.0       # deg per second

    def apply_held(self, held: set[str], dt: float) -> None:
        """Update analogue axes + aim slew from the currently-held keys."""
        if self.estop:
            self.roll = self.pitch = self.yaw = 0.0
            self.throttle = 0.0
            return
        for axis, (pos, neg) in _AXES.items():
            setattr(self, axis,
                    (1.0 if pos in held else 0.0) - (1.0 if neg in held else 0.0))
        if "r" in held:
            self.throttle = _clamp(self.throttle + self.throttle_rate * dt, 0.0, 1.0)
        if "f" in held:
            self.throttle = _clamp(self.throttle - self.throttle_rate * dt, 0.0, 1.0)
        if "l" in held:
            self.net_pan = _clamp(self.net_pan + self.aim_rate * dt, *PAN_LIMITS)
        if "j" in held:
            self.net_pan = _clamp(self.net_pan - self.aim_rate * dt, *PAN_LIMITS)
        if "i" in held:
            self.net_tilt = _clamp(self.net_tilt + self.aim_rate * dt, *TILT_LIMITS)
        if "k" in held:
            self.net_tilt = _clamp(self.net_tilt - self.aim_rate * dt, *TILT_LIMITS)

    def handle_key(self, key: str) -> dict | None:
        """Process a discrete key press; return a command dict or None.

        Interlocks: every payload action (fire/cinch/cord-cut/release) requires
        ARMED; nothing arms while E-STOP is latched. CINCH belongs to CRADLE and
        CORD-CUT to TRAWLER, so the wrong-mode key is refused — you can't cinch a
        stand-off net, and you can't cut a recovery net's tether. These mirror the
        hardware arming interlock (docs/06 §11).
        """
        action = _EVENTS.get(key.lower())
        if action is None:
            return None
        if action == "ESTOP":
            self.estop = True
            self.armed = False
            self.throttle = 0.0
            self.mode = "ESTOP"
        elif action == "ESTOP_RESET":
            self.estop = False
            self.mode = "MANUAL"
        elif action == "ARM_TOGGLE":
            if self.estop:
                return self._denied("E-STOP latched")
            self.armed = not self.armed
            action = "ARM" if self.armed else "DISARM"
        elif action == "MODE_TOGGLE":
            # Selecting which net is armed is just turret/munition selection; it
            # is always allowed (no actuation), even disarmed or under E-STOP.
            self.engagement_mode = TRAWLER if self.engagement_mode == CRADLE else CRADLE
            action = f"MODE_{self.engagement_mode}"
            self.last_action = action
            return {"type": action, "engagement_mode": self.engagement_mode,
                    "setpoint": self.setpoint()}
        elif action == "FIRE":
            # Mode-aware trigger: CRADLE recovery net vs TRAWLER stand-off net.
            action = "FIRE_NET" if self.engagement_mode == CRADLE else "FIRE_TRAWLER"
            if self.estop or not self.armed:
                return self._denied("payload not armed")
        elif action == "CINCH_NET":
            if self.engagement_mode != CRADLE:
                return self._denied("CINCH is CRADLE-mode only")
            if self.estop or not self.armed:
                return self._denied("payload not armed")
        elif action == "CORD_CUT":
            if self.engagement_mode != TRAWLER:
                return self._denied("CORD-CUT is TRAWLER-mode only")
            if self.estop or not self.armed:
                return self._denied("payload not armed")
        elif action == "RELEASE":
            if self.estop or not self.armed:
                return self._denied("payload not armed")
        elif action == "RTH":
            self.mode = "RTH"
        self.last_action = action
        return {"type": action, "setpoint": self.setpoint()}

    def setpoint(self) -> dict:
        """Compact signed-setpoint payload sent to the vehicle each frame."""
        return {
            "roll": round(self.roll, 3), "pitch": round(self.pitch, 3),
            "yaw": round(self.yaw, 3), "throttle": round(self.throttle, 3),
            "net_pan": round(self.net_pan, 1), "net_tilt": round(self.net_tilt, 1),
            "armed": self.armed, "mode": self.mode,
            "engagement_mode": self.engagement_mode,
        }

    def _denied(self, reason: str) -> dict:
        self.last_action = f"DENIED:{reason}"
        return {"type": "DENIED", "reason": reason}
