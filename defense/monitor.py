"""Integrated navigation & link defence monitor.

Fuses the independent defensive layers into a single, explainable verdict that
the flight stack can act on. This is the glue that "applies the defence code to
ours": the Geulmae interceptor calls :meth:`DefenseMonitor.assess` every epoch
and uses the returned :class:`NavSecurityState` to decide whether to keep
trusting GNSS, coast on inertial dead-reckoning, or fall back to return-to-home.

Defence-in-depth layers combined here:
  1. OSNMA / TESLA navigation-message authentication  (cryptographic truth)
  2. RAIM fault detection & exclusion                 (geometric consistency)
  3. GNSS spoofing/jamming consistency checks         (sensor consistency)
  4. C2 link authentication + anti-replay             (command trust)

Layering matters: cryptographic authentication (1) is the only layer that can
catch a *perfectly self-consistent* spoof, while (2)-(3) catch faults and
spoofs against receivers that do not yet have OSNMA lock. (4) is orthogonal and
protects the command path regardless of GNSS state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .gnss.osnma_adapter import AuthResult
from .gnss.raim import RaimResult
from .gnss.spoof_detection import SpoofingVerdict


class NavMode(str, Enum):
    TRUST_GNSS = "TRUST_GNSS"
    GNSS_DEGRADED = "GNSS_DEGRADED"           # use with caution / inflate covariance
    DEADRECKON = "DEADRECKON"                 # coast on IMU, ignore GNSS position
    RETURN_TO_HOME = "RETURN_TO_HOME"         # last-resort failsafe


@dataclass
class NavSecurityState:
    mode: NavMode
    gnss_authenticated: bool
    spoofing_suspected: bool
    jamming_suspected: bool
    raim_healthy: bool
    command_link_trusted: bool
    reasons: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return f"{self.mode.value}: " + "; ".join(self.reasons)


class DefenseMonitor:
    def assess(
        self,
        osnma: AuthResult | None,
        raim: RaimResult | None,
        spoof: SpoofingVerdict | None,
        command_link_ok: bool,
    ) -> NavSecurityState:
        reasons: list[str] = []

        authenticated = bool(osnma and osnma.authenticated)
        if osnma is not None:
            reasons.append(f"OSNMA:{'ok' if authenticated else osnma.reason}")

        raim_healthy = raim.healthy if raim is not None else True
        if raim is not None and not raim_healthy:
            reasons.append("RAIM: unresolved fault")
        elif raim is not None and raim.excluded_index is not None:
            reasons.append(f"RAIM: excluded sat #{raim.excluded_index}")

        spoofing = bool(spoof and spoof.spoofing_suspected)
        jamming = bool(spoof and spoof.jamming_suspected)
        if spoof is not None:
            reasons.append(
                f"consistency: {spoof.num_flags} flag(s)"
                + (" SPOOF" if spoofing else "")
                + (" JAM" if jamming else "")
            )

        # Decision logic (defence-in-depth, fail-safe toward inertial).
        mode = NavMode.TRUST_GNSS
        if spoofing:
            # Consistency layer screams spoof: only OSNMA authentication can
            # rescue trust; otherwise stop using GNSS position entirely.
            mode = NavMode.GNSS_DEGRADED if authenticated else NavMode.DEADRECKON
        elif not raim_healthy:
            mode = NavMode.DEADRECKON
        elif jamming:
            mode = NavMode.DEADRECKON
        elif osnma is not None and not authenticated:
            mode = NavMode.GNSS_DEGRADED

        if not command_link_ok:
            reasons.append("C2 link: UNAUTHENTICATED commands rejected")
            # Loss of trusted command link while navigation is also compromised
            # is the worst case -> conservative failsafe.
            if mode in (NavMode.DEADRECKON,):
                mode = NavMode.RETURN_TO_HOME

        return NavSecurityState(
            mode=mode,
            gnss_authenticated=authenticated,
            spoofing_suspected=spoofing,
            jamming_suspected=jamming,
            raim_healthy=raim_healthy,
            command_link_trusted=command_link_ok,
            reasons=reasons,
        )
