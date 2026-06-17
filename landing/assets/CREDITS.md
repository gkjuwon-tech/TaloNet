# Landing page asset credits

All media is real, free, and cleared for use. No AI-generated or AI-styled imagery
is used, and no commercial stock photography is used. Every still and clip is a
work of the U.S. federal government (public domain), downloaded from the Defense
Visual Information Distribution Service (DVIDS).

## Video (DVIDS — U.S. Department of Defense, public domain)

Footage is downloaded from the Defense Visual Information Distribution Service
(DVIDS). As works of the U.S. federal government, the visuals are in the public
domain. All clips are trimmed, muted (audio removed) and re-encoded for web
delivery (MP4 + WebM, with a JPEG poster).

| File | Footage | Source |
|------|---------|--------|
| `video/hero.*` | Dusk reconnaissance drone launch and flight | "B-Roll: U.S. Army paratroopers fly drone in Kenya during Justified Accord 2025", 173rd Airborne Brigade — DVIDS video 952747 |
| `video/engage.*` | Counter-UAS operations — aerial and ground | "1st Cavalry Division tests counter UAS capabilities during Operation Return of the Condor", Fort Hood — DVIDS video 975941 |
| `video/eofeed.*` | Live drone EO feed with navigation telemetry (HUD) | Same source as `engage` (DVIDS video 975941) |

Audio tracks are intentionally stripped on web delivery; the videos are silent
background loops, so any music licensed in the original productions is not used.

## Photography (DVIDS — U.S. Department of Defense, public domain)

All photographs are downloaded from DVIDS (dvidshub.net). As works of the U.S.
federal government they are in the public domain. Each is downscaled and stripped
of metadata for web delivery; one is cropped only for framing.

| File | Photograph | Source |
|------|-----------|--------|
| `recovered-drones.jpg` | Recovered Iranian Shahed-123 UAS staged on a display table (full-bleed band) | "Iranian Weapons Materiel on Display at Joint Base Anacostia-Bolling", DoD photo by Lisa Ferdinando — DVIDS image 4935794 |
| `counter-uas-operator.jpg` | U.S. Soldiers training with a hand-held counter-UAS device | "U.S. Army Soldiers conduct training with the Drone Buster C-UAS device, Pabradė, Lithuania", photo by Sgt. Max Elliott — DVIDS image 9709333 |
| `forensic-recovery.jpg` | Tracked robot recovering a downed UAS in the field | "Counter Unmanned Aerial System Training Exercise at Al Asad Air Base", U.S. Army photo by Spc. Derek Mustard — DVIDS image 6218886 |
| `platform-uas.jpg` | Soldier hand-launching a small vertical-takeoff UAS | "101st Airborne Division (Air Assault) Multi-Functional Reconnaissance Company Drone Training", photo by Sgt. Adel Pacheco Alvarez — DVIDS image 9172211 |

Per DVIDS terms, use must comply with the restrictions at
https://www.dvidshub.net/about/copyright.

## Typography

| Family | Use | Source / License |
|--------|-----|------------------|
| **Archivo** | Display headlines and body | Variable grotesque (weight 100–900, width 62.5–125%) by Omnibus-Type. Used at a light weight (≈300), normal width and sentence case for a restrained, defense-prime display type. SIL Open Font License 1.1 |
| **B612 Mono** | Eyebrows, labels, captions, credits | Monospace by Airbus + Intactile DESIGN / ENAC for cockpit display legibility. SIL Open Font License 1.1 |

Fonts are self-hosted (`assets/fonts/*.woff2`) — no third-party font CDN is called,
so the page makes no external requests at runtime. The B612 proportional (sans)
weights (`b612-400/700.woff2`) ship in the repo but are no longer referenced by the
page. B612 Mono is a genuine aviation typeface drawn for instrument readability.
