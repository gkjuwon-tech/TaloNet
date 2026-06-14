# 10. ForensIQ-1 — Operator Guide

**TaloNet ForensIQ-1 Field Forensic Appliance — Operator's Manual**
Document type: field operating procedure · Audience: trained forensic operators
Read [§1 Safety & Legal](#1-safety--legal-notice) before first use.

---

## 1. Safety & Legal Notice

- **Lawful forensics only.** ForensIQ-1 is for read-only analysis of storage
  media from drones that have been **physically captured and secured** under
  proper authority. It is **not** an intrusion, jamming, or interception tool.
- **Never boot the seized device.** Remove the storage card and read it **only**
  through the WRITE-BLOCKED slot. Hostile firmware may wipe or self-destruct if
  powered in an unauthorized environment.
- **Never insert a seized card into any non–write-blocked port** (e.g. a bare
  USB reader). If in doubt, stop.
- **Two-person integrity.** Acquisition, hashing, and sealing are performed with
  an operator **and** a witness; both sign the chain-of-custody record.
- **Preserve the original.** All analysis runs on a verified copy. The original
  card is sealed and returned to evidence storage immediately after imaging.
- **Electrical safety.** Use the supplied AC/DC inlet; the internal UPS enables a
  clean shutdown — do not yank power mid-acquisition.

---

## 2. Hardware overview

Front panel (operator side):

| Control / feature | Description |
|---|---|
| **7" touchscreen** (left) | Operator UI: case workflow, live status, findings review. |
| **WRITE-BLOCKER module** (upper right) | Recessed **microSD** (upper) and **SD** (lower) slots behind the hardware write-blocker, with a **green "BLOCKED" LED** beside the slots. |
| **START** button (green) | Begin the acquisition + analysis run. |
| **EJECT** button (amber) | Release the card after the run completes. |
| **Status-LED row** | Power · Activity · **WRITE-BLOCKED** · Error · Done. |
| **Key-lock cylinder** | Tamper lock; case actions require the key. |
| **Printer paper-exit + tear bar** (lower right) | 80 mm thermal report output. |

Rear panel: AC/DC inlet · Gigabit Ethernet (airgapped by default) ·
**Evidence USB** (write-once export) · Kensington lock slot · cooling vents.
Top: carry handle. Inside (service access): compute board, write-blocker PCB,
thermal printer + paper roll, NVMe SSD, UPS/battery, fan.

A 3/4 render of the front panel is in
[`cad/forensic_appliance.scad`](../cad/forensic_appliance.scad); full hardware
design is in [docs/09](09_Forensic_Appliance_Design.md).

---

## 3. Pre-use checklist

1. **Power & UPS:** mains connected; UPS charge ≥ 30 %.
2. **Thermal paper:** 80 mm roll loaded, cover latched, a tab of paper protruding.
3. **Write-blocker self-test:** on power-up the unit verifies the blocker; the
   **WRITE-BLOCKED LED** must pass self-test (see §8 if it shows red).
4. **Storage:** internal SSD free space ≥ expected card size × 1.2.
5. **Time:** RTC shows correct **UTC**; if drifted, re-sync at provisioning.
6. **Evidence USB:** a write-once / WORM USB is inserted in the rear Evidence port
   (for PDF/map export). Optional but recommended.

---

## 4. Step-by-step operation

### 4.1 Power on & self-test
Turn the key to **ON** and press power. The unit boots, runs the write-blocker
and storage self-tests, and shows the **Home** screen. Confirm all status LEDs
are nominal (Error LED off).

### 4.2 Authenticate
Log in at the touchscreen with your operator credential (PIN/badge). The witness
is recorded for two-person integrity.

### 4.3 Open a new case
Tap **New Case** and enter:
- **Evidence ID** (links to the capture mission ID / coordinates / time),
- **Seized-by** and **Seized-at (UTC)**,
- **Witness**,
- **Device description** (card type, capacity, markings/serial, photo).

This opens the **chain-of-custody** record (an append-only, hash-chained log).

### 4.4 Insert the card — confirm WRITE-BLOCKED
Insert the seized **microSD** or **SD** card into the labelled WRITE-BLOCKER
slot. **Verify the WRITE-BLOCKED LED is solid green** before continuing.
> If the LED is **not green**, remove the card and STOP — do not analyze.

### 4.5 Acquire (image + verify)
Press **START**. The appliance makes a read-only copy to the internal SSD and
computes **SHA-256** of both the source and the image.
- **Hashes match** → acquisition verified; analysis proceeds.
- **Hashes differ** → the run **halts** with an integrity error (see §8). Re-image.

### 4.6 Automatic analysis
The pipeline runs unattended:
- **Content / metadata** — file inventory (hashed), media EXIF, device
  identifiers (FCC ID / serial / MAC).
- **Flight-log parsing** — auto-detected and parsed by verified open-source
  parsers: ArduPilot `.bin`/`.tlog` (pymavlink), PX4 `.ulg` (pyulog), NMEA
  (pynmea2), DJI (dji-log-parser).
- **Trajectory & intent** — reconstructs the track and estimates the **launch**
  point and **target/observation** area (longest loiter), each with a
  **confidence score**.

### 4.7 Review on screen
Inspect the **map**, the launch/target estimates and confidence, identifiers,
and the file/media summary. Confidence is an investigative weighting — **not a
certainty** (see §5).

### 4.8 Print the report
Tap **Print Report**. The **built-in thermal printer** prints the threat-intel
report plus the **chain-of-custody appendix**. The full **PDF** (with the
trajectory map) is automatically archived to the **Evidence USB**.

### 4.9 Eject, seal, close
Press **EJECT**, remove the card, apply a **tamper seal**, and have the operator
and witness sign. Tap **Close Case** — the seal event is appended to the custody
log and the case is finalized.

---

## 5. Understanding the report

| Section | Meaning |
|---|---|
| **Header** | Evidence ID, UTC generation time, overall confidence (0–1). |
| **Executive summary** | Estimated launch/origin and target/observation point. |
| **Trajectory & intent** | Parser provenance, path length, launch→target range/bearing, operating-area bounding box, loiter evidence. |
| **Identifiers (IFF)** | Recovered FCC ID / serial / MAC, for attribution. |
| **Content & payload** | File inventory count, media metadata, altitude profile. |
| **Chain-of-custody appendix** | Every step, actor, witness, and timestamp. |
| **Tooling & provenance** | Exact parser/library versions used. |

> **All estimates carry a confidence and an evidence basis. Nothing is asserted
> as certainty.** Launch/target are leads for an analyst, derived only from what
> the recovered logs contain; GPS multipath, log corruption, or partial data
> widen uncertainty.

---

## 6. Maintenance

- **Thermal paper:** open the printer cover, drop in an 80 mm roll (thermal side
  out), feed a tab through the exit, close the cover.
- **Card slots:** blow out dust; never insert non-write-blocked adapters.
- **Software/firmware:** apply only **signed** update packages over the wired
  enclave network; verify the signature before installing.
- **Battery/UPS:** check charge monthly; replace per the cell datasheet.
- **Seals & lock:** inspect tamper seals each use; report any compromise.

---

## 7. Specifications

| Item | Spec |
|---|---|
| Compute | Raspberry Pi CM4 / NUC-class, runs `forensics/` pipeline |
| Display | 7" capacitive touchscreen, 1024×600 |
| Intake | microSD + SD behind a **hardware write-blocker** |
| Printer | 80 mm ESC/POS thermal, auto-cutter |
| Archive | internal NVMe SSD (encrypted) + write-once Evidence USB |
| Time | DS3231 RTC (UTC) |
| Power | AC/DC inlet + LiFePO4 UPS |
| Network | Gigabit Ethernet (airgap default); no Wi-Fi/cellular |
| Security | key-lock, tamper seals, Kensington slot, append-only audit log |
| Enclosure | rugged khaki case (`cad/forensic_appliance.scad`) |

---

## 8. Troubleshooting

| Symptom | Action |
|---|---|
| **WRITE-BLOCKED LED red / not green** | Remove the card. Do **not** analyze. Re-seat the card; if still red, the write-blocker failed self-test — take the unit out of service. |
| **Hash mismatch (integrity error)** | The image does not match the source. **STOP**, re-seat the card, and re-image. Persistent mismatch ⇒ failing card/reader; document and escalate. |
| **"Unsupported log format"** | The log is not a recognized ArduPilot/PX4/NMEA/DJI type, or DJI logs are encrypted and need the dji-log-parser key. Export the raw files via Evidence USB for offline analysis; record the limitation in the report. |
| **Printer out of paper / jam** | Reload the 80 mm roll (§6). The PDF is already on the Evidence USB; reprint from the case screen. |
| **Low confidence / no fixes** | Few/no GPS fixes were recovered. The report notes this; treat launch/target as weak leads and corroborate with other evidence. |
| **No Evidence USB detected** | Insert a write-once USB in the rear port and reprint/re-export; the PDF is retained on the internal SSD until exported. |

---

## 9. Chain-of-custody & evidence handling (appendix)

- Open the custody record **before** inserting the card; close it only after
  sealing.
- The log is **append-only and hash-chained** — any later edit breaks the chain
  and is detected on verification.
- Record every hand-off (time, from, to, reason, signatures).
- Keep the original card sealed; perform all analysis on the verified copy.
- Export the report PDF + custody log to write-once media; retain per policy.

> Pipeline internals: [docs/08](08_사후_포렌식.md) · hardware: [docs/09](09_Forensic_Appliance_Design.md) · software: [`forensics/`](../forensics/).
