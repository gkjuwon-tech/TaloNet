# Landing page asset credits

All media is real, free, and cleared for use. No AI-generated or AI-styled imagery
is used. Video is genuine U.S. Department of Defense footage (public domain), and
the photograph is a U.S. federal government work — not commercial stock.

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

## Photography

| File | Source | License |
|------|--------|---------|
| `recovered-drones.jpg` | Wikimedia Commons — "Shahed drones recovered from Iraq and Ukraine", U.S. Defense Intelligence Agency | Public domain (U.S. federal government work) |

Photographs are downscaled and stripped of metadata for web delivery.

## Typography

| Family | Use | Source / License |
|--------|-----|------------------|
| **B612** | Body and headings | Designed by Airbus + Intactile DESIGN / ENAC for cockpit display legibility. SIL Open Font License 1.1 |
| **B612 Mono** | Labels, telemetry, specs, UI | Monospace companion to B612. SIL Open Font License 1.1 |

Fonts are self-hosted (`assets/fonts/*.woff2`) — no third-party font CDN is called,
so the page makes no external requests at runtime. B612 is a genuine aviation
typeface drawn for instrument readability, not a decorative "military" display font.
