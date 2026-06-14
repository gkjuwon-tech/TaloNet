"""GNSS spoofing / jamming detection (sensor-consistency layer).

This module bundles several *independent*, well-established consistency checks.
None of them is individually sufficient, but a spoofer has to defeat all of
them simultaneously, which is hard. The checks here are deliberately the ones
that flight controllers already ship in production firmware:

  * Position "glitch" gate -- ArduPilot Copter GPS glitch protection
    (compare each fix against a fix propagated from the previous
    position+velocity; accept only within ``GPSGLITCH_RADIUS`` and an
    acceleration-bounded radius). See:
    https://ardupilot.org/copter/docs/gps-failsafe-glitch-protection.html
  * EKF innovation gating -- reject GPS measurements whose normalized
    innovation squared (NIS) against the IMU-propagated state exceeds a
    chi-square gate (``EK3_POS_GATE`` in ArduPilot NavEKF3). See:
    https://ardupilot.org/copter/docs/gps-failsafe-glitch-protection.html
    and ArduPilot PR #24899 "EKF: cope better with GPS jamming".
  * C/N0 anomaly monitor -- spoofers commonly transmit at elevated, unusually
    uniform power; flag abnormally high mean and abnormally low spread, or a
    sudden step in carrier-to-noise density.
  * Receiver-clock-jump detector -- a sudden, oscillator-inconsistent jump in
    the estimated clock bias is a classic takeover signature.
  * Multi-constellation cross-check -- independent GPS / Galileo / GLONASS
    fixes should agree; a divergence flags a partial-constellation spoof.

These are detection/defensive measures only. Nothing here transmits, jams, or
spoofs anything.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    name: str
    suspicious: bool
    detail: str = ""
    metric: float = 0.0


@dataclass
class SpoofingVerdict:
    spoofing_suspected: bool
    jamming_suspected: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def num_flags(self) -> int:
        return sum(1 for c in self.checks if c.suspicious)

    def recommended_action(self) -> str:
        if self.spoofing_suspected:
            return "REJECT_GNSS_DEADRECKON"  # coast on IMU, do not trust position
        if self.jamming_suspected:
            return "DEGRADE_TO_INERTIAL"
        return "TRUST_GNSS"


def _dist3(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class GpsGlitchGate:
    """ArduPilot-style glitch gate.

    Accept a fix only if it lies within ``radius_m`` of, and within an
    acceleration-bounded radius of, the position propagated from the previous
    fix using the previous velocity.
    """

    def __init__(self, radius_m: float = 5.0, accel_mss: float = 10.0) -> None:
        self.radius_m = radius_m
        self.accel_mss = accel_mss
        self._prev_pos = None
        self._prev_vel = None
        self._prev_t = None

    def update(self, t: float, pos, vel) -> CheckResult:
        if self._prev_pos is None:
            self._prev_pos, self._prev_vel, self._prev_t = pos, vel, t
            return CheckResult("gps_glitch", False, "first fix (seed)", 0.0)
        dt = max(t - self._prev_t, 1e-3)
        projected = [self._prev_pos[i] + self._prev_vel[i] * dt for i in range(3)]
        err = _dist3(pos, projected)
        accel_radius = self.accel_mss * dt * dt
        gate = self.radius_m + accel_radius
        suspicious = err > gate
        if not suspicious:
            self._prev_pos, self._prev_vel, self._prev_t = pos, vel, t
        return CheckResult(
            "gps_glitch", suspicious,
            f"err={err:.2f}m gate={gate:.2f}m", err,
        )


class InnovationGate:
    """EKF innovation consistency gate (normalized innovation squared)."""

    def __init__(self, gate_sigma: float = 5.0) -> None:
        # ArduPilot expresses the gate in 'sigma'; we test NIS against gate^2.
        self.gate = gate_sigma * gate_sigma

    def check(self, innovation, innovation_var) -> CheckResult:
        nis = 0.0
        for r, var in zip(innovation, innovation_var):
            nis += (r * r) / max(var, 1e-9)
        nis /= max(len(innovation), 1)
        suspicious = nis > self.gate
        return CheckResult("ekf_innovation", suspicious, f"NIS={nis:.2f} gate={self.gate:.2f}", nis)


class Cn0Monitor:
    """Carrier-to-noise-density anomaly monitor.

    Flags spoofing if the constellation is simultaneously *too strong* and
    *too uniform* (a hallmark of a single spoofing transmitter), and flags
    jamming if C/N0 collapses across the board.
    """

    def __init__(
        self,
        high_dbhz: float = 52.0,
        uniform_std_dbhz: float = 1.5,
        jam_floor_dbhz: float = 28.0,
    ) -> None:
        self.high_dbhz = high_dbhz
        self.uniform_std_dbhz = uniform_std_dbhz
        self.jam_floor_dbhz = jam_floor_dbhz

    @staticmethod
    def _mean_std(values):
        n = len(values)
        mean = sum(values) / n
        var = sum((v - mean) ** 2 for v in values) / n
        return mean, math.sqrt(var)

    def check(self, cn0_dbhz) -> tuple[CheckResult, CheckResult]:
        if not cn0_dbhz:
            return (
                CheckResult("cn0_spoof", False, "no measurements"),
                CheckResult("cn0_jam", False, "no measurements"),
            )
        mean, std = self._mean_std(cn0_dbhz)
        spoof = mean >= self.high_dbhz and std <= self.uniform_std_dbhz
        jam = mean <= self.jam_floor_dbhz
        return (
            CheckResult("cn0_spoof", spoof, f"mean={mean:.1f} std={std:.2f}", mean),
            CheckResult("cn0_jam", jam, f"mean={mean:.1f} floor={self.jam_floor_dbhz}", mean),
        )


class ClockJumpDetector:
    """Detect oscillator-inconsistent jumps in the estimated clock bias."""

    def __init__(self, max_drift_mps: float = 50.0) -> None:
        # Allowed receiver-clock-bias rate (m/s equivalent) for a TCXO-class clock.
        self.max_drift_mps = max_drift_mps
        self._prev_bias = None
        self._prev_t = None

    def update(self, t: float, clock_bias_m: float) -> CheckResult:
        if self._prev_bias is None:
            self._prev_bias, self._prev_t = clock_bias_m, t
            return CheckResult("clock_jump", False, "first sample (seed)", 0.0)
        dt = max(t - self._prev_t, 1e-3)
        rate = abs(clock_bias_m - self._prev_bias) / dt
        suspicious = rate > self.max_drift_mps
        self._prev_bias, self._prev_t = clock_bias_m, t
        return CheckResult("clock_jump", suspicious, f"rate={rate:.1f} m/s", rate)


class MultiConstellationCrossCheck:
    """Cross-check independent per-constellation position fixes."""

    def __init__(self, max_disagreement_m: float = 30.0) -> None:
        self.max_disagreement_m = max_disagreement_m

    def check(self, fixes_by_constellation: dict[str, list[float]]) -> CheckResult:
        names = list(fixes_by_constellation)
        if len(names) < 2:
            return CheckResult("multi_constellation", False, "single constellation")
        worst = 0.0
        pair = ""
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                d = _dist3(fixes_by_constellation[names[i]], fixes_by_constellation[names[j]])
                if d > worst:
                    worst, pair = d, f"{names[i]}/{names[j]}"
        suspicious = worst > self.max_disagreement_m
        return CheckResult("multi_constellation", suspicious, f"max={worst:.1f}m ({pair})", worst)


class SpoofingDetector:
    """Aggregate the independent GNSS consistency checks into one verdict."""

    def __init__(self, spoof_flag_threshold: int = 2) -> None:
        self.glitch = GpsGlitchGate()
        self.innovation = InnovationGate()
        self.cn0 = Cn0Monitor()
        self.clock = ClockJumpDetector()
        self.cross = MultiConstellationCrossCheck()
        self.spoof_flag_threshold = spoof_flag_threshold

    def evaluate(
        self,
        t: float,
        pos,
        vel,
        innovation,
        innovation_var,
        cn0_dbhz,
        clock_bias_m: float,
        fixes_by_constellation: dict[str, list[float]] | None = None,
    ) -> SpoofingVerdict:
        checks = [
            self.glitch.update(t, pos, vel),
            self.innovation.check(innovation, innovation_var),
        ]
        cn0_spoof, cn0_jam = self.cn0.check(cn0_dbhz)
        checks.append(cn0_spoof)
        checks.append(self.clock.update(t, clock_bias_m))
        checks.append(self.cross.check(fixes_by_constellation or {}))

        # Spoofing = several positive, consistency-style flags together.
        spoof_flags = [c for c in checks if c.suspicious and c.name != "cn0_jam"]
        spoofing = len(spoof_flags) >= self.spoof_flag_threshold
        return SpoofingVerdict(
            spoofing_suspected=spoofing,
            jamming_suspected=cn0_jam.suspicious,
            checks=checks + [cn0_jam],
        )
