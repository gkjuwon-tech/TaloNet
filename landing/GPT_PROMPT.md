# GPT prompt — TaloNet 랜딩페이지 (통 이미지 생성)

> 사용법: 아래 **PROMPT** 블록을 통째로 ChatGPT(이미지 생성 모델)에 붙여넣으면, 코드가 아니라 **완성된 랜딩페이지 전체를 하나의 긴 세로 이미지**로 뽑아준다(실제 웹사이트 스크롤 스크린샷처럼). Devin은 이 이미지를 보고 똑같은 디자인으로 `landing/index.html`을 복제한다.

---

## PROMPT (copy-paste, English)

```
You are a senior product designer for a real defense-technology company.
GENERATE ONE SINGLE, TALL, VERTICAL IMAGE of a COMPLETE marketing landing page
— as if it were a full-length screenshot of a finished, scrollable website,
top to bottom, in one continuous image. NOT code, NOT HTML, NOT separate asset
tiles. Just one long, polished landing-page image with all sections stacked
vertically. Render realistic UI chrome: nav bar, hero, body sections, square
cards, a spec table, a contact form, and a footer, composed like a real
product site. Aim for a tall aspect ratio (e.g. ~1440px wide, very tall).

The page must look like real, photographed defense/aerospace product marketing:
cinematic, photo-realistic background photography (NOT illustration, NOT 3D
render, NOT AI-art cliche), shot on a full-frame camera — desaturated, muted,
documentary feel, realistic grain, slightly underexposed. Photographic
backgrounds sit behind dark scrims (~55-75% opacity) so light text stays
readable. Suggested backdrop per section: an octocopter counter-UAS
interceptor hovering at overcast dusk (hero); a deployed kevlar catch-net
close-up (capabilities); a dim ground-control operations room with
out-of-focus screens (security); an empty field/riverbed from altitude
(safe-disposal); a sterile forensic lab bench with a recovered drone and an
extracted SD card (forensics). No neon, no purple gradients, no lens flares,
no readable text baked into the photos, no faces.

Brand: "TaloNet" — physical counter-UAS interception. A large mothership drone
nets hostile drones and either recovers them to base or safely drops dangerous
ones (e.g. kamikaze types) in unpopulated areas. NO jamming, NO spoofing, NO
hacking — purely physical capture, plus a defensive on-board security stack
(GNSS anti-spoofing, MAVLink command-link signing), plus lawful post-capture
forensics on recovered drones.

STRICT design rules:
- Language: ENGLISH only.
- Typography: Inter, loaded from Google Fonts. Use THIN / LIGHT weights
  (200-300) for headings and large text; 400 for body. Generous letter-spacing
  on small uppercase labels.
- Signature color: DEFENSE KHAKI. Use exactly these CSS variables:
    --ink:#0E0F0C; --surface:#15160F; --khaki:#86855F; --khaki-dark:#4C4B36;
    --mist:#E7E7DD; --muted:#A9A99B; --line:rgba(231,231,221,.14);
  Khaki is the accent/CTA color; backgrounds are near-black ink over the photos.
- Buttons: SHARP corners only — border-radius: 0. No rounded corners anywhere
  (cards, inputs, images all square). Primary button = khaki fill, ink text,
  uppercase, letter-spacing ~.08em, thin weight; secondary = 1px khaki outline,
  transparent fill.
- Must NOT look AI-generated: no emoji, no glassmorphism, no glow, no big rounded
  blobs, no centered-everything. Use a restrained editorial grid, hairline 1px
  dividers, lots of negative space, left-aligned section intros, small uppercase
  eyebrow labels, and real-sounding sober copy. Think Anduril / Palantir / Shield
  AI marketing tone — serious, technical, confident, understated.
- Tone: PROFESSIONAL. Not funny. No jokes, no slang.

Make it LONG — a full landing page with these sections stacked top-to-bottom,
in order:
  1. Sticky top nav (wordmark left "TALONET", anchor links, one khaki CTA
     "Request briefing").
  2. Hero: thin headline e.g. "Physical airspace defense.", one-sentence
     subhead, two buttons (primary "Request briefing", secondary "View
     capabilities"). Small spec strip below
     (e.g. 120 km/h · 14 kg MTOW · 8 km radius · <90 s detect-to-deliver).
  3. Problem statement: short editorial paragraph on the small-drone threat +
     why kinetic/jamming answers fall short.
  4. "How it works" — 3 steps: Detect → Decide → Deliver (capture & recover, or
     capture & safe-drop). Square cards, hairline borders, numbered 01/02/03.
  5. Capabilities: grid of capability tiles (Net interception, Onboard VLM
     threat classification, Sensor fusion, GNSS anti-spoofing, Command-link
     signing, Safe disposal).
  6. Platform spec table (the "Geulmae" mothership): clean two-column rows.
  7. Defensive security band: emphasize OSNMA GNSS authentication, RAIM,
     MAVLink 2 message signing — "we don't attack, we harden."
  8. Safe-disposal section: recover vs safe-drop logic.
  9. Post-capture forensics section: lawful forensic analysis of RECOVERED
     drones — read-only SD-card / storage imaging with hash-verified chain of
     custody, GPS & flight-log reconstruction (origin, route, intent), and
     threat-intelligence reporting. Frame it soberly and explicitly: this is
     NOT hacking. Intercepting a live system's comms is hacking; analyzing the
     storage of a physically secured object is lawful forensics / security
     investigation — turning captured devices into intelligence that prevents
     future attacks. Lay it out as a clean tile / spec-row flow:
     Image → Hash → Parse → Reconstruct route → Report.
 10. Final CTA band: "Request a briefing" + simple square contact form
     (name / organization / email, square inputs, khaki submit button).
 11. Minimal footer: wordmark, short legal line, nav.

OUTPUT: exactly ONE image — the entire landing page rendered top-to-bottom as a
single tall vertical composition. Do NOT output code, HTML, CSS, or multiple
separate images, and do NOT describe the page in text. Just produce the one
long finished landing-page image. If a single generation cannot fit the full
height, produce the tallest cohesive single image you can while keeping every
section above visible and in order.
```

---

## 디자인 토큰 요약 (Devin 구현과 동일하게 유지)

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--ink` | `#0E0F0C` | 배경(near-black) |
| `--surface` | `#15160F` | 카드/섹션 표면 |
| `--khaki` | `#86855F` | **시그니처 / CTA** |
| `--khaki-dark` | `#4C4B36` | 강조 보더/호버 |
| `--mist` | `#E7E7DD` | 본문 텍스트 |
| `--muted` | `#A9A99B` | 보조 텍스트 |
| 폰트 | Inter 200/300/400 | 얇게 |
| 버튼 라운드 | `border-radius: 0` | 전 요소 직각 |

## 체크리스트 (납품 전 검수)
- [ ] 출력은 **코드가 아니라 통 랜딩 이미지 1장**(긴 세로 구성, 섹션 순서 유지)
- [ ] 사후 포렌식(SD카드/GPS 분석) 섹션 포함 — "해킹 아니라 합법 포렌식" 프레이밍
- [ ] 영어만, 농담/이모지 없음, 전문적 톤
- [ ] Inter 얇은 weight, 작은 대문자 eyebrow 라벨
- [ ] 사진 에셋이 풀블리드 배경 + 어두운 스크림
- [ ] 모든 버튼/카드/인풋 직각(radius 0)
- [ ] 시그니처 국방카키(`#86855F`)
- [ ] AI 티 나는 요소(글래스모피즘/네온/글로우/둥근 blob) 없음
- [ ] 길고(10 섹션) 반응형
