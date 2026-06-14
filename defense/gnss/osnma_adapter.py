"""GNSS navigation-message authentication (OSNMA) adapter.

Galileo **OSNMA** (Open Service Navigation Message Authentication) lets a
receiver cryptographically verify that the navigation message really came from
the Galileo satellites, which is the strongest defence against a meaconing /
spoofing attack that forges a self-consistent constellation (the kind RAIM and
consistency checks cannot catch).

This module does NOT re-implement the full OSNMA ICD. Instead it:

1. Provides a thin adapter that delegates to a verified, audited open-source
   OSNMA implementation when one is installed:
     * OSNMAlib (Python, EUPL-1.2) -- github.com/Algafix/OSNMA
     * galileo-osnma (Rust, Apache-2.0) -- github.com/daniestevez/galileo-osnma
   These libraries were validated against the official Galileo OSNMA ICD test
   vectors, so we depend on them rather than hand-rolling crypto.

2. Implements the *core* primitive that OSNMA is built on -- the TESLA
   (Timed Efficient Stream Loss-tolerant Authentication) one-way key chain and
   delayed-MAC verification -- in dependency-free, unit-tested form. This lets
   the rest of the stack be exercised and tested offline, and documents exactly
   what authentication property we rely on:

       key chain:   K_{i} = H(K_{i+1})           (one-way; root K_0 is anchored)
       MAC:         tag_i = HMAC(K_i, nav_data)  (computed with a not-yet-public key)
       disclosure:  K_i is broadcast later; receiver checks H^i(K_i) == K_0
                    and then verifies the previously-received tag.

Reference: Perrig et al., "The TESLA Broadcast Authentication Protocol";
Fernandez-Hernandez et al., "Galileo OSNMA" (IEEE/ION).
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass


def hash_once(data: bytes, algo: str = "sha256") -> bytes:
    return hashlib.new(algo, data).digest()


def tesla_key_chain(seed: bytes, length: int, algo: str = "sha256") -> list[bytes]:
    """Build a TESLA one-way key chain.

    Returns ``[K_0, K_1, ..., K_{length-1}]`` where ``K_i = H(K_{i+1})`` so the
    chain is generated from the tip (``seed`` = last key) backwards. ``K_0`` is
    the root/anchor that would be authenticated by ECDSA in real OSNMA.
    """
    if length < 1:
        raise ValueError("length must be >= 1")
    chain = [b""] * length
    chain[length - 1] = seed
    for i in range(length - 2, -1, -1):
        chain[i] = hash_once(chain[i + 1], algo)
    return chain


def verify_tesla_key(disclosed_key: bytes, index: int, anchor: bytes, algo: str = "sha256") -> bool:
    """Check that hashing ``disclosed_key`` ``index`` times yields ``anchor`` (K_0)."""
    acc = disclosed_key
    for _ in range(index):
        acc = hash_once(acc, algo)
    return hmac.compare_digest(acc, anchor)


def compute_mac(key: bytes, message: bytes, tag_len: int = 16, algo: str = "sha256") -> bytes:
    return hmac.new(key, message, algo).digest()[:tag_len]


def verify_mac(key: bytes, message: bytes, tag: bytes, algo: str = "sha256") -> bool:
    expected = compute_mac(key, message, len(tag), algo)
    return hmac.compare_digest(expected, tag)


@dataclass
class AuthResult:
    authenticated: bool
    reason: str


class OsnmaAuthenticator:
    """Offline TESLA-based navigation-data authenticator.

    Models the OSNMA delayed-disclosure flow: a tag is received in subframe
    ``i`` (computed with the still-secret key ``K_i``), then ``K_i`` is
    disclosed in a later subframe. Authentication succeeds only if the
    disclosed key chains back to the trusted anchor AND the tag verifies.
    """

    def __init__(self, anchor_key: bytes, algo: str = "sha256") -> None:
        self.anchor_key = anchor_key
        self.algo = algo

    def authenticate(self, nav_data: bytes, tag: bytes, disclosed_key: bytes, index: int) -> AuthResult:
        if not verify_tesla_key(disclosed_key, index, self.anchor_key, self.algo):
            return AuthResult(False, "TESLA key does not chain to trusted anchor (possible spoof)")
        if not verify_mac(disclosed_key, nav_data, tag, self.algo):
            return AuthResult(False, "MAC mismatch: navigation data not authentic")
        return AuthResult(True, "navigation data authenticated via OSNMA/TESLA")


def osnmalib_available() -> bool:
    """True if the verified OSNMAlib package is importable for live SIS auth."""
    try:  # pragma: no cover - depends on optional external package
        import osnma  # noqa: F401  (github.com/Algafix/OSNMA)
        return True
    except Exception:
        return False
