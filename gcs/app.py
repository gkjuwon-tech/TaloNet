"""TaloNet GCS — manual teleoperation cockpit (pygame).

Speed-first manual control: NO onboard VLM. The screen is a realistic EO/IR FPV
feed with a professional military HUD (boresight + pitch ladder, bank arc,
heading/speed/altitude tapes, a HOSTILE-UAS target box, and the green NET-AIM
reticle the operator slews onto the target). Flight + net launcher (aim / fire /
cinch / release) are all flown by hand; commands go out over a signed link.

Run it:   python -m gcs
Headless: SDL_VIDEODRIVER=dummy python -c "from gcs.app import run; run(max_frames=1, screenshot='cockpit.png')"

Key map (gcs.control): WASD+QE fly, RF throttle, IJKL aim net, SPACE fire,
C cinch, V drop, G arm, B e-stop, N reset, H RTH, ESC quit.
"""

from __future__ import annotations

import math
import time

from .camera import SyntheticCamera
from .control import PAN_LIMITS, TILT_LIMITS, ControlState
from .link import LoopbackLink

_HELD_KEYS = ("w", "a", "s", "d", "q", "e", "r", "f", "i", "j", "k", "l")

# HUD palette
HUD = (122, 240, 150)        # symbology green
AMBER = (240, 190, 60)
RED = (235, 80, 70)
WHITE = (235, 240, 235)
DIM = (90, 150, 110)


def build_link(connect=None, key_secret=b"talonet-demo-key"):
    """Real MAVLink link if ``connect`` is reachable, else the offline loopback."""
    if not connect:
        return LoopbackLink(key=key_secret), "OFFLINE (loopback)"
    try:
        from .link import MavlinkLink

        link = MavlinkLink(connect)        # signing opt-in; SITL/FC unsigned by default
        ok = link.wait_heartbeat(timeout=6.0)
        if ok:
            return link, f"MAVLINK {connect}"
        link.close()
    except Exception as exc:  # pymavlink missing / no link -> degrade gracefully
        print(f"[gcs] MAVLink connect failed ({exc}); falling back to loopback")
    return LoopbackLink(key=key_secret), "OFFLINE (loopback)"


def build_camera(video=None, window=(1280, 720)):
    if video is not None:
        try:
            from .camera import OpenCVCamera

            return OpenCVCamera(video, window[0], window[1])
        except Exception as exc:
            print(f"[gcs] video source failed ({exc}); using synthetic scene")
    return SyntheticCamera(window[0], window[1])


def run(link=None, camera=None, window=(1280, 720), fps=30, max_frames=None,
        screenshot=None, key_secret=b"talonet-demo-key", state=None,
        connect=None, video=None):
    """Launch the cockpit. ``connect`` (MAVLink string) drives real hardware/SITL;
    ``max_frames``/``screenshot`` enable headless tests."""
    import numpy as np
    import pygame

    link_status = "OFFLINE (loopback)"
    if link is None:
        link, link_status = build_link(connect, key_secret)
    if camera is None:
        camera = build_camera(video, window)

    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode(window)
    pygame.display.set_caption("TaloNet GCS - manual teleop cockpit")
    clock = pygame.time.Clock()
    fonts = {
        "s": pygame.font.SysFont("dejavusansmono,consolas,monospace", 13),
        "m": pygame.font.SysFont("dejavusansmono,consolas,monospace", 16),
        "l": pygame.font.SysFont("dejavusansmono,consolas,monospace", 20, bold=True),
    }
    state = state if state is not None else ControlState()

    t0 = time.time()
    frames = 0
    running = True
    while running:
        dt = clock.tick(fps) / 1000.0
        t = time.time() - t0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                name = pygame.key.name(ev.key)
                if name == "escape":
                    running = False
                cmd = state.handle_key(name)
                if cmd is not None:
                    link.send(cmd)
        pressed = pygame.key.get_pressed()
        held = {n for n in _HELD_KEYS if pressed[getattr(pygame, "K_" + n)]}
        state.apply_held(held, dt)
        link.send({"type": "SETPOINT", "setpoint": state.setpoint()})
        telem = link.telemetry() if hasattr(link, "telemetry") else {}

        frame = camera.frame(t, state)            # (H, W, 3) RGB
        surf = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
        if surf.get_size() != window:
            surf = pygame.transform.smoothscale(surf, window)
        screen.blit(surf, (0, 0))
        _draw_hud(pygame, screen, fonts, state, link, camera, window, t,
                  telem, link_status)
        pygame.display.flip()

        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False

    if screenshot:
        pygame.image.save(screen, screenshot)
    pygame.quit()
    return state


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
def _rot(px, py, cx, cy, ang):
    s, c = math.sin(ang), math.cos(ang)
    dx, dy = px - cx, py - cy
    return (cx + dx * c - dy * s, cy + dx * s + dy * c)


def _text(screen, font, s, x, y, color=HUD, center=False, right=False):
    img = font.render(s, True, color)
    r = img.get_rect()
    if center:
        r.center = (x, y)
    elif right:
        r.topright = (x, y)
    else:
        r.topleft = (x, y)
    screen.blit(img, r)


def _draw_hud(pygame, screen, fonts, state, link, camera, window, t,
              telem=None, link_status="OFFLINE (loopback)"):
    w, h = window
    cx, cy = w // 2, h // 2
    sm, md, lg = fonts["s"], fonts["m"], fonts["l"]
    draw = pygame.draw
    telem = telem or {}
    live = bool(telem)   # real telemetry present?

    # translucent overlay for tapes/bars
    ov = pygame.Surface(window, pygame.SRCALPHA)

    # --- frame corner brackets + classification banner ---
    for ox, oy, dx, dy in ((24, 24, 1, 1), (w - 24, 24, -1, 1),
                           (24, h - 24, 1, -1), (w - 24, h - 24, -1, -1)):
        draw.line(screen, HUD, (ox, oy), (ox + 26 * dx, oy), 2)
        draw.line(screen, HUD, (ox, oy), (ox, oy + 26 * dy), 2)
    _text(screen, sm, "MANUAL // HUMAN-IN-THE-LOOP // NO AUTO-ENGAGE", cx, 14,
          AMBER, center=True)
    _text(screen, sm, f"LINK: {link_status}", 56, 30, HUD if live else AMBER)

    # --- REC + mission clock (top-right) ---
    if int(t * 2) % 2 == 0:
        draw.circle(screen, RED, (w - 150, 40), 6)
    _text(screen, sm, "REC", w - 138, 33, RED)
    _text(screen, md, f"T {int(t) // 60:02d}:{int(t) % 60:02d}", w - 40, 30, HUD, right=True)
    _text(screen, sm, "EO/IR  CAM-1  x1.0", w - 40, 50, DIM, right=True)

    # --- heading tape (top) ---
    hdg = telem.get('hdg', (t * 8 + state.yaw * 40) % 360)
    tw = 460
    draw.rect(ov, (0, 0, 0, 110), (cx - tw // 2, 30, tw, 26))
    for d in range(-40, 41, 5):
        hd = int(round((hdg + d) / 5.0) * 5) % 360
        x = cx + (hd - hdg if abs(hd - hdg) < 180 else hd - hdg - 360 * (1 if hd > hdg else -1)) * (tw / 90)
        x = cx + d * (tw / 90)
        if hd % 10 == 0:
            draw.line(screen, HUD, (x, 40), (x, 50), 1)
            if hd % 30 == 0:
                _text(screen, sm, f"{hd:03d}", int(x), 22, HUD, center=True)
    draw.polygon(screen, AMBER, [(cx, 54), (cx - 6, 44), (cx + 6, 44)])
    _text(screen, sm, f"HDG {int(hdg):03d}", cx, 66, AMBER, center=True)

    # --- bank arc + roll pointer (top centre) ---
    roll_deg = telem.get('roll', state.roll * 30)
    rb = 150
    for a in (-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60):
        ar = math.radians(-90 + a)
        x1, y1 = cx + rb * math.cos(ar), (cy - 70) + rb * math.sin(ar)
        ln = 12 if a % 30 == 0 else 7
        x2, y2 = cx + (rb - ln) * math.cos(ar), (cy - 70) + (rb - ln) * math.sin(ar)
        draw.line(screen, HUD, (x1, y1), (x2, y2), 1)
    ar = math.radians(-90 + roll_deg)
    px, py = cx + (rb - 14) * math.cos(ar), (cy - 70) + (rb - 14) * math.sin(ar)
    draw.polygon(screen, AMBER, [(px, py),
                 _rot(px - 6, py - 12, px, py, ar + math.pi / 2),
                 _rot(px + 6, py - 12, px, py, ar + math.pi / 2)])

    # --- pitch ladder (rotated by bank) ---
    pitch_deg = telem.get('pitch', state.pitch * 15)
    ang = math.radians(roll_deg)
    ppd = 7
    for v in (-20, -15, -10, -5, 5, 10, 15, 20):
        dy = -(v - pitch_deg) * ppd
        yv = cy + dy
        if abs(dy) > h * 0.32:
            continue
        for sgn in (-1, 1):
            x1 = cx + sgn * 26
            x2 = cx + sgn * 96
            p1 = _rot(x1, yv, cx, cy, ang)
            p2 = _rot(x2, yv, cx, cy, ang)
            if v > 0:
                draw.line(screen, HUD, p1, p2, 1)
            else:  # dive bars: tick + dashed feel
                draw.line(screen, HUD, p1, _rot(x2, yv, cx, cy, ang), 1)
                tick = _rot(x2, yv + 6, cx, cy, ang)
                draw.line(screen, HUD, p2, tick, 1)
            lp = _rot(cx + sgn * 110, yv, cx, cy, ang)
            _text(screen, sm, f"{abs(v)}", int(lp[0]), int(lp[1]), HUD, center=True)

    # --- boresight ---
    draw.line(screen, HUD, (cx - 30, cy), (cx - 10, cy), 2)
    draw.line(screen, HUD, (cx + 10, cy), (cx + 30, cy), 2)
    draw.line(screen, HUD, (cx, cy - 8), (cx, cy + 8), 1)
    draw.circle(screen, HUD, (cx, cy), 3)

    # --- speed tape (left) + altitude tape (right) ---
    spd = telem.get('spd', state.throttle * 28.0)
    alt = telem.get('alt', 118 + math.sin(t * 0.5) * 4)
    _tape(pygame, screen, ov, sm, 70, cy, spd, "SPD m/s", HUD)
    _tape(pygame, screen, ov, sm, w - 70, cy, alt, "ALT m", HUD, right=True)

    # --- HOSTILE-UAS target box (slaved to the EO tracker) ---
    bx, by = getattr(camera, "bogey", (cx, int(h * 0.4)))
    bs = int(w * 0.035)
    for ox, oy in ((-bs, -bs), (bs, -bs), (-bs, bs), (bs, bs)):
        sx = 1 if ox < 0 else -1
        sy = 1 if oy < 0 else -1
        draw.line(screen, RED, (bx + ox, by + oy), (bx + ox + 12 * sx, by + oy), 2)
        draw.line(screen, RED, (bx + ox, by + oy), (bx + ox, by + oy + 12 * sy), 2)
    _text(screen, sm, "HOSTILE UAS  TGT-01", bx, by - bs - 16, RED, center=True)
    rng = 280 + 60 * math.sin(t * 0.3)
    brg = int((math.degrees(math.atan2(bx - cx, cy - by)) + 360) % 360)
    _text(screen, sm, f"RNG {rng:3.0f}m  BRG {brg:03d}  CONF .82", bx, by + bs + 6, RED, center=True)

    # --- NET-AIM reticle (operator slews onto the target) ---
    nx = int(cx + (state.net_pan / PAN_LIMITS[1]) * (w * 0.34))
    mid = (TILT_LIMITS[0] + TILT_LIMITS[1]) / 2
    ny = int(cy + ((state.net_tilt - mid) / mid) * (h * 0.30))
    rc = HUD if state.armed else AMBER
    draw.circle(screen, rc, (nx, ny), 18, 2)
    draw.line(screen, rc, (nx - 28, ny), (nx - 8, ny), 2)
    draw.line(screen, rc, (nx + 8, ny), (nx + 28, ny), 2)
    draw.line(screen, rc, (nx, ny - 28), (nx, ny - 8), 2)
    draw.line(screen, rc, (nx, ny + 8), (nx, ny + 28), 2)
    _text(screen, sm, f"NET  P{state.net_pan:+.0f} T{state.net_tilt:.0f}", nx + 24, ny + 20, rc)
    lock = "READY" if state.armed else "SAFE"
    _text(screen, sm, lock, nx + 24, ny + 34, rc)

    # --- bottom status bar ---
    bar_h = 30
    draw.rect(ov, (0, 0, 0, 150), (0, h - bar_h, w, bar_h))
    if state.estop:
        st, sc = "E-STOP", RED
    elif state.armed:
        st, sc = "ARMED", HUD
    else:
        st, sc = "SAFE", AMBER
    batt = telem.get("batt")
    sats = telem.get("sats")
    lat = telem.get("lat", 37.5012)
    lon = telem.get("lon", 127.0431)
    link_lbl = ("LINK " + ("LIVE" if live else "SIM") + " #"
                + str(getattr(link, "seq", 0)) + (" SIGNED" if getattr(
                    link, "signing_enabled", True) else ""))
    segs = [
        (lg, state.mode, HUD), (lg, st, sc),
        (md, f"THR {state.throttle * 100:3.0f}%", WHITE),
        (md, f"NET P{state.net_pan:+.0f} T{state.net_tilt:.0f}", WHITE),
        (md, link_lbl, HUD if live else DIM),
        (md, f"BATT {batt:.0f}%" if batt is not None else "BATT --", WHITE),
        (md, f"GPS {sats}sat" if sats is not None else "GPS --", DIM),
        (md, f"{lat:.4f}N {lon:.4f}E", WHITE),
        (md, time.strftime("%H:%M:%SZ", time.gmtime()), WHITE),
    ]
    x = 16
    for font, s, col in segs:
        _text(screen, font, s, x, h - bar_h + 5, col)
        x += font.size(s)[0] + 26

    # last-action toast
    if state.last_action:
        col = RED if state.last_action.startswith("DENIED") else AMBER
        _text(screen, md, f">> {state.last_action}", 30, h - bar_h - 26, col)

    screen.blit(ov, (0, 0))


def _tape(pygame, screen, ov, font, x, cy, value, label, color, right=False):
    draw = pygame.draw
    bw, bh = 56, 230
    bx = x - bw // 2
    pygame.draw.rect(ov, (0, 0, 0, 110), (bx, cy - bh // 2, bw, bh))
    for i in range(-5, 6):
        v = round(value) + i * 2
        ty = cy - i * 20
        ln = 10 if v % 10 == 0 else 5
        if right:
            draw.line(screen, color, (bx + bw, ty), (bx + bw - ln, ty), 1)
            if v % 10 == 0:
                _text(screen, font, f"{v}", bx + bw - 12, ty - 7, color, right=True)
        else:
            draw.line(screen, color, (bx, ty), (bx + ln, ty), 1)
            if v % 10 == 0:
                _text(screen, font, f"{v}", bx + 12, ty - 7, color)
    # current-value box
    draw.rect(screen, color, (bx - 2, cy - 12, bw + 4, 24), 2)
    _text(screen, font, f"{value:4.0f}", x, cy - 7, WHITE, center=True)
    _text(screen, font, label, x, cy - bh // 2 - 16, color, center=True)


if __name__ == "__main__":
    run()
