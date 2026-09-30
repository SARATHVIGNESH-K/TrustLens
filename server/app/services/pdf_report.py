"""
PDF verification report generation.

Builds a self-contained forensic report PDF from a VideoRecord + its
AnalysisResult: case details, verdict, authenticity score, reasons,
suspicious timeline, raw forensic signals, and video metadata.

Uses reportlab's platypus layer (flowing document elements) rather than
low-level canvas drawing, so the layout reflows cleanly regardless of how
many reasons/timeline segments a given video has.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

# Palette echoing the web app's evidence/forensics theme, adapted for print
# (print needs darker text on white rather than light text on dark).
INK = colors.HexColor('#14171C')
MUTED = colors.HexColor('#6E737C')
SCANNER = colors.HexColor('#317684')
FLAG = colors.HexColor('#A6362F')
VERIFIED = colors.HexColor('#3B6E49')
HAIRLINE = colors.HexColor('#D8D4C7')


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(
        name='TLTitle', fontName='Helvetica-Bold', fontSize=20, leading=24,
        textColor=INK, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        name='TLLabel', fontName='Helvetica', fontSize=8, leading=10,
        textColor=MUTED, spaceAfter=2, tracking=0.5,
    ))
    ss.add(ParagraphStyle(
        name='TLSection', fontName='Helvetica-Bold', fontSize=11, leading=14,
        textColor=INK, spaceBefore=14, spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        name='TLBody', fontName='Helvetica', fontSize=9.5, leading=14,
        textColor=INK,
    ))
    ss.add(ParagraphStyle(
        name='TLMono', fontName='Courier', fontSize=8, leading=11,
        textColor=MUTED,
    ))
    return ss


def _verdict_color(verdict: str | None):
    if verdict == 'Authentic':
        return VERIFIED
    return FLAG


def generate_report_pdf(video, analysis, output_path: str | Path) -> Path:
    """
    video    : app.models.VideoRecord instance
    analysis : app.models.AnalysisResult instance or None
    Returns the path to the written PDF.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"TrustLens Report — {video.original_filename}",
    )
    styles = _styles()
    story = []

    # --- Header -----------------------------------------------------
    story.append(Paragraph("TrustLens", styles['TLLabel']))
    story.append(Paragraph("Video Authenticity Verification Report", styles['TLTitle']))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=HAIRLINE))
    story.append(Spacer(1, 10))

    case_id = video.id[:8]
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    meta_table = Table(
        [
            ["Case ID", case_id, "Generated", generated],
            ["File name", video.original_filename, "Status", video.status],
        ],
        colWidths=[28 * mm, 62 * mm, 28 * mm, 52 * mm],
    )
    meta_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 8.5),
        ('TEXTCOLOR', (0, 0), (0, -1), MUTED),
        ('TEXTCOLOR', (2, 0), (2, -1), MUTED),
        ('TEXTCOLOR', (1, 0), (1, -1), INK),
        ('TEXTCOLOR', (3, 0), (3, -1), INK),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # --- Verdict summary ---------------------------------------------
    if analysis:
        vcolor = _verdict_color(analysis.verdict)
        auth_score = round(max(0.0, min(100.0, 100.0 - (analysis.fake_probability or 0.0))), 1)
        story.append(Paragraph("Verdict", styles['TLSection']))
        verdict_table = Table(
            [[
                Paragraph(f"<b>{analysis.verdict}</b>", ParagraphStyle(
                    'v', parent=styles['TLBody'], fontSize=16, textColor=vcolor)),
                Paragraph(f"Authenticity score<br/><b>{auth_score}%</b>", styles['TLBody']),
                Paragraph(f"Fake risk<br/><b>{analysis.fake_probability}%</b>", styles['TLBody']),
                Paragraph(f"Confidence<br/><b>{analysis.confidence_label}</b>", styles['TLBody']),
            ]],
            colWidths=[42.5 * mm, 42.5 * mm, 42.5 * mm, 42.5 * mm],
        )
        verdict_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, HAIRLINE),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, HAIRLINE),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(verdict_table)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"Model: {analysis.model_used} — heuristic forensic signal analysis, "
            f"not yet a trained deepfake classifier. Treat this score as a first-pass "
            f"signal rather than a certified determination.",
            ParagraphStyle('note', parent=styles['TLBody'], fontSize=7.5, textColor=MUTED),
        ))

        # --- Reasons ---------------------------------------------------
        story.append(Paragraph("Why this verdict", styles['TLSection']))
        for reason in (analysis.reasons or []):
            story.append(Paragraph(f"•  {reason}", styles['TLBody']))
        story.append(Spacer(1, 6))

        # --- Timeline ----------------------------------------------------
        if analysis.timeline_segments:
            story.append(Paragraph("Suspicious timeline", styles['TLSection']))
            rows = [["Start", "End", "Status", "Notes"]]
            for seg in analysis.timeline_segments:
                rows.append([
                    f"{seg['start']}s", f"{seg['end']}s",
                    seg['status'].capitalize(), seg['reason'],
                ])
            tl_table = Table(rows, colWidths=[18 * mm, 18 * mm, 24 * mm, 110 * mm])
            style_cmds = [
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
                ('LINEBELOW', (0, 0), (-1, 0), 0.75, HAIRLINE),
                ('LINEBELOW', (0, 1), (-1, -2), 0.25, HAIRLINE),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
            for i, seg in enumerate(analysis.timeline_segments, start=1):
                if seg['status'] == 'suspicious':
                    style_cmds.append(('TEXTCOLOR', (2, i), (2, i), FLAG))
                else:
                    style_cmds.append(('TEXTCOLOR', (2, i), (2, i), VERIFIED))
            tl_table.setStyle(TableStyle(style_cmds))
            story.append(tl_table)
            story.append(Spacer(1, 6))

        # --- Raw forensic signals ----------------------------------------
        story.append(Paragraph("Raw forensic signals", styles['TLSection']))
        signals = analysis.forensic_signals or {}
        for key in ('frame_diff_mean', 'blur_variance_median', 'compression_artifact_score'):
            if key in signals and signals[key] is not None:
                story.append(Paragraph(
                    f"{key.replace('_', ' ')}: <font face='Courier'>{signals[key]:.4f}</font>",
                    styles['TLBody'],
                ))
        brightness = signals.get('brightness') or {}
        if brightness:
            story.append(Paragraph(
                f"brightness mean: <font face='Courier'>{brightness.get('mean', 0):.2f}</font>, "
                f"coefficient of variation: "
                f"<font face='Courier'>{brightness.get('coefficient_of_variation', 0):.4f}</font>",
                styles['TLBody'],
            ))
    else:
        story.append(Paragraph(
            "This video has not been analyzed yet — no verdict available.",
            styles['TLBody'],
        ))

    # --- Video metadata ------------------------------------------------
    story.append(Paragraph("Video metadata", styles['TLSection']))
    meta_rows = [
        ["Duration", f"{video.duration_sec:.2f}s" if video.duration_sec else "—"],
        ["Frame rate", f"{video.fps} fps" if video.fps else "—"],
        ["Resolution", f"{video.width}×{video.height}" if video.width else "—"],
        ["Codec", video.codec or "—"],
        ["Bitrate", f"{round(video.bitrate / 1000)} kbps" if video.bitrate else "—"],
        ["Frame count", str(video.frame_count) if video.frame_count else "—"],
        ["File size", f"{video.size_bytes / (1024 * 1024):.2f} MB"],
    ]
    meta_grid = Table(meta_rows, colWidths=[40 * mm, 130 * mm])
    meta_grid.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica', 8.5),
        ('FONT', (1, 0), (1, -1), 'Courier', 8.5),
        ('TEXTCOLOR', (0, 0), (0, -1), MUTED),
        ('LINEBELOW', (0, 0), (-1, -2), 0.25, HAIRLINE),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_grid)

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HAIRLINE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Generated by TrustLens — automated forensic analysis based on classical signal "
        "processing. This report is a first-pass technical signal and does not constitute "
        "legal or journalistic verification on its own.",
        ParagraphStyle('footer', parent=styles['TLBody'], fontSize=7, textColor=MUTED),
    ))

    doc.build(story)
    return output_path
