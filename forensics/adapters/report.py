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

_BANNER = "TaloNet ForensIQ // COUNTER-UAS EXPLOITATION // TARGET INTELLIGENCE"
_DISCLAIMER = (
    "INTELLIGENCE PRODUCT, NOT A FIRE ORDER. Estimates are derived from the logs "
    "of a non-kinetically captured hostile UAS by verified open-source parsers and "
    "carry a confidence and an uncertainty radius; they are leads, not certainties. "
    "This supports a PROPORTIONATE, HUMAN-AUTHORIZED self-defence response against "
    "the source of the attack. EVERY engagement decision remains with the authorized "
    "commander under the Rules of Engagement and the Law of Armed Conflict "
    "(distinction, proportionality, precautions). Not for use against civilians or "
    "civilian objects. Verify the launch site by independent means before any action."
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
    radius = (
        f"  +/- {findings.launch_radius_m:.0f} m"
        if findings.launch_radius_m is not None else ""
    )
    L: list[str] = []
    L.append("=" * 40)
    L.append("TaloNet ForensIQ - COUNTER-UAS TARGET INTEL")
    L.append("=" * 40)
    L.append(f"Evidence ID : {evidence_id}")
    L.append(f"Generated   : {_utc_now()}")
    L.append(f"Geo conf.   : {findings.confidence:.2f} (0-1)")
    L.append("-" * 40)
    L.append("HOSTILE LAUNCH SITE (COUNTER-UAS ORIGIN)")
    L.append(f"  {_pt(findings.launch_estimate)}{radius}")
    L.append("  >> actionable origin for proportionate, human-authorized response")
    L.append("-" * 40)
    L.append("INTENDED TARGET (DEFENDED ASSET)")
    L.append(f"  {_pt(findings.target_estimate)}")
    if findings.operating_radius_m or findings.launch_sites:
        L.append("-" * 40)
        L.append("ENEMY BASING (RANGE RING)")
        if findings.operating_radius_m:
            L.append(f"  operating radius ~{findings.operating_radius_m / 1000:.2f} km "
                     "from launch")
        if len(findings.launch_sites) >= 2:
            L.append(f"  {len(findings.launch_sites)} sortie origins; "
                     + ("RECURRING (fixed base)" if findings.recurring_origin
                        else "dispersed"))
    if findings.mission_plan:
        L.append("-" * 40)
        L.append(f"PLANNED MISSION ({len(findings.mission_plan)} waypoints)")
        for i, wp in enumerate(findings.mission_plan[:8]):
            L.append(f"  WP{i} {wp.lat:.6f},{wp.lon:.6f} {wp.fix_quality or ''}")
    if findings.firmware:
        L.append("-" * 40)
        L.append("ATTRIBUTION (firmware / board)")
        for k, v in findings.firmware.items():
            L.append(f"  {k}: {v}")
    if findings.parameters_of_interest:
        L.append("-" * 40)
        L.append("PARAMETERS OF INTEREST (fence/failsafe/radio)")
        for k, v in findings.parameters_of_interest.items():
            L.append(f"  {k} = {v}")
    if findings.imaged_locations:
        L.append("-" * 40)
        L.append(f"ISR IMAGERY GEOTAGS ({len(findings.imaged_locations)})")
        for g in findings.imaged_locations[:8]:
            L.append(f"  {g['lat']},{g['lon']}  {g.get('file', '')}")
    if findings.timeline:
        L.append("-" * 40)
        L.append("TIMELINE")
        for k, v in findings.timeline.items():
            L.append(f"  {k}: {v}")
    L.append("-" * 40)
    L.append("TRAJECTORY / PATTERN OF LIFE")
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
    L.append("INTELLIGENCE PROVENANCE (hash-chained)")
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
    L.append("CAVEAT: " + _DISCLAIMER)
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
        pdf.cell(0, 10, "Counter-UAS Target Intelligence Report",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        body(f"Evidence ID: {evidence_id}    Generated: {_utc_now()}    "
             f"Geolocation confidence: {findings.confidence:.2f}/1.0")
        pdf.ln(2)

        radius = (f" +/- {findings.launch_radius_m:.0f} m"
                  if findings.launch_radius_m is not None else "")
        h("1. Hostile Launch Site (Counter-UAS Origin)")
        body(
            f"HOSTILE LAUNCH SITE: {_pt(findings.launch_estimate)}{radius}\n"
            f"Geolocation confidence: {findings.confidence:.2f} (0-1).\n"
            "Actionable origin of the attack for a proportionate, human-authorized "
            "self-defence response. Confirm by independent means before any action."
        )
        pdf.ln(1)

        h("2. Intended Target (Defended Asset)")
        body(f"The hostile UAS was aimed at: {_pt(findings.target_estimate)}")
        pdf.ln(1)

        if findings.operating_radius_m or len(findings.launch_sites) >= 2:
            h("3. Enemy Basing (Range Ring)")
            if findings.operating_radius_m:
                body(f"- operating radius ~{findings.operating_radius_m / 1000:.2f} km "
                     "from launch => base lies within this ring")
            if len(findings.launch_sites) >= 2:
                body(f"- {len(findings.launch_sites)} sortie origins; "
                     + ("RECURRING (fixed launch site / enemy basing)"
                        if findings.recurring_origin else "dispersed launch points"))
            pdf.ln(1)

        if findings.mission_plan:
            h(f"4. Planned Mission ({len(findings.mission_plan)} waypoints)")
            for i, wp in enumerate(findings.mission_plan[:12]):
                body(f"- WP{i}: {wp.lat:.6f}, {wp.lon:.6f}  {wp.fix_quality or ''}")
            pdf.ln(1)

        if findings.firmware or findings.parameters_of_interest:
            h("5. Attribution & Configuration")
            for k, v in findings.firmware.items():
                body(f"- firmware {k}: {v}")
            for k, v in findings.parameters_of_interest.items():
                body(f"- param {k} = {v}")
            pdf.ln(1)

        if findings.imaged_locations or findings.timeline:
            h("6. ISR Imagery & Timeline")
            for g in findings.imaged_locations[:12]:
                body(f"- imaged {g['lat']}, {g['lon']}  {g.get('file', '')}")
            for k, v in findings.timeline.items():
                body(f"- {k}: {v}")
            pdf.ln(1)

        h("7. Trajectory & Pattern of Life")
        for line in findings.evidence_basis or ["no trajectory recovered"]:
            body(f"- {line}")
        if findings.map_html_path:
            body(f"Interactive map: {os.path.basename(findings.map_html_path)} "
                 "(archived alongside this report).")
        pdf.ln(1)

        if findings.identifiers:
            h("8. Identifiers (IFF / Attribution)")
            for k, v in findings.identifiers.items():
                body(f"- {k}: {v}")
            pdf.ln(1)

        h("9. Content & Payload")
        for line in findings.payload_assessment or ["no content findings"]:
            body(f"- {line}")
        body(f"- files inventoried: {len(findings.file_inventory)}; "
             f"media records: {len(findings.media_metadata)}")
        pdf.ln(1)

        h("10. Intelligence Provenance (hash-chained)")
        for ev in custody_log:
            wit = f" / witness {ev['witness']}" if ev.get("witness") else ""
            body(f"[{ev.get('timestamp', '')}] {ev.get('action', '')} by "
                 f"{ev.get('actor', '')}{wit}\n    {ev.get('detail', '')}")
        pdf.ln(1)

        if self.tool_versions:
            h("11. Tooling & Provenance")
            for k, v in self.tool_versions.items():
                body(f"- {k}: {v}")
            pdf.ln(1)

        h("Caveat - Rules of Engagement / Law of Armed Conflict")
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
