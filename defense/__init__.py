"""TaloNet defensive navigation & link-security stack.

Defence-only Counter-UAS hardening: GNSS anti-spoofing/anti-jamming and
command-link authentication. Nothing in this package transmits, jams, or
spoofs any signal -- it only *detects* and *rejects* attacks against our own
interceptor.

See ``defense/README.md`` for the verified open-source sources each module is
based on, and ``docs/05_방어_시스템.md`` for the system-level description.
"""

from .monitor import DefenseMonitor, NavMode, NavSecurityState

__all__ = ["DefenseMonitor", "NavMode", "NavSecurityState"]
