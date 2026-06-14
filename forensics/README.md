# `forensics/` — TaloNet post-capture forensics (architecture & interfaces)

> **Forensics, not intrusion.** Nothing here boots, talks to, jams, or spoofs a
> device. This package analyses the storage/logs of an enemy drone that has been
> **physically captured and safely secured** by the net interceptor — legal
> post-incident analysis of seized property, the same ethically-clean posture as
> the rest of TaloNet (`defense/` hardens *us*; `forensics/` reads what we caught).

Full pipeline, integrity / chain-of-custody procedure, and the verified
open-source parser list live in [`docs/08_사후_포렌식.md`](../docs/08_사후_포렌식.md).

## Status

**Implemented and tested.** The full pipeline runs end-to-end on real verified
open-source parsers; the core (interfaces, pipeline, chain-of-custody, geo math,
hashing, imaging) needs zero third-party deps, and the parser/report/map adapters
light up when `requirements-forensics.txt` is installed. Heavy libraries are
imported lazily, so `import forensics` works with nothing installed.

```python
from forensics import ForensicAppliance
app = ForensicAppliance(work_dir="/var/forensiq/work", evidence_usb="/mnt/evidence")
report, coc = app.process_card(
    evidence_id="EV-2026-0014", source_path="/mnt/wb_card",  # write-blocked mount
    seized_by="operator-A", device_description="32GB microSD ex netted FPV",
    witness="operator-B")
assert coc.verify()          # tamper-evident custody chain intact
print(report.pdf_path)        # threat-intel PDF (also printed + archived to USB)
```

## Layout

| File | Role |
|------|------|
| `interfaces.py` | Data contracts + stage `Protocol`s (`Imager`, `HashVerifier`, `ContentAnalyzer`, `FlightLogParser`, `TrajectoryAnalyzer`, `ReportBuilder`) |
| `geo.py` | Dependency-free trajectory math: haversine, bearing, bounding box, loiter/dwell detection |
| `chain_of_custody.py` | `ChainOfCustody` — append-only, **hash-chained** (tamper-evident) custody log |
| `pipeline.py` | `ForensicPipeline` — enforces 7-stage order + integrity gates (hash mismatch ⇒ `IntegrityError`, no report) |
| `printing.py` | Built-in printer sinks: text / 80mm ESC/POS thermal / CUPS-PDF |
| `appliance.py` | `ForensicAppliance` — high-level card→analysis→print→archive workflow |
| `adapters/imaging.py` | `DiskImager` — read-only bit/logical copy + SHA-256 (optional `dc3dd`) |
| `adapters/hashing.py` | `Sha256Verifier` — stdlib |
| `adapters/content.py` | `FileSystemContentAnalyzer` — inventory, log discovery, identifiers, optional ExifTool |
| `adapters/flightlog.py` | `ArduPilotLogParser` (pymavlink), `Px4UlogParser` (pyulog), `NmeaLogParser` (pynmea2), `DjiLogParser`, `LogParserRouter` |
| `adapters/trajectory.py` | `TrajectoryReconstructor` — launch/target estimate + folium map |
| `adapters/report.py` | `PdfReportBuilder` (fpdf2) + thermal-friendly text formatter |

## Pipeline (7 stages)

```
intake → imaging(write-blocker) → hash(SHA-256) → content(TSK/binwalk/exiftool)
       → flight-log(pymavlink/pyulog/pynmea2/dji) → trajectory(gpxpy/folium) → report
```

Each stage is a `Protocol`, so a concrete class is just an **adapter around a
verified OSS tool** — no hand-rolled parsers. The pipeline owns ordering and the
integrity checks (original/image hash match) and **never writes to the original
evidence**.

## Design choices (mirrors `defense/`)

- **Delegate to verified tools.** Parsing/imaging defer to audited open-source
  (pymavlink, pyulog, The Sleuth Kit, dc3dd, libewf). The repo keeps only the
  thin, auditable orchestration + integrity logic.
- **Integrity first.** Append-only hash-chained custody log; image is verified
  against the original before any analysis runs.
- **Human-in-the-loop.** Launch/target/intent estimates always carry a
  confidence and an evidence basis — never asserted as certainty.

## Run (chain-of-custody self-check)

```python
from forensics import ChainOfCustody

coc = ChainOfCustody("EV-2026-0014")
coc.record("operator-A", "intake", "32GB microSD recovered from netted FPV", witness="operator-B")
coc.record("examiner-1", "imaging", "dc3dd raw image + SHA-256", witness="operator-B")
assert coc.verify()  # tamper-evident chain intact
```
