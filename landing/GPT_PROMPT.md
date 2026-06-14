# GPT prompt — TaloNet landing page (image generation + build)

> 사용법: 아래 **PROMPT** 블록을 통째로 ChatGPT(이미지 생성 가능한 모델)에 붙여넣으면, 배경용 사진 에셋을 생성하고 그 에셋을 깐 랜딩페이지(단일 `index.html`)를 만들어 준다. Devin도 동일 사양으로 이미 `landing/index.html`을 구현해 두었으니, GPT 결과물과 비교/대체용으로 쓰면 된다.

---

## PROMPT (copy-paste, English)

```
You are a senior product designer + front-end engineer. Build a single-file,
production-quality marketing landing page for a real defense-technology company.
Do TWO things, in order:

PART 1 — GENERATE PHOTOGRAPHIC BACKGROUND ASSETS
Generate a set of cinematic, photo-realistic background images (NOT illustrations,
NOT 3D renders, NOT AI-art clichés). They must look like real defense/aerospace
photography shot on a full-frame camera. Desaturated, muted, documentary feel.
Generate these assets:
  1. hero.jpg (wide, 2400x1350) — a large multi-rotor counter-UAS interceptor
     drone (octocopter, ~1m span, carbon-fibre, matte dark-grey) hovering against
     an overcast dusk sky. Cold, flat light. Negative space on the right for text.
  2. capture.jpg (wide, 2400x1350) — abstract close-up of a deployed catch-net /
     kevlar mesh against blurred sky, shallow depth of field.
  3. ops.jpg (wide, 2400x1350) — a dim ground-control / operations room, screens
     out of focus, no readable text, no logos, no faces.
  4. field.jpg (wide, 2400x1350) — open empty field / riverbed from above at
     altitude, overcast, for the "safe-drop / disposal" section.
Constraints for all images: muted military KHAKI + charcoal palette, no neon, no
purple gradients, no lens flares, no text baked into the image, no people's faces,
realistic grain, slightly underexposed. They are BACKGROUNDS, so they will sit
behind a dark overlay — keep them low-contrast and uncluttered.

PART 2 — BUILD THE LANDING PAGE (single index.html, inline CSS)
Use the generated images as full-bleed section backgrounds with a dark scrim
(linear-gradient overlay, ~55-75% opacity) so light text stays readable.

Brand: "TaloNet" — physical counter-UAS interception. A large mothership drone
nets hostile drones and either recovers them to base or safely drops dangerous
ones (e.g. kamikaze types) in unpopulated areas. NO jamming, NO spoofing, NO
hacking — purely physical capture, plus a defensive on-board security stack
(GNSS anti-spoofing, MAVLink command-link signing).

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

Make it LONG — a full landing page with these sections, in order:
  1. Sticky top nav (wordmark left "TALONET", anchor links, one khaki CTA
     "Request briefing").
  2. Hero (hero.jpg bg): thin headline e.g. "Physical airspace defense.",
     one-sentence subhead, two buttons (primary "Request briefing",
     secondary "View capabilities"). Small spec strip below
     (e.g. 120 km/h · 14 kg MTOW · 8 km radius · <90 s detect-to-deliver).
  3. Problem statement: short editorial paragraph on the small-drone threat +
     why kinetic/jamming answers fall short.
  4. "How it works" — 3 steps: Detect → Decide → Deliver (capture & recover, or
     capture & safe-drop). Square cards, hairline borders, numbered 01/02/03.
  5. Capabilities (capture.jpg bg): grid of capability tiles (Net interception,
     Onboard VLM threat classification, Sensor fusion, GNSS anti-spoofing,
     Command-link signing, Safe disposal).
  6. Platform spec table (the "Geulmae" mothership): clean two-column rows.
  7. Defensive security band (ops.jpg bg): emphasize OSNMA GNSS authentication,
     RAIM, MAVLink 2 message signing — "we don't attack, we harden."
  8. Safe-disposal section (field.jpg bg): recover vs safe-drop logic.
  9. Final CTA band: "Request a briefing" + simple square contact form
     (name / organization / email, square inputs, khaki submit button).
 10. Minimal footer: wordmark, short legal line, nav.

Deliver ONE self-contained index.html with inline <style>, semantic HTML,
responsive (mobile collapses the grids to one column), accessible contrast,
and smooth-scroll anchor nav. Reference the generated images by the filenames
above (./assets/hero.jpg etc.). Output only the code.
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
- [ ] 영어만, 농담/이모지 없음, 전문적 톤
- [ ] Inter 얇은 weight, 작은 대문자 eyebrow 라벨
- [ ] 사진 에셋이 풀블리드 배경 + 어두운 스크림
- [ ] 모든 버튼/카드/인풋 직각(radius 0)
- [ ] 시그니처 국방카키(`#86855F`)
- [ ] AI 티 나는 요소(글래스모피즘/네온/글로우/둥근 blob) 없음
- [ ] 길고(10 섹션) 반응형
