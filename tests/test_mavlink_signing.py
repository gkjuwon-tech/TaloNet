import hashlib
import unittest

from defense.link.mavlink_signing import (
    MAVLINK_SIGNING_EPOCH_OFFSET,
    MavlinkSigner,
    MavlinkVerifier,
    make_signature_block,
    mavlink_timestamp,
    sign_packet,
)

KEY = bytes(range(32))
PACKET = bytes.fromhex("fd0900000142010a000102030405060708") + b"\xab\xcd"  # fake hdr+payload+crc
NOW = 1_700_000_000.0


class MavlinkSigningSpecTest(unittest.TestCase):
    def test_signature_matches_spec_formula(self):
        # signature = sha256_48(secret + packet + link_id + timestamp[6 LE])
        ts = 123456789
        link_id = 3
        block = make_signature_block(KEY, PACKET, link_id, ts)
        self.assertEqual(len(block), 13)
        self.assertEqual(block[0], link_id)
        self.assertEqual(int.from_bytes(block[1:7], "little"), ts)
        expected_sig = hashlib.sha256(
            KEY + PACKET + bytes([link_id]) + ts.to_bytes(6, "little")
        ).digest()[:6]
        self.assertEqual(block[7:13], expected_sig)

    def test_timestamp_epoch(self):
        self.assertEqual(mavlink_timestamp(MAVLINK_SIGNING_EPOCH_OFFSET), 0)
        # 1 second after epoch == 100000 ticks of 10 microseconds
        self.assertEqual(mavlink_timestamp(MAVLINK_SIGNING_EPOCH_OFFSET + 1), 100_000)

    def test_secret_key_length_enforced(self):
        with self.assertRaises(ValueError):
            make_signature_block(b"tooshort", PACKET, 0, 1)


class MavlinkRoundTripTest(unittest.TestCase):
    def test_valid_signature_accepted(self):
        signer = MavlinkSigner(KEY, link_id=1)
        verifier = MavlinkVerifier(KEY)
        signed = signer.sign(PACKET, now_unix=NOW)
        res = verifier.verify(signed, sysid=1, compid=1, now_unix=NOW)
        self.assertTrue(res.valid, res.reason)

    def test_tampered_packet_rejected(self):
        verifier = MavlinkVerifier(KEY)
        signed = sign_packet(KEY, PACKET, link_id=0, timestamp=mavlink_timestamp(NOW))
        tampered = bytearray(signed)
        tampered[5] ^= 0xFF  # flip a payload byte
        res = verifier.verify(bytes(tampered), sysid=1, compid=1, now_unix=NOW)
        self.assertFalse(res.valid)
        self.assertIn("signature", res.reason)

    def test_wrong_key_rejected(self):
        verifier = MavlinkVerifier(bytes([0xAA]) * 32)
        signed = sign_packet(KEY, PACKET, 0, mavlink_timestamp(NOW))
        res = verifier.verify(signed, 1, 1, now_unix=NOW)
        self.assertFalse(res.valid)

    def test_replay_rejected(self):
        signer = MavlinkSigner(KEY, link_id=2)
        verifier = MavlinkVerifier(KEY)
        signed = signer.sign(PACKET, now_unix=NOW)
        first = verifier.verify(signed, 1, 1, now_unix=NOW)
        replay = verifier.verify(signed, 1, 1, now_unix=NOW)
        self.assertTrue(first.valid)
        self.assertFalse(replay.valid)
        self.assertIn("replay", replay.reason)

    def test_monotonic_timestamps(self):
        signer = MavlinkSigner(KEY)
        a = signer.sign(PACKET, now_unix=NOW)
        b = signer.sign(PACKET, now_unix=NOW)  # same wall clock -> must still increase
        ta = int.from_bytes(a[-12:-6], "little")
        tb = int.from_bytes(b[-12:-6], "little")
        self.assertGreater(tb, ta)

    def test_future_timestamp_rejected(self):
        verifier = MavlinkVerifier(KEY, max_clock_skew_ticks=1000)
        far_future = mavlink_timestamp(NOW) + 10_000_000
        signed = sign_packet(KEY, PACKET, 0, far_future)
        res = verifier.verify(signed, 1, 1, now_unix=NOW)
        self.assertFalse(res.valid)
        self.assertIn("future", res.reason)


if __name__ == "__main__":
    unittest.main()
