"""Camera sources for the cockpit FPV pane.

``SyntheticCamera`` renders a dependency-light test FPV frame (sky/ground horizon
that banks with roll/pitch, plus a moving hostile-UAS blip) so the cockpit runs
and is testable with zero capture hardware. ``OpenCVCamera`` (optional) pulls a
real EO/IR feed from a device index or RTSP/UDP URL when ``opencv-python`` is
installed. Both return an ``(H, W, 3)`` uint8 RGB array.
"""

from __future__ import annotations

import math


class SyntheticCamera:
    """Procedural FPV frame generator (numpy)."""

    def __init__(self, width: int = 640, height: int = 360) -> None:
        self.width = width
        self.height = height

    def frame(self, t: float, state=None):
        import numpy as np

        h, w = self.height, self.width
        roll = getattr(state, "roll", 0.0) if state else 0.0
        pitch = getattr(state, "pitch", 0.0) if state else 0.0
        img = np.empty((h, w, 3), dtype=np.uint8)

        # banking horizon: row threshold per column tilts with roll, lifts w/ pitch
        cols = np.arange(w)
        base = h * 0.5 - pitch * h * 0.18
        horizon = base + (cols - w / 2) * math.tan(roll * 0.6) * 0.5
        rows = np.arange(h)[:, None]
        sky = rows < horizon[None, :]
        img[:] = np.where(sky[..., None], np.array([46, 60, 82], np.uint8),
                          np.array([34, 44, 30], np.uint8))

        # moving hostile-UAS blip (the thing the operator is chasing)
        bx = int(w * 0.5 + math.sin(t * 0.8) * w * 0.30)
        by = int(h * 0.42 + math.cos(t * 1.1) * h * 0.16)
        img[max(0, by - 7):by + 7, max(0, bx - 7):bx + 7] = (220, 64, 52)
        return img


class OpenCVCamera:
    """Real EO/IR feed via OpenCV (optional dependency)."""

    def __init__(self, source=0, width: int = 640, height: int = 360) -> None:
        import cv2  # lazy: optional opencv-python

        self.width, self.height = width, height
        self._cap = cv2.VideoCapture(source)
        self._cv2 = cv2

    def frame(self, t: float, state=None):
        import numpy as np

        ok, bgr = self._cap.read()
        if not ok:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        bgr = self._cv2.resize(bgr, (self.width, self.height))
        return self._cv2.cvtColor(bgr, self._cv2.COLOR_BGR2RGB)
