"""MAVLink 2 message signing (command-link authentication).

Implements the MAVLink 2 message-signing scheme exactly as specified by the
official MAVLink guide, so it interoperates with PX4 / ArduPilot / pymavlink:

    https://mavlink.io/en/guide/message_signing.html

Why this matters for TaloNet: the command-and-control (C2) uplink is the most
attractive target for an adversary -- if they can inject a forged ``COMMAND_LONG``
they could try to redirect the interceptor. Message signing lets the vehicle
*reject any command that is not signed with the shared 32-byte secret key*, and
the monotonic timestamp rule defeats replay attacks. (Signing authenticates;
it does not encrypt the payload -- per the spec.)

Spec summary implemented here:
  * A signed packet appends 13 bytes: ``link_id`` (1) + ``timestamp`` (6, 48-bit
    little-endian) + ``signature`` (6).
  * ``signature = sha256_48(secret_key + packet + link_id + timestamp)`` where
    ``packet`` is the full frame header+payload+CRC (without the signature) and
    ``sha256_48`` is the first 48 bits (6 bytes) of the SHA-256 digest.
  * ``timestamp`` is in units of 10 microseconds since 2015-01-01 00:00 UTC
    (unix offset 1420070400 s) and must strictly increase per
    ``(SystemID, ComponentID, LinkID)`` stream.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

#: Unix seconds at 2015-01-01 00:00:00 UTC (MAVLink signing epoch).
MAVLINK_SIGNING_EPOCH_OFFSET = 1420070400
SECRET_KEY_LEN = 32
SIGNATURE_BLOCK_LEN = 13  # link_id(1) + timestamp(6) + signature(6)


def mavlink_timestamp(unix_seconds: float | None = None) -> int:
    """Current MAVLink signing timestamp (48-bit, units of 10 microseconds)."""
    if unix_seconds is None:
        unix_seconds = time.time()
    ticks = int((unix_seconds - MAVLINK_SIGNING_EPOCH_OFFSET) * 1e5)
    if ticks < 0:
        ticks = 0
    return ticks & 0xFFFFFFFFFFFF  # clamp to 48 bits


def _sha256_48(secret_key: bytes, packet: bytes, link_id: int, timestamp: int) -> bytes:
    h = hashlib.sha256()
    h.update(secret_key)
    h.update(packet)
    h.update(bytes([link_id & 0xFF]))
    h.update(timestamp.to_bytes(6, "little"))
    return h.digest()[:6]


def make_signature_block(secret_key: bytes, packet: bytes, link_id: int, timestamp: int) -> bytes:
    """Return the 13-byte signature block for an (unsigned) MAVLink 2 ``packet``."""
    if len(secret_key) != SECRET_KEY_LEN:
        raise ValueError("MAVLink signing secret key must be exactly 32 bytes")
    sig = _sha256_48(secret_key, packet, link_id, timestamp)
    return bytes([link_id & 0xFF]) + timestamp.to_bytes(6, "little") + sig


def sign_packet(secret_key: bytes, packet: bytes, link_id: int, timestamp: int) -> bytes:
    """Append a valid signature block to ``packet`` and return the signed frame."""
    return packet + make_signature_block(secret_key, packet, link_id, timestamp)


@dataclass
class VerifyResult:
    valid: bool
    reason: str
    timestamp: int = 0


class MavlinkSigner:
    """Outgoing-side signer with a strictly monotonic timestamp."""

    def __init__(self, secret_key: bytes, link_id: int = 0) -> None:
        if len(secret_key) != SECRET_KEY_LEN:
            raise ValueError("secret key must be 32 bytes")
        self.secret_key = secret_key
        self.link_id = link_id
        self._last_ts = 0

    def sign(self, packet: bytes, now_unix: float | None = None) -> bytes:
        ts = mavlink_timestamp(now_unix)
        if ts <= self._last_ts:  # enforce strict monotonicity per the spec
            ts = self._last_ts + 1
        self._last_ts = ts
        return sign_packet(self.secret_key, packet, self.link_id, ts)


class MavlinkVerifier:
    """Incoming-side verifier: checks the signature and rejects replays.

    A packet is accepted only if (a) the 48-bit signature recomputes correctly
    with the shared key, and (b) its timestamp strictly exceeds the last
    accepted timestamp for that ``(sysid, compid, link_id)`` stream.
    """

    def __init__(self, secret_key: bytes, max_clock_skew_ticks: int = 6_000_000) -> None:
        if len(secret_key) != SECRET_KEY_LEN:
            raise ValueError("secret key must be 32 bytes")
        self.secret_key = secret_key
        # Allowed future skew (default ~60 s in 10 us ticks) to bound forgeries.
        self.max_clock_skew_ticks = max_clock_skew_ticks
        self._last_ts: dict[tuple[int, int, int], int] = {}

    def verify(self, signed_packet: bytes, sysid: int, compid: int, now_unix: float | None = None) -> VerifyResult:
        if len(signed_packet) <= SIGNATURE_BLOCK_LEN:
            return VerifyResult(False, "frame too short to be signed")
        packet, block = signed_packet[:-SIGNATURE_BLOCK_LEN], signed_packet[-SIGNATURE_BLOCK_LEN:]
        link_id = block[0]
        timestamp = int.from_bytes(block[1:7], "little")
        sig = block[7:13]

        expected = _sha256_48(self.secret_key, packet, link_id, timestamp)
        if not _consttime_eq(expected, sig):
            return VerifyResult(False, "bad signature: unauthenticated or tampered packet", timestamp)

        # Reject far-future timestamps (limits a captured-key forgery window).
        now_ts = mavlink_timestamp(now_unix)
        if timestamp > now_ts + self.max_clock_skew_ticks:
            return VerifyResult(False, "timestamp too far in the future", timestamp)

        stream = (sysid, compid, link_id)
        last = self._last_ts.get(stream, -1)
        if timestamp <= last:
            return VerifyResult(False, "replay/old timestamp rejected", timestamp)

        self._last_ts[stream] = timestamp
        return VerifyResult(True, "signature valid, timestamp fresh", timestamp)


def _consttime_eq(a: bytes, b: bytes) -> bool:
    import hmac as _hmac
    return _hmac.compare_digest(a, b)
