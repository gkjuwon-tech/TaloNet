# 09. ForensIQ-1 — Counter-UAS Exploitation Appliance (Hardware Design)

> **TaloNet ForensIQ-1** is a sealed, benchtop/field **counter-UAS exploitation
> kiosk**. An operator removes the microSD/SD card from a hostile drone that the
> TaloNet net interceptor has **non-kinetically captured and secured**, inserts it
> into a **write-blocked** slot, and the appliance runs the TaloNet exploitation
> pipeline (`forensics/`, [docs/08](08_사후_포렌식.md)) to geolocate the **hostile
> launch site** and **print a counter-UAS target-intelligence report on a built-in
> thermal printer**, archiving the full PDF to a write-once Evidence USB. Nothing
> on the card is booted, modified, or transmitted to.
>
> The product is **target intelligence to support a proportionate,
> human-authorized self-defence response** against the source of an attack the
> adversary initiated — **not a fire order**, and not autonomous engagement. Every
> engagement decision remains with the authorized commander under the Rules of
> Engagement and the Law of Armed Conflict (distinction, proportionality,
> precautions; never civilians or civilian objects).
>
> Mechanical model: [`cad/forensic_appliance.scad`](../cad/forensic_appliance.scad).
> Operator manual: [docs/10](10_Forensic_Appliance_Operator_Guide.md).

---

## 1. Purpose & threat model

| | |
|---|---|
| **In scope** | Read-only acquisition and exploitation of the **non-volatile storage** (microSD/SD, and via adapter eMMC/USB) of a hostile drone that is **already physically secured**; output is **counter-UAS target intelligence** (chiefly the hostile launch site with an uncertainty radius). |
| **Out of scope (forbidden)** | Booting the seized device, writing to it, real-time interception, jamming, spoofing, reaching any *other* system, or any **autonomous engagement / automated targeting**. |
| **Basis (self-defence)** | The adversary struck first with hostile intent; TaloNet only **defended** (non-kinetic capture, no first strike, no RF jamming/spoofing). Geolocating the **source of that attack** for a proportionate response is a legitimate **self-defence / counter-UAS targeting** function — offline technical exploitation of secured hardware (TECHINT/DOMEX), not real-time intrusion. |
| **Human control (ROE/LOAC)** | The appliance produces **intelligence only**. Whether, how, and when to engage is a **human commander's decision** under the Rules of Engagement and the Law of Armed Conflict — distinction, proportionality, precautions; never civilians or civilian objects. Estimates carry confidence + an uncertainty radius and must be corroborated. |
| **Anti-forensic safety** | The card is **never powered as a bootable device** — it is read behind a hardware **write-blocker** so a hostile firmware's "unauthorized-environment → wipe/self-destruct" logic is never triggered. |

---

## 2. System block diagram

```mermaid
graph TD
    CARD["Seized microSD / SD card"] --> WB["HARDWARE WRITE-BLOCKER\n(read-only) + card reader"]
    WB -->|read-only USB| SBC["Compute (Raspberry Pi CM4 / NUC-class)\nruns forensics/ pipeline"]
    RTC["RTC (DS3231)"] --> SBC
    SSD["Internal NVMe SSD\n(working images + case store)"] <--> SBC
    SBC --> TS["7\" capacitive touchscreen\n(operator UI)"]
    SBC --> PRN["Built-in 80 mm ESC/POS\nthermal printer"]
    SBC --> EUSB["EVIDENCE USB port\n(write-once / WORM export)"]
    SBC --> ETH["Gigabit Ethernet\n(AIRGAP by default)"]
    UPS["UPS / battery (LiFePO4)"] --> SBC
    PWR["AC/DC inlet"] --> UPS
    KEY["Key-lock + tamper seals"] -.-> CASE["Sealed khaki enclosure"]
    FAN["Cooling fan"] --> SBC
```

**Read path is one-way:** card → write-blocker → compute. There is no electrical
path that can write the card. Outputs go to the screen, the thermal printer, and
the write-once Evidence USB only.

---

## 3. Subsystems

| Subsystem | Function | Notes |
|-----------|----------|-------|
| **Write-blocker + card intake** | Hardware read-only bridge for the seized card; front-panel microSD + SD slots behind a labelled WRITE-BLOCKER module with a **green "BLOCKED" LED**. | Hardware blocker is the trust anchor; the SD mechanical lock tab is *not* relied upon. |
| **Compute (SBC)** | Runs `forensics/` (imaging, hashing, parsing, trajectory/intent, report). | Raspberry Pi **CM4** carrier or an Intel **NUC**-class board; `requirements-forensics.txt` preinstalled. |
| **Touchscreen UI** | Case workflow: open case, confirm write-block, run, review, print, seal. | 7" capacitive, 1024×600. |
| **Built-in thermal printer** | Prints the threat-intel report + chain-of-custody appendix at the point of analysis. | 80 mm ESC/POS, driven via `forensics.printing.ThermalPrinter`. |
| **PDF archive + Evidence USB** | Full report PDF + trajectory map written to a **write-once / WORM** USB for evidentiary export. | `forensics.ForensicAppliance` copies PDF/map to the USB mount. |
| **Internal NVMe SSD** | Working images, case database, audit logs (append-only). | Encrypted at rest; never the seized media. |
| **RTC** | Trustworthy UTC timestamps for hashes and custody events. | DS3231; synced/sealed at provisioning. |
| **UPS / battery** | Field autonomy + clean shutdown; prevents corruption mid-acquisition. | LiFePO4 UPS HAT / DC-UPS. |
| **Networking** | **Airgapped by default.** Gigabit Ethernet only for signed software updates / case export in a controlled enclave. | No Wi-Fi / cellular by policy. |
| **Tamper / physical security** | Keyed lock, tamper-evident seals, Kensington-style lock slot. | Two-person integrity for case handling. |

---

## 4. Bill of materials (representative real parts)

> Plausible commercial parts; substitute equivalents as procurement allows. The
> **hardware write-blocker** is the one non-negotiable trust component.

| Block | Part (example) | Spec |
|-------|----------------|------|
| Compute | **Raspberry Pi Compute Module 4** (4 GB/32 GB eMMC) + carrier (e.g. Waveshare CM4 carrier) *(alt: Intel NUC 13)* | quad-A72 / x86; USB3, GbE, PCIe NVMe |
| Touchscreen | **7" capacitive DSI display, 1024×600** (e.g. Waveshare 7" DSI) | 10-pt touch |
| **Write-blocker** | **Hardware USB write-blocker** (e.g. CRU WiebeTech USB WriteBlocker) + USB SD/microSD reader | enforced read-only |
| Printer | **80 mm panel-mount ESC/POS thermal printer** (e.g. Rongta RP05 / generic 80 mm, TTL/USB) | receipt-style report, auto-cutter |
| Storage | **NVMe SSD 512 GB** (working/case store, LUKS-encrypted) | not the seized media |
| Evidence export | **Write-once / WORM USB** or USB with hardware write-protect switch | evidentiary PDF/map |
| RTC | **DS3231** real-time clock + coin cell | sealed UTC time source |
| UPS | **LiFePO4 UPS HAT / DC-UPS** (e.g. PiJuice / Geekworm X1200-class) | clean shutdown, field run |
| Cooling | **60 mm fan** + filtered intake | thermal headroom under VLM-free load |
| Networking | **Gigabit Ethernet** (onboard) | airgap default |
| Enclosure | **Rugged khaki case** (Pelican/ammo-can class), keyed lock, tamper seals | per `cad/forensic_appliance.scad` |
| Indicators | Power / Activity / **WRITE-BLOCKED (green)** / Error / Done LEDs | front-panel row |
| Controls | START + EJECT illuminated pushbuttons, key-lock cylinder | front panel |

---

## 5. Data & print flow

```
1. INSERT  captured card into the WRITE-BLOCKED slot (green LED confirms read-only)
2. IMAGE   read-only bit/logical copy to the internal SSD  (forensics DiskImager)
3. HASH    SHA-256 of source vs image — must match, else STOP (IntegrityError)
4. PARSE   content + flight logs: pymavlink (.bin/.tlog), pyulog (.ulg),
           pynmea2 (NMEA), dji-log-parser (DJI)
5. ANALYZE HOSTILE LAUNCH SITE (origin) + uncertainty radius + confidence;
           intended target (loiter); folium map  (trajectory.py)
6. REPORT  fpdf2 counter-UAS target-intel PDF + thermal text report
7. OUTPUT  -> built-in thermal printer (target packet + provenance appendix +
              ROE/LOAC caveat) -> write-once Evidence USB (full PDF + map)
8. HANDOFF eject card, seal; the packet goes to the authorized command/fires cell,
           which decides any response under ROE/LOAC (the appliance does not engage)
```

Every step is appended to a tamper-evident **hash-chained provenance log**
(`forensics.ChainOfCustody`) so the commander can trust the intelligence; the
report bundles that log as an appendix. The high-level call is a single
`forensics.ForensicAppliance.process_card(...)`.

---

## 6. Mechanical model & verification

`cad/forensic_appliance.scad` is the parametric massing/packaging model
(enclosure, front panel, internal layout). Front-panel features (touchscreen,
write-blocker + card slots, printer exit, buttons/LEDs/key-lock) are
**self-contained solids unioned on top of the cut body**, so panel cutouts never
consume them — the model stays 2-manifold.

```
openscad -o appliance.stl cad/forensic_appliance.scad
# Simple: yes  (~3,566 vertices / ~2,398 facets, OpenSCAD 2021.01)
```

Key parameters are exposed in the Customizer (case W/D/H, wall thickness, screen
diagonal/bezel, write-blocker block + slot sizes, printer bay + paper slot,
button/LED/key-lock sizes, SBC board, fan, vents). See
[`cad/README.md`](../cad/README.md).

---

## 7. Security, integrity & control properties
- **One-way read path:** no electrical route writes the captured card.
- **Verified copy:** acquisition is rejected unless source/image SHA-256 match.
- **Tamper-evident provenance:** append-only hash-chained log; encrypted SSD — so
  the commander can trust the launch-site geolocation.
- **Intelligence only / human-in-the-loop:** the appliance never engages; it emits
  a target packet with confidence + uncertainty radius and an explicit ROE/LOAC
  caveat. Engagement is a human decision (distinction, proportionality, precautions).
- **Airgap default:** no radio; Ethernet only for signed updates / controlled export.
- **Two-person integrity & sealing:** keyed lock + tamper seals; operator + witness.

> Next: [docs/10 Operator Guide](10_Forensic_Appliance_Operator_Guide.md) ·
> pipeline internals in [docs/08](08_사후_포렌식.md) and [`forensics/`](../forensics/).
