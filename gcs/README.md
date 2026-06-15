# `gcs/` — TaloNet manual teleop cockpit

> **Speed first, human in the loop, no VLM.** A ground-control app you install on a
> laptop: a realistic **EO/IR FPV feed** fills the screen under a **professional
> military HUD** (boresight + pitch ladder, bank arc, heading/speed/altitude tapes,
> a HOSTILE-UAS target box, and the green NET-AIM reticle), and you fly the
> mothership **and** aim/fire the software-aimed net from the keyboard. Onboard VLM
> autonomy was dropped — a human reacts faster than a 2-second inference, and the
> engagement decision stays with the operator.

![cockpit](../docs/img/cockpit.png)

## Run

```bash
pip install -r requirements-gcs.txt          # pygame, numpy, pymavlink

python -m gcs                                 # offline (synthetic EO scene)
```

### Real working prototype (real MAVLink)

```bash
# A) no hardware — full loop over real MAVLink 2 frames
python -m gcs.sim_vehicle                      # vehicle emulator (udpin:127.0.0.1:14550)
python -m gcs --connect udpout:127.0.0.1:14550 # cockpit: real arm/aim/fire + live HUD

# B) ArduPilot SITL
sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550
python -m gcs --connect udpout:127.0.0.1:14550

# C) real Pixhawk + EO feed
python -m gcs --connect /dev/ttyACM0 --video rtsp://10.0.0.5:8554/eo
```

Net aim goes out as `DO_SET_SERVO` on the channels in
[`payload_map.py`](payload_map.py) (the **single source of truth** shared with the
CAD limits and `docs/06`); arm/fire/RTL are real `COMMAND_LONG`s; the HUD is driven
by live `ATTITUDE`/`VFR_HUD`/`GPS_RAW_INT`/`SYS_STATUS`. Full CONOPS + deployment:
[`docs/11`](../docs/11_CONOPS_and_Deployment.md).

Headless smoke (no display):

```bash
SDL_VIDEODRIVER=dummy python -c "from gcs.app import run; run(max_frames=1, screenshot='cockpit.png')"
```

## Controls

| Keys | Action |
|------|--------|
| `W`/`S` `A`/`D` | pitch / roll |
| `Q`/`E` | yaw |
| `R`/`F` | throttle up / down |
| `I`/`K` `J`/`L` | net aim tilt / pan (slews the green reticle) |
| `SPACE` | **fire net** (armed only, in the aimed direction) |
| `C` | cinch (purse the mouth shut) |
| `V` | release / drop |
| `G` | arm toggle · `B` E-STOP · `N` reset · `H` return-to-home · `ESC` quit |

Interlocks mirror the hardware (docs/06 §11): FIRE/CINCH/RELEASE require **ARMED**,
nothing arms while **E-STOP** is latched.

## Architecture

| Module | Role | Deps |
|--------|------|------|
| `payload_map.py` | **single source of truth**: servo channels / PWM / angle limits (shared with CAD + docs/06) | stdlib |
| `control.py` | `ControlState` + key mapping → setpoints & command events | stdlib |
| `link.py` | `LoopbackLink` (offline, HMAC-signed) + **`MavlinkLink`** (real MAVLink 2 to FC/SITL: MANUAL_CONTROL + DO_SET_SERVO + arm/relay/RTL + telemetry) | pymavlink |
| `sim_vehicle.py` | runnable MAVLink vehicle emulator (`python -m gcs.sim_vehicle`) | pymavlink |
| `camera.py` | `SyntheticCamera` (realistic procedural EO scene) + optional `OpenCVCamera` | numpy / opencv |
| `app.py` | pygame cockpit: realistic FPV + pro military HUD, live telemetry, auto-connect (`run()`) | pygame, numpy |

The control core is dependency-free and unit-tested (`tests/test_gcs.py`); `pygame`
is imported lazily so importing `gcs` works without a display.

The real command link uses **MAVLink 2 message signing** (the cockpit's
`LoopbackLink` HMAC is the same idea, stubbed) — see
[`defense/link/mavlink_signing.py`](../defense/link/mavlink_signing.py) and
[`defense/link/rf_link_security.py`](../defense/link/rf_link_security.py). Net aim
maps to the `net_pan`/`net_tilt` gimbal in
[`cad/talonet_frame.scad`](../cad/talonet_frame.scad) and the AIM-PAN/AIM-TILT
servo channels in [`docs/06`](../docs/06_회로_설계.md).
