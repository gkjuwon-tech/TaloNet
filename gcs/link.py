"""Command link from the GCS cockpit to the vehicle.

``LoopbackLink`` is an in-process link for development/testing and for the
offline cockpit: it sequences commands, optionally **HMAC-signs** each frame and
verifies it vehicle-side (a stand-in for MAVLink 2 message signing — see
``defense/link/mavlink_signing.py`` / ``defense/link/rf_link_security.py`` for
the real, audited command-authentication path), and records every frame so a
test or the HUD can inspect what was sent. Unsigned frames or replays are
rejected when a key is configured.

Stdlib only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field


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
