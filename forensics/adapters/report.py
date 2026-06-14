"""Threat-intelligence report builder (PDF via fpdf2) + plain-text formatter.

:class:`PdfReportBuilder` renders an :class:`~forensics.interfaces.AnalysisFindings`
plus the chain-of-custody log into an archival PDF. :func:`format_text_report`
produces the same content as 80mm-friendly plain text for the appliance's
built-in thermal printer. fpdf2 is imported lazily.

All output is ASCII so it renders on PDF core fonts and ESC/POS thermal heads
without a Unicode font; estimates always carry a confidence and a disclaimer —
nothing is asserted as certainty.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from ..interfaces import AnalysisFindings, ForensicReport, TrackPoint

_BANNER = "TaloNet ForensIQ // POST-CAPTURE FORENSICS // LAWFUL-FORENSIC USE"
_DISCLAIMER = (
    "Estimates are derived from recovered logs by verified open-source parsers "
    "and carry a confidence score; they are investigative leads, not certainties. "
    "Analysis is performed on physically-secured seized media (read-only, "
    "hash-verified) under chain-of-custody."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pt(p: TrackPoint | None) -> str:
    if p is None:
        return "n/a"
    alt = f", {p.alt_m:.0f} m" if p.alt_m is not None else ""
    t = f" @ {p.t_utc}" if p.t_utc else ""
    return f"{p.lat:.6f}, {p.lon:.6f}{alt}{t}"


def format_text_report(
    evidence_id: str,
    findings: AnalysisFindings,
    custody_log: list[dict[str, str]],
    tool_versions: dict[str, str] | None = None,
) -> str:
    """Plain-text rendering (thermal-printer / console friendly)."""
    L: list[str] = []
    L.append("=" * 40)
    L.append("TaloNet ForensIQ - THREAT INTEL REPORT")
    L.append("=" * 40)
    L.append(f"Evidence ID : {evidence_id}")
    L.append(f"Generated   : {_utc_now()}")
    L.append(f"Confidence  : {findings.confidence:.2f} (0-1)")
    L.append("-" * 40)
    L.append("TRAJECTORY / INTENT")
    L.append(f"  Launch est.: {_pt(findings.launch_estimate)}")
    L.append(f"  Target est.: {_pt(findings.target_estimate)}")
    for line in findings.evidence_basis:
        L.append(f"  - {line}")
    if findings.identifiers:
        L.append("-" * 40)
        L.append("IDENTIFIERS (IFF)")
        for k, v in findings.identifiers.items():
            L.append(f"  {k}: {v}")
    if findings.payload_assessment:
        L.append("-" * 40)
        L.append("CONTENT / PAYLOAD")
        for line in findings.payload_assessment:
            L.append(f"  - {line}")
    L.append(f"  files inventoried: {len(findings.file_inventory)}")
    L.append(f"  media records    : {len(findings.media_metadata)}")
    L.append("-" * 40)
    L.append("CHAIN OF CUSTODY")
    for ev in custody_log:
        L.append(
            f"  [{ev.get('timestamp', '')}] {ev.get('action', '')} "
            f"by {ev.get('actor', '')}"
            + (f" / wit {ev['witness']}" if ev.get("witness") else "")
        )
        if ev.get("detail"):
            L.append(f"      {ev['detail']}")
    if tool_versions:
        L.append("-" * 40)
        L.append("TOOLING")
        for k, v in tool_versions.items():
            L.append(f"  {k}: {v}")
    L.append("-" * 40)
    L.append("NOTE: " + _DISCLAIMER)
    L.append("=" * 40)
    return "\n".join(L)


class PdfReportBuilder:
    """Implements :class:`forensics.interfaces.ReportBuilder` (PDF via fpdf2)."""

    def __init__(self, out_dir: str = ".", tool_versions: dict[str, str] | None = None) -> None:
        self.out_dir = out_dir
        self.tool_versions = tool_versions or {}

    def build(
        self,
        evidence_id: str,
        findings: AnalysisFindings,
        custody_log: list[dict[str, str]],
    ) -> ForensicReport:
        from fpdf import FPDF  # lazy: LGPL dependency
        from fpdf.enums import XPos, YPos

        os.makedirs(self.out_dir, exist_ok=True)
        pdf_path = os.path.join(self.out_dir, f"{evidence_id}_report.pdf")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        def h(text: str, size: int = 13) -> None:
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", size)
            pdf.set_fill_color(134, 133, 95)  # signature khaki #86855F
            pdf.set_text_color(255, 255, 255)
            pdf.cell(pdf.epw, 8, f" {text}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

        def body(text: str, size: int = 10) -> None:
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "", size)
            pdf.multi_cell(pdf.epw, 5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                           wrapmode="CHAR")

        # banner + title
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 4, _BANNER, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 17)
        pdf.cell(0, 10, "Threat Intelligence Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        body(f"Evidence ID: {evidence_id}    Generated: {_utc_now()}    "
             f"Confidence: {findings.confidence:.2f}/1.0")
        pdf.ln(2)

        h("1. Executive Summary")
        body(
            f"Estimated launch/origin: {_pt(findings.launch_estimate)}\n"
            f"Estimated target/observation: {_pt(findings.target_estimate)}\n"
            f"Assessment confidence: {findings.confidence:.2f} (0-1)."
        )
        pdf.ln(1)

        h("2. Trajectory & Intent")
        for line in findings.evidence_basis or ["no trajectory recovered"]:
            body(f"- {line}")
        if findings.map_html_path:
            body(f"Interactive map: {os.path.basename(findings.map_html_path)} "
                 "(archived alongside this report).")
        pdf.ln(1)

        if findings.identifiers:
            h("3. Identifiers (IFF / Attribution)")
            for k, v in findings.identifiers.items():
                body(f"- {k}: {v}")
            pdf.ln(1)

        h("4. Content & Payload")
        for line in findings.payload_assessment or ["no content findings"]:
            body(f"- {line}")
        body(f"- files inventoried: {len(findings.file_inventory)}; "
             f"media records: {len(findings.media_metadata)}")
        pdf.ln(1)

        h("5. Chain-of-Custody Appendix")
        for ev in custody_log:
            wit = f" / witness {ev['witness']}" if ev.get("witness") else ""
            body(f"[{ev.get('timestamp', '')}] {ev.get('action', '')} by "
                 f"{ev.get('actor', '')}{wit}\n    {ev.get('detail', '')}")
        pdf.ln(1)

        if self.tool_versions:
            h("6. Tooling & Provenance")
            for k, v in self.tool_versions.items():
                body(f"- {k}: {v}")
            pdf.ln(1)

        h("Legal / Ethical Note")
        body(_DISCLAIMER)

        pdf.output(pdf_path)
        return ForensicReport(
            evidence_id=evidence_id,
            findings=findings,
            map_html_path=findings.map_html_path,
            pdf_path=pdf_path,
            custody_log=custody_log,
            tool_versions=self.tool_versions,
        )
