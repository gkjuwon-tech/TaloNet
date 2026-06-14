# `defense/` — TaloNet defensive navigation & link-security stack

> **Defence only.** Nothing in this package transmits, jams, or spoofs any
> signal. It only *detects* and *rejects* attacks against our own interceptor
> (GNSS spoofing/jamming, command-link injection/replay). This keeps TaloNet on
> the ethically clean side of counter-UAS — same posture as the rest of the
> project: we capture/dispose drones physically, and we harden ourselves
> cryptographically.

This code is **not hand-rolled crypto from scratch**. Each module implements a
published, verified algorithm and/or delegates to an audited open-source
implementation. Sources and licenses are listed below so the lineage is
auditable.

## Layers & sources

| Module | What it does | Verified source / spec |
|--------|--------------|------------------------|
| `gnss/osnma_adapter.py` | GNSS navigation-message authentication (TESLA one-way key chain + delayed MAC). Adapter delegates to a real OSNMA library for live signal-in-space auth. | **galileo-osnma** (Rust, Apache-2.0) — github.com/daniestevez/galileo-osnma · **OSNMAlib** (Python, EUPL-1.2) — github.com/Algafix/OSNMA · TESLA: Perrig et al. · Galileo OSNMA ICD |
| `gnss/raim.py` | Receiver Autonomous Integrity Monitoring: least-squares-residuals fault detection + exclusion with a chi-square test. | Parkinson & Axelrad (NAVIGATION, 1988) · RTCA DO-229 (WAAS MOPS) · Stanford GPS Lab IONGNSS-2021 spoofing-integrity paper · ref impl github.com/MichaelBeechan/RAIM_PANG_NAV |
| `gnss/spoof_detection.py` | Sensor-consistency checks: position glitch gate, EKF innovation gate, C/N0 anomaly, clock-jump, multi-constellation cross-check. | **ArduPilot** GPS glitch/EKF gating — ardupilot.org/copter/docs/gps-failsafe-glitch-protection.html · ArduPilot PR #24899 "EKF: cope better with GPS jamming" · gnss-sdr spoofing fork github.com/oscimp/gnss-sdr-1PPS |
| `link/mavlink_signing.py` | MAVLink 2 message signing (SHA-256, 48-bit signature, monotonic 48-bit timestamp) for C2 authentication + replay rejection. | **MAVLink** spec — mavlink.io/en/guide/message_signing.html · used by PX4 (docs.px4.io) and ArduPilot |
| `link/rf_link_security.py` | Transport-agnostic HMAC frame auth, IPsec-style sliding-window anti-replay, jamming/takeover link monitor. | RFC 4303 / RFC 6479 anti-replay window · HMAC RFC 2104 |
| `monitor.py` | Fuses all layers into one explainable navigation-trust verdict (TRUST / DEGRADED / DEADRECKON / RTH). | Defence-in-depth composition (this repo) |

## Design choices

- **Dependency-free core.** The detection/auth logic uses only the Python
  standard library so it can be audited and run on an embedded flight computer
  without a BLAS stack. The full OSNMA signal-in-space verification is the one
  thing we defer to an external audited library (`osnma` / OSNMAlib) when
  installed — see `osnmalib_available()`.
- **Defence in depth.** Cryptographic authentication (OSNMA) is the only layer
  that catches a *perfectly self-consistent* spoof; RAIM and the consistency
  checks catch faults and spoofs before OSNMA lock. Link signing is orthogonal
  and protects the command path regardless of GNSS state.
- **Fail safe toward inertial.** When trust is lost the monitor recommends
  coasting on IMU dead-reckoning or returning to home — it never silently
  trusts a suspect fix.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

## Optional live-OSNMA dependency

For real signal-in-space OSNMA verification, install one of the verified
implementations (kept optional; the rest of the stack runs without it):

```bash
pip install -r requirements-optional.txt   # OSNMAlib (EUPL-1.2)
```
