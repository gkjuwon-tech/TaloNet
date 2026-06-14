"""Receiver Autonomous Integrity Monitoring (RAIM).

Snapshot, residual-based RAIM with Fault Detection and Exclusion (FDE). This is
the classical least-squares-residuals (LSR) RAIM method: compute the weighted
least-squares position solution, form the sum-of-squared-errors (SSE) test
statistic, and compare it against a chi-square threshold. If a fault is
detected, the most likely faulty measurement is excluded and the solution is
recomputed.

References (verified, public):
  * Parkinson & Axelrad, "Autonomous GPS Integrity Monitoring Using the
    Pseudorange Residual," NAVIGATION, 1988.
  * RTCA DO-229 (WAAS MOPS) RAIM/FDE definitions.
  * Stanford GPS Lab, "Providing Continuity and Integrity in the presence of
    spoofing" (IONGNSS 2021) which extends RAIM residual equations to spoofing.
  * Open-source reference: github.com/MichaelBeechan/RAIM_PANG_NAV

RAIM was designed to catch *single* faulted satellites; it is included here as
one independent layer of the anti-spoofing stack. A coordinated spoofer that
forges a self-consistent constellation will not necessarily trip RAIM, which is
exactly why this module is combined with OSNMA authentication, innovation
gating against the IMU, and C/N0 monitoring in :mod:`defense.monitor`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..linalg import weighted_least_squares


def _gammln(x: float) -> float:
    # Lanczos approximation of ln(Gamma(x)).
    cof = [
        76.18009172947146, -86.50532032941677, 24.01409824083091,
        -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5,
    ]
    y = x
    tmp = x + 5.5
    tmp -= (x + 0.5) * math.log(tmp)
    ser = 1.000000000190015
    for c in cof:
        y += 1.0
        ser += c / y
    return -tmp + math.log(2.5066282746310005 * ser / x)


def _gammp(a: float, x: float) -> float:
    """Regularized lower incomplete gamma function P(a, x)."""
    if x < 0.0 or a <= 0.0:
        raise ValueError("invalid arguments to gammp")
    if x == 0.0:
        return 0.0
    if x < a + 1.0:  # series expansion
        ap = a
        total = 1.0 / a
        delta = total
        for _ in range(1000):
            ap += 1.0
            delta *= x / ap
            total += delta
            if abs(delta) < abs(total) * 1e-12:
                break
        return total * math.exp(-x + a * math.log(x) - _gammln(a))
    # continued fraction for the complement Q(a, x)
    b = x + 1.0 - a
    c = 1.0 / 1.0e-30
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    q = math.exp(-x + a * math.log(x) - _gammln(a)) * h
    return 1.0 - q


def chi2_cdf(x: float, dof: int) -> float:
    """CDF of the chi-square distribution with ``dof`` degrees of freedom."""
    if dof <= 0:
        raise ValueError("dof must be positive")
    if x <= 0.0:
        return 0.0
    return _gammp(dof / 2.0, x / 2.0)


def chi2_threshold(p_false_alarm: float, dof: int) -> float:
    """Detection threshold T such that P(SSE > T | no fault) = p_false_alarm."""
    if not 0.0 < p_false_alarm < 1.0:
        raise ValueError("p_false_alarm must be in (0, 1)")
    target = 1.0 - p_false_alarm
    lo, hi = 0.0, max(50.0, dof * 10.0)
    while chi2_cdf(hi, dof) < target:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if chi2_cdf(mid, dof) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@dataclass
class RaimResult:
    solution: list[float]
    sse: float
    threshold: float
    fault_detected: bool
    excluded_index: int | None = None
    n_measurements: int = 0
    dof: int = 0
    used_indices: list[int] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not self.fault_detected or self.excluded_index is not None


class RaimMonitor:
    """Least-squares-residuals RAIM with single-fault exclusion.

    Parameters
    ----------
    p_false_alarm:
        Continuity / false-alarm probability used to set the chi-square
        detection threshold (DO-229 uses ~1/15000 per sample for en-route).
    n_states:
        Number of estimated states (4 for single-constellation: x, y, z, dt).
    """

    def __init__(self, p_false_alarm: float = 1.0 / 15000.0, n_states: int = 4) -> None:
        self.p_false_alarm = p_false_alarm
        self.n_states = n_states

    def _solve(self, geometry, residual_meas, weights):
        x_hat, post_residuals, _ = weighted_least_squares(geometry, residual_meas, weights)
        sse = 0.0
        for r, w in zip(post_residuals, weights):
            sse += w * r * r
        return x_hat, post_residuals, sse

    def check(self, geometry, residual_meas, weights=None) -> RaimResult:
        """Run RAIM on a measurement epoch.

        ``geometry`` is the m x n observation (design) matrix of line-of-sight
        unit vectors plus a clock column; ``residual_meas`` is the m-vector of
        (measured - predicted) pseudoranges; ``weights`` are 1/sigma^2 weights.
        """
        m = len(geometry)
        weights = weights or [1.0] * m
        dof = m - self.n_states
        if dof < 1:
            # Not enough redundancy to detect a fault.
            x_hat, _, _ = self._solve(geometry, residual_meas, weights)
            return RaimResult(x_hat, 0.0, math.inf, False, None, m, max(dof, 0),
                              list(range(m)))

        x_hat, _, sse = self._solve(geometry, residual_meas, weights)
        threshold = chi2_threshold(self.p_false_alarm, dof)
        if sse <= threshold:
            return RaimResult(x_hat, sse, threshold, False, None, m, dof, list(range(m)))

        # Fault detected -> attempt single-measurement exclusion (FDE).
        best_idx, best_sse, best_sol, best_used = None, math.inf, x_hat, list(range(m))
        for drop in range(m):
            keep = [i for i in range(m) if i != drop]
            sub_geo = [geometry[i] for i in keep]
            sub_meas = [residual_meas[i] for i in keep]
            sub_w = [weights[i] for i in keep]
            if len(keep) - self.n_states < 0:
                continue
            sol, _, sub_sse = self._solve(sub_geo, sub_meas, sub_w)
            if sub_sse < best_sse:
                best_idx, best_sse, best_sol, best_used = drop, sub_sse, sol, keep

        sub_dof = (m - 1) - self.n_states
        excluded = best_idx
        if sub_dof >= 1 and best_idx is not None:
            sub_threshold = chi2_threshold(self.p_false_alarm, sub_dof)
            if best_sse > sub_threshold:
                # Even after exclusion the solution is inconsistent: do not trust.
                excluded = None
        return RaimResult(best_sol, sse, threshold, True, excluded, m, dof, best_used)
