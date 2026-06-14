import unittest

from defense.gnss.osnma_adapter import (
    OsnmaAuthenticator,
    compute_mac,
    tesla_key_chain,
    verify_mac,
    verify_tesla_key,
)


class TeslaChainTest(unittest.TestCase):
    def test_chain_is_one_way(self):
        chain = tesla_key_chain(b"tip-secret-key-material", length=10)
        # K_i = H(K_{i+1}); so hashing K_{i+1} once gives K_i.
        from defense.gnss.osnma_adapter import hash_once
        for i in range(len(chain) - 1):
            self.assertEqual(hash_once(chain[i + 1]), chain[i])

    def test_verify_key_against_anchor(self):
        chain = tesla_key_chain(b"seed", length=8)
        anchor = chain[0]
        self.assertTrue(verify_tesla_key(chain[5], 5, anchor))
        self.assertFalse(verify_tesla_key(b"forged-key-not-in-chain", 5, anchor))


class MacTest(unittest.TestCase):
    def test_mac_roundtrip(self):
        key = b"some-tesla-key"
        tag = compute_mac(key, b"nav-data", tag_len=16)
        self.assertTrue(verify_mac(key, b"nav-data", tag))
        self.assertFalse(verify_mac(key, b"tampered", tag))


class OsnmaAuthenticatorTest(unittest.TestCase):
    def setUp(self):
        self.chain = tesla_key_chain(b"galileo-test-seed", length=16)
        self.auth = OsnmaAuthenticator(anchor_key=self.chain[0])

    def test_authentic_nav_data_passes(self):
        idx = 7
        key = self.chain[idx]
        nav = b"ephemeris+clock-block"
        tag = compute_mac(key, nav)
        res = self.auth.authenticate(nav, tag, key, idx)
        self.assertTrue(res.authenticated, res.reason)

    def test_forged_key_fails(self):
        nav = b"ephemeris"
        forged = b"x" * 32
        tag = compute_mac(forged, nav)
        res = self.auth.authenticate(nav, tag, forged, 7)
        self.assertFalse(res.authenticated)
        self.assertIn("anchor", res.reason)

    def test_tampered_navdata_fails(self):
        idx = 4
        key = self.chain[idx]
        tag = compute_mac(key, b"original-nav")
        res = self.auth.authenticate(b"spoofed-nav", tag, key, idx)
        self.assertFalse(res.authenticated)
        self.assertIn("MAC", res.reason)


if __name__ == "__main__":
    unittest.main()
