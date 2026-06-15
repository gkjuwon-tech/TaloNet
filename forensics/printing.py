"""Report output to the appliance's built-in printer.

Two real sinks plus a dependency-free default:

- :class:`TextReportPrinter` — writes the plain-text report next to the PDF (and
  optionally echoes to stdout). Default; stdlib only; always works (and testable).
- :class:`ThermalPrinter` — drives an 80mm ESC/POS panel-mount thermal printer
  via **python-escpos**, imported lazily.
- :class:`CupsPdfPrinter` — sends the archival PDF to a CUPS queue via ``lp``.

A printer takes a built :class:`~forensics.interfaces.ForensicReport` and emits
the human-readable threat-intel report + chain-of-custody appendix.
"""

from __future__ import annotations

import os
import subprocess

from .adapters.report import format_text_report
from .interfaces import ForensicReport


def _text(report: ForensicReport) -> str:
    return format_text_report(
        report.evidence_id, report.findings, report.custody_log, report.tool_versions
    )


class TextReportPrinter:
    """Stdlib default: persist the text report (and optionally echo it)."""

    def __init__(self, out_dir: str | None = None, echo: bool = False) -> None:
        self.out_dir = out_dir
        self.echo = echo

    def print_report(self, report: ForensicReport) -> str:
        text = _text(report)
        out_dir = self.out_dir or (
            os.path.dirname(report.pdf_path) if report.pdf_path else "."
        )
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{report.evidence_id}_report.txt")
        with open(path, "w") as fh:
            fh.write(text)
        if self.echo:
            print(text)
        return path


class ThermalPrinter:
    """80mm ESC/POS thermal printer (python-escpos)."""

    def __init__(self, device: str = "/dev/usb/lp0", cut: bool = True) -> None:
        self.device = device
        self.cut = cut

    def print_report(self, report: ForensicReport) -> str:
        from escpos.printer import File  # lazy: GPL-3.0 dependency

        printer = File(self.device)
        printer.set(align="left")
        printer.text(_text(report) + "\n")
        if self.cut:
            printer.cut()
        return self.device


class CupsPdfPrinter:
    """Send the archival PDF to a CUPS print queue via ``lp``."""

    def __init__(self, queue: str | None = None) -> None:
        self.queue = queue

    def print_report(self, report: ForensicReport) -> str:
        if not report.pdf_path or not os.path.exists(report.pdf_path):
            raise FileNotFoundError("report has no PDF to print")
        cmd = ["lp"]
        if self.queue:
            cmd += ["-d", self.queue]
        cmd.append(report.pdf_path)
        subprocess.run(cmd, check=True)
        return report.pdf_path
