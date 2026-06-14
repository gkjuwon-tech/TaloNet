"""RF data-link security primitives (authentication, anti-replay, integrity).

Transport-agnostic building blocks that harden any radio link (telemetry,
mesh, video C2) against injection, replay and jamming. They are independent of
MAVLink so they can wrap a custom link layer too.

  * :class:`AuthenticatedChannel` -- HMAC-SHA256 frame authentication with an
    explicit, authenticated sequence number. This is the same construction used
    by IPsec/ESP and TLS record MACs (encrypt-then-MAC style auth tag), applied
    to radio frames. We authenticate (not encrypt) by default, mirroring the
    MAVLink signing philosophy where integrity/authenticity is the priority.
  * :class:`ReplayWindow` -- sliding-window anti-replay, modelled on the IPsec
    anti-replay window (RFC 4303 Appendix A / RFC 6479). Tolerates limited
    reordering while rejecting duplicates and stale frames.
  * :class:`LinkIntegrityMonitor` -- statistical jamming / takeover detector:
    watches CRC-error bursts (jamming) and RSSI step changes from a stronger
    nearby emitter (overpowering / meaconing attempt).

Defensive only -- nothing here transmits on, jams, or spoofs any frequency.
"""

from __future__ import annotations

import hmac
import struct
from dataclasses import dataclass


class ReplayWindow:
    """Sliding-window anti-replay (RFC 6479-style bitmap)."""

    def __init__(self, window_size: int = 64) -> None:
        self.window_size = window_size
        self._highest = 0
        self._bitmap = 0
        self._seen_first = False

    def check_and_update(self, seq: int) -> bool:
        """Return True if ``seq`` is fresh (and record it); False if replayed/stale."""
        if seq <= 0:
            return False
        if not self._seen_first:
            self._seen_first = True
            self._highest = seq
            self._bitmap = 1
            return True
        if seq > self._highest:
            shift = seq - self._highest
            if shift >= self.window_size:
                self._bitmap = 1
            else:
                self._bitmap = ((self._bitmap << shift) | 1) & ((1 << self.window_size) - 1)
            self._highest = seq
            return True
        offset = self._highest - seq
        if offset >= self.window_size:
            return False  # too old
        mask = 1 << offset
        if self._bitmap & mask:
            return False  # duplicate
        self._bitmap |= mask
        return True


@dataclass
class Frame:
    seq: int
    payload: bytes


class AuthenticatedChannel:
    """HMAC-authenticated, anti-replay radio framing.

    Wire format: ``seq (8B big-endian) || payload || tag (tag_len B)`` where
    ``tag = HMAC-SHA256(key, seq || payload)[:tag_len]``.
    """

    def __init__(self, key: bytes, tag_len: int = 16, window_size: int = 64) -> None:
        if len(key) < 16:
            raise ValueError("link key should be at least 16 bytes")
        self.key = key
        self.tag_len = tag_len
        self._tx_seq = 0
        self._replay = ReplayWindow(window_size)

    def _tag(self, seq: int, payload: bytes) -> bytes:
        msg = struct.pack(">Q", seq) + payload
        return hmac.new(self.key, msg, "sha256").digest()[: self.tag_len]

    def wrap(self, payload: bytes) -> bytes:
        self._tx_seq += 1
        seq = self._tx_seq
        return struct.pack(">Q", seq) + payload + self._tag(seq, payload)

    def unwrap(self, frame: bytes) -> Frame | None:
        """Authenticate and de-replay an incoming frame. Returns None if rejected."""
        if len(frame) < 8 + self.tag_len:
            return None
        seq = struct.unpack(">Q", frame[:8])[0]
        payload = frame[8:-self.tag_len]
        tag = frame[-self.tag_len:]
        if not hmac.compare_digest(self._tag(seq, payload), tag):
            return None  # forged or corrupted
        if not self._replay.check_and_update(seq):
            return None  # replay / stale
        return Frame(seq, payload)


@dataclass
class LinkStatus:
    jamming_suspected: bool
    takeover_suspected: bool
    detail: str = ""


class LinkIntegrityMonitor:
    """Detect jamming (CRC error bursts) and takeover (RSSI step from new emitter)."""

    def __init__(
        self,
        crc_error_rate_threshold: float = 0.30,
        rssi_step_db: float = 12.0,
        history: int = 50,
    ) -> None:
        self.crc_error_rate_threshold = crc_error_rate_threshold
        self.rssi_step_db = rssi_step_db
        self.history = history
        self._rssi: list[float] = []

    def update(self, rssi_dbm: float, crc_ok: bool, crc_fail: bool) -> LinkStatus:
        total = crc_ok + crc_fail
        crc_rate = (crc_fail / total) if total else 0.0
        jamming = crc_rate >= self.crc_error_rate_threshold

        takeover = False
        detail = f"crc_err_rate={crc_rate:.2f}"
        if self._rssi:
            baseline = sum(self._rssi) / len(self._rssi)
            if rssi_dbm - baseline >= self.rssi_step_db:
                takeover = True
                detail += f" rssi_step=+{rssi_dbm - baseline:.1f}dB"
        self._rssi.append(rssi_dbm)
        if len(self._rssi) > self.history:
            self._rssi.pop(0)
        return LinkStatus(jamming, takeover, detail)
