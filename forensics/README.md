# `forensics/` — TaloNet post-capture forensics (architecture & interfaces)

> **Forensics, not intrusion.** Nothing here boots, talks to, jams, or spoofs a
> device. This package analyses the storage/logs of an enemy drone that has been
> **physically captured and safely secured** by the net interceptor — legal
> post-incident analysis of seized property, the same ethically-clean posture as
> the rest of TaloNet (`defense/` hardens *us*; `forensics/` reads what we caught).

Full pipeline, integrity / chain-of-custody procedure, and the verified
open-source parser list live in [`docs/08_사후_포렌식.md`](../docs/08_사후_포렌식.md).

## Status

**Interfaces + pipeline skeleton only.** Concrete acquisition/parsing adapters
(pymavlink, pyulog, pynmea2, The Sleuth Kit, dc3dd/libewf, folium) land in the
next step. The one piece with a working stdlib implementation is the
tamper-evident chain-of-custody log.

## Layout

| File | Role |
|------|------|
| `interfaces.py` | Data contracts (`EvidenceItem`, `AcquiredImage`, `FlightTrack`, `AnalysisFindings`, `ForensicReport`) + stage `Protocol`s (`Imager`, `HashVerifier`, `ContentAnalyzer`, `FlightLogParser`, `TrajectoryAnalyzer`, `ReportBuilder`) |
| `pipeline.py` | `ForensicPipeline` — enforces 7-stage order + integrity gates; raises `NotImplementedError` until adapters are injected |
| `chain_of_custody.py` | `ChainOfCustody` — append-only, **hash-chained** (tamper-evident) custody log (working impl) |

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
