"""Camera sources for the cockpit FPV pane.

``SyntheticCamera`` renders a realistic procedural EO/IR gun-camera scene (numpy):
a graded sky with sun haze, hazy distant ridgelines, value-noise terrain with a
winding road, an atmospheric horizon band, and a moving hostile-quad silhouette —
a stand-in for a real drone EO feed so the cockpit looks like an actual operator
screen with zero capture hardware. It exposes ``.bogey`` (the hostile UAS screen
position) so the HUD can draw a target box. ``OpenCVCamera`` (optional) pulls a
real EO/IR feed from a device index or RTSP/UDP URL.

Both return an ``(H, W, 3)`` uint8 RGB array.
"""

from __future__ import annotations

import math


def _resize(g, h, w):
    import numpy as np

    gh, gw = g.shape
    yi = np.linspace(0, gh - 1, h)
    xi = np.linspace(0, gw - 1, w)
    y0 = np.floor(yi).astype(int)
    x0 = np.floor(xi).astype(int)
    y1 = np.minimum(y0 + 1, gh - 1)
    x1 = np.minimum(x0 + 1, gw - 1)
    wy = (yi - y0)[:, None]
    wx = (xi - x0)[None, :]
    a = g[np.ix_(y0, x0)]
    b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]
    d = g[np.ix_(y1, x1)]
    return (a * (1 - wx) + b * wx) * (1 - wy) + (c * (1 - wx) + d * wx) * wy


def _fractal_noise(h, w, seed):
    import numpy as np

    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for octv in range(4):
        gh = max(2, h >> (5 - octv))
        gw = max(2, w >> (5 - octv))
        out += _resize(rng.random((gh, gw)).astype(np.float32), h, w) * amp
        tot += amp
        amp *= 0.5
    out /= tot
    return (out - out.min()) / (np.ptp(out) + 1e-6)


def _disc(img, cx, cy, r, color):
    import numpy as np

    h, w = img.shape[:2]
    y0, y1 = max(0, cy - r), min(h, cy + r + 1)
    x0, x1 = max(0, cx - r), min(w, cx + r + 1)
    if y0 >= y1 or x0 >= x1:
        return
    yy = np.arange(y0, y1)[:, None] - cy
    xx = np.arange(x0, x1)[None, :] - cx
    mask = yy * yy + xx * xx <= r * r
    img[y0:y1, x0:x1][mask] = color


def _line(img, x0, y0, x1, y1, color, width=2):
    import numpy as np

    n = int(max(abs(x1 - x0), abs(y1 - y0)) + 1)
    xs = np.linspace(x0, x1, n).astype(int)
    ys = np.linspace(y0, y1, n).astype(int)
    for px, py in zip(xs, ys):
        _disc(img, px, py, width, color)


def _draw_quad(img, cx, cy, size):
    """Dark hostile-quad silhouette (X-frame + 4 rotor discs)."""
    body = (24, 26, 28)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        ex, ey = cx + dx * size, cy + dy * size
        _line(img, cx, cy, ex, ey, body, 1)
        _disc(img, ex, ey, max(2, size // 3), (18, 20, 22))
    _disc(img, cx, cy, max(2, size // 4), (12, 12, 14))


class SyntheticCamera:
    """Realistic procedural EO/IR FPV scene (numpy)."""

    def __init__(self, width: int = 1280, height: int = 720, seed: int = 7) -> None:
        self.width = width
        self.height = height
        self.bogey = (width // 2, int(height * 0.40))
        self._terrain = _fractal_noise(height, width, seed)

    def frame(self, t: float, state=None):
        import numpy as np

        h, w = self.height, self.width
        roll = (getattr(state, "roll", 0.0) or 0.0) * 0.5
        pitch = getattr(state, "pitch", 0.0) or 0.0
        yaw = getattr(state, "yaw", 0.0) or 0.0

        cols = np.arange(w)
        rows = np.arange(h)[:, None]
        horizon = h * 0.46 - pitch * h * 0.16 + (cols - w / 2) * math.tan(roll * 0.5)
        H = horizon[None, :]
        below = rows >= H

        # sky gradient + warm sun glow
        sky_frac = np.clip(rows / np.maximum(H, 1.0), 0, 1)[..., None]
        top = np.array([46, 74, 122], np.float32)
        haze = np.array([188, 206, 218], np.float32)
        sky = top * (1 - sky_frac) + haze * sky_frac
        sx, sy = int(w * 0.72), int(h * 0.15)
        dist = np.sqrt((cols[None, :] - sx) ** 2 + (np.arange(h)[:, None] - sy) ** 2)
        glow = (np.clip(1 - dist / (w * 0.55), 0, 1) ** 2)[..., None]
        sky = sky + glow * np.array([70, 62, 38], np.float32)

        # ground: far-haze -> near-terrain, texture stronger toward the foreground
        depth = np.clip((rows - H) / np.maximum(h - H, 1.0), 0, 1)[..., None]
        far = np.array([150, 162, 158], np.float32)
        near = np.array([74, 84, 54], np.float32)
        ground = far * (1 - depth) + near * depth
        ground = ground * (0.80 + 0.42 * self._terrain[..., None] * depth)

        img = np.where(below[..., None], ground, sky).astype(np.float32)

        # winding road (uses centre-column horizon for a stable per-row depth)
        hc = float(horizon[w // 2])
        dr = np.clip((np.arange(h) - hc) / max(h - hc, 1.0), 0, 1)[:, None]
        roadc = w / 2 + np.sin(dr * 3.0 + 1.1) * w * 0.16 + yaw * w * 0.05
        roadw = 1.5 + dr * w * 0.03
        road = (np.abs(cols[None, :] - roadc) < roadw) & below
        img[road] = img[road] * 0.4 + np.array([176, 170, 150], np.float32) * 0.6

        # hazy distant ridgeline just above the horizon
        band = np.exp(-(((rows - H) / (h * 0.045)) ** 2))
        ridge = (np.sin(cols * 0.012) * 0.5 + np.sin(cols * 0.05) * 0.5) * h * 0.012
        band = band * (1 - 0.4 * (rows < (H + ridge[None, :])))
        img = img * (1 - band[..., None] * 0.45) + haze * band[..., None] * 0.45

        # hostile quad (flying above the horizon), tracked for the HUD target box
        bx = int(w * 0.5 + math.sin(t * 0.45) * w * 0.24 - yaw * w * 0.12)
        by = int(float(horizon[min(max(bx, 0), w - 1)]) - h * 0.11
                 + math.cos(t * 0.7) * h * 0.04)
        self.bogey = (bx, by)
        _draw_quad(img, bx, by, max(7, int(w * 0.012)))

        # subtle EO-sensor feel: vignette + faint scanlines
        vy = (np.arange(h)[:, None] - h / 2) / (h / 2)
        vx = (cols[None, :] - w / 2) / (w / 2)
        vig = np.clip(1 - 0.35 * (vx * vx + vy * vy), 0.55, 1.0)[..., None]
        img *= vig
        img[::3, :, :] *= 0.94

        return np.clip(img, 0, 255).astype(np.uint8)


class OpenCVCamera:
    """Real EO/IR feed via OpenCV (optional dependency)."""

    def __init__(self, source=0, width: int = 1280, height: int = 720) -> None:
        import cv2  # lazy: optional opencv-python

        self.width, self.height = width, height
        self.bogey = (width // 2, height // 2)
        self._cap = cv2.VideoCapture(source)
        self._cv2 = cv2

    def frame(self, t: float, state=None):
        import numpy as np

        ok, bgr = self._cap.read()
        if not ok:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        bgr = self._cv2.resize(bgr, (self.width, self.height))
        return self._cv2.cvtColor(bgr, self._cv2.COLOR_BGR2RGB)
