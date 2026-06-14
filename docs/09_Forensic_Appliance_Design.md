# 09. ForensIQ-1 — Forensic Appliance Hardware Design

> **TaloNet ForensIQ-1** is a sealed, benchtop/field **forensic kiosk**. An
> operator removes the microSD/SD card from a drone that the TaloNet net
> interceptor has **physically captured and secured**, inserts it into a
> **write-blocked** slot, and the appliance runs the TaloNet forensics pipeline
> (`forensics/`, [docs/08](08_사후_포렌식.md)) and **prints a threat-intelligence
> report on a built-in thermal printer**, archiving the full PDF to a write-once
> Evidence USB. Nothing on the card is booted, modified, or transmitted to.
>
> Mechanical model: [`cad/forensic_appliance.scad`](../cad/forensic_appliance.scad).
> Operator manual: [docs/10](10_Forensic_Appliance_Operator_Guide.md).

---

## 1. Purpose & threat model

| | |
|---|---|
| **In scope** | Read-only acquisition and analysis of the **non-volatile storage** (microSD/SD, and via adapter eMMC/USB) of an enemy drone that is **already physically secured**. |
| **Out of scope (forbidden)** | Booting the seized device, writing to it, real-time interception, jamming, spoofing, or reaching any *other* system. |
| **Ethical/legal basis** | This is lawful post-incident **forensics on seized property**, consistent with the project's *Clean Defense* posture: non-kinetic physical capture, no RF jamming/spoofing, analysis confined to media under chain-of-custody. Real-time intrusion would be "hacking"; offline analysis of secured evidence is "forensics." |
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
1. INSERT  seized card into the WRITE-BLOCKED slot (green LED confirms read-only)
2. IMAGE   read-only bit/logical copy to the internal SSD  (forensics DiskImager)
3. HASH    SHA-256 of source vs image — must match, else STOP (IntegrityError)
4. PARSE   content + flight logs: pymavlink (.bin/.tlog), pyulog (.ulg),
           pynmea2 (NMEA), dji-log-parser (DJI)
5. ANALYZE trajectory + intent: launch / target (loiter) estimate, folium map
6. REPORT  fpdf2 threat-intel PDF + thermal text report
7. OUTPUT  -> built-in thermal printer (report + chain-of-custody appendix)
           -> write-once Evidence USB (full PDF + map)
8. SEAL    eject card, apply tamper seal, sign — case closed in the custody log
```

Every step is appended to a tamper-evident **hash-chained chain-of-custody log**
(`forensics.ChainOfCustody`); the report bundles that log as an appendix. The
high-level call is a single `forensics.ForensicAppliance.process_card(...)`.

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

## 7. Security & integrity properties
- **One-way read path:** no electrical route writes the seized card.
- **Verified copy:** acquisition is rejected unless source/image SHA-256 match.
- **Tamper-evident audit:** append-only hash-chained custody log; encrypted SSD.
- **Airgap default:** no radio; Ethernet only for signed updates / controlled export.
- **Two-person integrity & sealing:** keyed lock + tamper seals; operator + witness.

> Next: [docs/10 Operator Guide](10_Forensic_Appliance_Operator_Guide.md) ·
> pipeline internals in [docs/08](08_사후_포렌식.md) and [`forensics/`](../forensics/).
