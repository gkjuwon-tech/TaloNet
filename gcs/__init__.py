"""TaloNet GCS — manual teleoperation cockpit.

A speed-first ground-control app: the operator flies the mothership and aims/fires
the software-aimed net by keyboard while watching the FPV camera. There is NO
onboard VLM in the control loop (autonomy was dropped for latency, and to keep
the engagement decision with the human).

- :mod:`gcs.control` — ``ControlState`` + key mapping (dependency-free, tested).
- :mod:`gcs.link` — ``LoopbackLink`` signed/anti-replay command link.
- :mod:`gcs.camera` — ``SyntheticCamera`` (+ optional ``OpenCVCamera``).
- :mod:`gcs.app` — the pygame cockpit (``run()``); needs ``pygame``.

The core (control/link/camera) runs with stdlib + numpy; ``pygame`` is only
needed for the windowed cockpit and is imported lazily.
"""

from .camera import SyntheticCamera
from .control import PAN_LIMITS, TILT_LIMITS, ControlState
from .link import Ack, LoopbackLink, MavlinkLink

__all__ = [
    "Ack",
    "ControlState",
    "LoopbackLink",
    "MavlinkLink",
    "PAN_LIMITS",
    "SyntheticCamera",
    "TILT_LIMITS",
]
