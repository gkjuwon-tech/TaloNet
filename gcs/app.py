"""TaloNet GCS — manual teleoperation cockpit (pygame).

A speed-first manual controller: NO onboard VLM in the loop. The screen shows the
FPV camera, a HUD, and a green NET-AIM reticle the operator slews with the
keyboard; flight + net launcher (aim/fire/cinch/release) are all flown by hand
and the commands go out over a signed link (:mod:`gcs.link`).

Run it:   python -m gcs            (or gcs.app.run())
Headless: SDL_VIDEODRIVER=dummy python -c "from gcs.app import run; run(max_frames=1, screenshot='cockpit.png')"

Key map is in :mod:`gcs.control` (W/A/S/D + Q/E + R/F fly; I/J/K/L aim;
SPACE fire, C cinch, V release, G arm, B e-stop, N reset, H RTH, ESC quit).
"""

from __future__ import annotations

import time

from .camera import SyntheticCamera
from .control import PAN_LIMITS, TILT_LIMITS, ControlState
from .link import LoopbackLink

_HELD_KEYS = ("w", "a", "s", "d", "q", "e", "r", "f", "i", "j", "k", "l")

_LEGEND = ("WASD pitch/roll  QE yaw  RF throttle | IJKL aim net | "
           "SPACE fire  C cinch  V drop  G arm  B e-stop  N reset  H RTH")


def run(link=None, camera=None, window=(960, 540), fps=30, max_frames=None,
        screenshot=None, key_secret=b"talonet-demo-key", state=None):
    """Launch the cockpit. ``max_frames``/``screenshot`` enable headless tests."""
    import numpy as np
    import pygame

    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode(window)
    pygame.display.set_caption("TaloNet GCS - manual teleop cockpit")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 15)
    big = pygame.font.SysFont("monospace", 22, bold=True)

    state = state if state is not None else ControlState()
    link = link if link is not None else LoopbackLink(key=key_secret)
    camera = camera if camera is not None else SyntheticCamera()

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

        frame = camera.frame(t, state)            # (H, W, 3) RGB
        surf = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
        screen.blit(pygame.transform.smoothscale(surf, window), (0, 0))
        _draw_hud(pygame, screen, font, big, state, link, window)
        pygame.display.flip()

        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False

    if screenshot:
        pygame.image.save(screen, screenshot)
    pygame.quit()
    return state


def _draw_hud(pygame, screen, font, big, state, link, window) -> None:
    w, h = window
    green, red, amber, white = (60, 220, 90), (230, 70, 60), (240, 180, 40), (235, 235, 230)

    # NET-AIM reticle (green=armed/ready, red=safe). Operator slews onto the bogey.
    cx = int(w / 2 + (state.net_pan / PAN_LIMITS[1]) * (w * 0.34))
    mid_tilt = (TILT_LIMITS[0] + TILT_LIMITS[1]) / 2
    cy = int(h * 0.5 + ((state.net_tilt - mid_tilt) / mid_tilt) * (h * 0.30))
    rc = green if state.armed else red
    pygame.draw.circle(screen, rc, (cx, cy), 16, 2)
    pygame.draw.line(screen, rc, (cx - 24, cy), (cx + 24, cy), 1)
    pygame.draw.line(screen, rc, (cx, cy - 24), (cx, cy + 24), 1)
    screen.blit(font.render(f"NET AIM p{state.net_pan:+.0f} t{state.net_tilt:.0f}",
                            True, rc), (cx + 20, cy + 18))

    # top status line
    if state.estop:
        st, sc = "E-STOP", red
    elif state.armed:
        st, sc = "ARMED", green
    else:
        st, sc = "SAFE", amber
    screen.blit(big.render(f"{state.mode}  [{st}]", True, sc), (12, 10))
    screen.blit(font.render("MANUAL TELEOP - human in the loop (no VLM)", True, white),
                (12, 40))

    # throttle bar
    bx, by, bw = 12, 70, 160
    pygame.draw.rect(screen, (90, 90, 90), (bx, by, bw, 12), 1)
    pygame.draw.rect(screen, green, (bx, by, int(bw * state.throttle), 12))
    screen.blit(font.render(f"THR {state.throttle * 100:3.0f}%", True, white), (bx + bw + 8, by - 2))

    # attitude + last action / last command seq
    screen.blit(font.render(
        f"R{state.roll:+.1f} P{state.pitch:+.1f} Y{state.yaw:+.1f}", True, white), (12, 90))
    if state.last_action:
        col = red if state.last_action.startswith("DENIED") else amber
        screen.blit(font.render(f"> {state.last_action}", True, col), (12, 110))
    seq = getattr(link, "seq", 0)
    screen.blit(font.render(f"link seq {seq}", True, (150, 150, 150)), (w - 120, 10))

    # key legend (bottom)
    screen.blit(font.render(_LEGEND, True, (200, 200, 200)), (12, h - 22))


if __name__ == "__main__":
    run()
