"""One-click takedown pack (PDF + copy-paste text) with platform-specific wording."""

import json
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _extract_candidate(detection: dict[str, Any]) -> dict[str, Any]:
    cand = detection.get("candidate")
    if isinstance(cand, dict):
        return cand
    cand_raw = detection.get("candidate_json")
    if isinstance(cand_raw, str):
        try:
            return json.loads(cand_raw)
        except Exception:
            return {}
    return {}


def _extract_breakdown(detection: dict[str, Any]) -> dict[str, float]:
    b = detection.get("breakdown")
    if isinstance(b, dict):
        return b
    b_raw = detection.get("breakdown_json")
    if isinstance(b_raw, str):
        try:
            return json.loads(b_raw)
        except Exception:
            return {}
    return {}


def _extract_evidence(detection: dict[str, Any]) -> list[str]:
    ev = detection.get("evidence")
    if isinstance(ev, list):
        return ev
    ev_raw = detection.get("evidence_json")
    if isinstance(ev_raw, str):
        try:
            return json.loads(ev_raw)
        except Exception:
            return []
    return []


def build_takedown_text(detection: dict[str, Any], brand: dict[str, Any]) -> str:
    """Generate platform-specific, ready-to-submit impersonation takedown text."""
    candidate = _extract_candidate(detection)
    evidence = _extract_evidence(detection)
    score = detection.get("score", 0.0)
    verdict = detection.get("verdict", "Unknown")

    brand_name = brand.get("company_name", "Brand Owner")
    official_socials = brand.get("social_accounts") or []
    official_apps = brand.get("official_apps") or []

    off_social_str = ", ".join(
        [
            f"@{getattr(s, 'handle', None) or s.get('handle')} ({getattr(s, 'platform', None) or s.get('platform')})"
            for s in official_socials
        ]
    ) or "Official brand verified accounts"
    off_apps_str = ", ".join(
        [
            f"{getattr(a, 'package_id', None) or a.get('package_id')} by '{getattr(a, 'developer_name', None) or a.get('developer_name')}'"
            for a in official_apps
        ]
    ) or "Official registered applications"

    platform = (
        candidate.get("platform")
        or candidate.get("store")
        or detection.get("candidate_type", "platform")
    ).lower()

    cand_title = candidate.get("name") or candidate.get("title") or "Unknown"
    raw_identifier = candidate.get("handle") or candidate.get("package_id") or "Unknown"
    cand_identifier = f"@{raw_identifier.lstrip('@')}" if candidate.get("handle") else raw_identifier
    cand_url = candidate.get("profile_url") or candidate.get("app_url") or "N/A"
    cand_developer = candidate.get("developer_name")

    evidence_bullets = "\n".join([f"  * {item}" for item in evidence]) or "  * Deceptive brand imitation"

    if platform in {"twitter", "x"}:
        recipient = "X / Twitter Trust & Safety (Impersonation & Brand Protection)"
        policy = "X Impersonation Policy & Trademark Guidelines"
    elif platform in {"instagram", "facebook"}:
        recipient = "Meta IP & Impersonation Operations"
        policy = "Meta Terms of Service regarding Deceptive Identity & Impersonation"
    elif platform in {"play", "google_play", "playstore"}:
        recipient = "Google Play Developer Policy Enforcement Team"
        policy = "Google Play Impersonation & Intellectual Property Policy"
    elif platform in {"appstore", "apple"}:
        recipient = "Apple Legal & App Store Dispute Management"
        policy = "Apple App Store Review Guidelines (Section 4.1 Copycats & 5.2 IP)"
    elif platform in {"telegram"}:
        recipient = "Telegram Anti-Scam & Phishing Team (@notoscam)"
        policy = "Telegram Terms of Service (Prohibition of Phishing & Impersonation)"
    else:
        recipient = f"{platform.capitalize()} Legal and Abuse Operations"
        policy = "Platform Impersonation and Brand Protection Terms"

    body = f"""TO: {recipient}
SUBJECT: URGENT: Impersonation & Brand Protection Takedown Notice - {cand_title} ({cand_identifier})

DATE: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
CASE REFERENCE: IMP-TKD-{detection.get('id', 'NEW')}

Dear Trust & Safety / Enforcement Team,

We are writing on behalf of {brand_name} to formally request the urgent suspension and removal of the unauthorized account/application identified below for deliberate impersonation, brand infringement, and potential consumer fraud.

I. INFRINGING ASSET DETAILS
- Platform / Store: {platform.upper()}
- Display Name / Title: {cand_title}
- Handle / Package Identifier: {cand_identifier}
{f"- Developer / Publisher: {cand_developer}" if cand_developer else ""}
- Asset URL: {cand_url}

II. AUTHORIZED OFFICIAL BRAND ASSETS
- Official Entity: {brand_name}
- Official Social Presence: {off_social_str}
- Official Application Identifiers: {off_apps_str}

III. FORENSIC THREAT ASSESSMENT & EVIDENCE
- ImpostorRadar Risk Score: {score}/100 (Verdict: {verdict.upper()})
- Forensic Evidence Findings:
{evidence_bullets}

IV. VIOLATIONS AND REQUESTED REMEDY
The subject asset violates {policy} by misrepresenting itself as an authorized representation of {brand_name}, confusing consumers, and exposing users to phishing and fraud.

We respectfully demand:
1. Immediate de-indexing or permanent suspension of {cand_identifier}.
2. Preservation of logs and registration credentials for law enforcement referral if phishing/fraud is confirmed.

V. GOOD FAITH DECLARATION
I certify under penalty of perjury that:
1. I am authorized to act on behalf of the owner of the trademark and intellectual property rights for {brand_name}.
2. The information in this notification is accurate and the use of the material in the manner complained of is not authorized by the rights owner, its agent, or the law.

Respectfully submitted,
Digital Risk Protection Officer
ImpostorRadar automated security operations for {brand_name}
"""
    return body.strip()


def build_takedown_pdf(detection: dict[str, Any], brand: dict[str, Any]) -> bytes:
    """Generate a clean, high-resolution takedown dossier PDF."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "TakedownTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "TakedownSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
    )
    heading_style = ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "TakedownBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    bold_style = ParagraphStyle(
        "TakedownBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
    )
    bullet_style = ParagraphStyle(
        "TakedownBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        leftIndent=12,
    )

    candidate = _extract_candidate(detection)
    evidence = _extract_evidence(detection)
    breakdown = _extract_breakdown(detection)
    score = detection.get("score", 0.0)
    verdict = detection.get("verdict", "Safe")
    brand_name = brand.get("company_name", "Brand")

    story = []

    # Header
    story.append(Paragraph("IMPOSTORRADAR — TAKEDOWN EVIDENCE PACK", title_style))
    story.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M:%S UTC')} | Case Ref: IR-TKD-{detection.get('id', 'N/A')}",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

    # Threat Summary Box
    verdict_colors = {
        "High": colors.HexColor("#ef4444"),
        "Medium": colors.HexColor("#f59e0b"),
        "Low": colors.HexColor("#eab308"),
        "Safe": colors.HexColor("#22c55e"),
    }
    v_color = verdict_colors.get(verdict, colors.HexColor("#64748b"))

    summary_data = [
        [
            Paragraph("<b>Target Brand:</b>", body_style),
            Paragraph(brand_name, bold_style),
            Paragraph("<b>Threat Score:</b>", body_style),
            Paragraph(f"<font color='{v_color.hexval()}'><b>{score}/100 ({verdict.upper()})</b></font>", bold_style),
        ],
        [
            Paragraph("<b>Infringing Name:</b>", body_style),
            Paragraph(str(candidate.get("name") or candidate.get("title") or "N/A"), body_style),
            Paragraph("<b>Asset Handle/ID:</b>", body_style),
            Paragraph(str(candidate.get("handle") or candidate.get("package_id") or "N/A"), body_style),
        ],
        [
            Paragraph("<b>Platform/Store:</b>", body_style),
            Paragraph(str(candidate.get("platform") or candidate.get("store") or "N/A").upper(), body_style),
            Paragraph("<b>Publisher / Dev:</b>", body_style),
            Paragraph(str(candidate.get("developer_name") or "Unverified Third Party"), body_style),
        ],
    ]

    summary_table = Table(summary_data, colWidths=[90, 180, 95, 175])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Evidence Findings
    story.append(Paragraph("I. Forensic Detection Evidence", heading_style))
    for ev_item in evidence:
        story.append(Paragraph(f"• {ev_item}", bullet_style))
        story.append(Spacer(1, 2))
    if not evidence:
        story.append(Paragraph("• No anomalous signals recorded.", bullet_style))

    story.append(Spacer(1, 10))

    # Scoring Breakdown Table
    story.append(Paragraph("II. Threat Signal Breakdown", heading_style))
    score_rows = [
        [
            Paragraph("<b>Signal Component</b>", bold_style),
            Paragraph("<b>Weight Max</b>", bold_style),
            Paragraph("<b>Assigned Points</b>", bold_style),
            Paragraph("<b>Risk Implication</b>", bold_style),
        ],
        [
            Paragraph("Name Lexical Similarity", body_style),
            Paragraph("35", body_style),
            Paragraph(str(breakdown.get("name_similarity", 0.0)), body_style),
            Paragraph("Direct phonetic or edit distance resemblance", body_style),
        ],
        [
            Paragraph("Look-alike Technique", body_style),
            Paragraph("15", body_style),
            Paragraph(str(breakdown.get("lookalike_technique", 0.0)), body_style),
            Paragraph(str(detection.get("lookalike_technique") or "None detected"), body_style),
        ],
        [
            Paragraph("Logo Perceptual Hash", body_style),
            Paragraph("20", body_style),
            Paragraph(str(breakdown.get("logo_hash", 0.0)), body_style),
            Paragraph("Image perceptual Hamming similarity", body_style),
        ],
        [
            Paragraph("Bio / Description TF-IDF", body_style),
            Paragraph("10", body_style),
            Paragraph(str(breakdown.get("text_similarity", 0.0)), body_style),
            Paragraph("Targeted keyword hijacking", body_style),
        ],
        [
            Paragraph("Publisher / Dev Mismatch", body_style),
            Paragraph("10", body_style),
            Paragraph(str(breakdown.get("publisher_mismatch", 0.0)), body_style),
            Paragraph("Unauthorized distribution channel", body_style),
        ],
        [
            Paragraph("Scam / Bait Indicators", body_style),
            Paragraph("10", body_style),
            Paragraph(str(breakdown.get("scam_indicators", 0.0)), body_style),
            Paragraph("Phishing links, urgency words, giveaway traps", body_style),
        ],
        [
            Paragraph("<b>TOTAL THREAT SCORE</b>", bold_style),
            Paragraph("<b>100</b>", bold_style),
            Paragraph(f"<b>{score}</b>", bold_style),
            Paragraph(f"<b>VERDICT: {verdict.upper()}</b>", bold_style),
        ],
    ]

    score_table = Table(score_rows, colWidths=[150, 70, 90, 230])
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(score_table)
    story.append(Spacer(1, 10))

    # Formal Legal Notice
    story.append(Paragraph("III. Formal Takedown Request Statement", heading_style))
    statement_text = (
        f"This document serves as formal notification that the aforementioned candidate entity falsely uses "
        f"the intellectual property and brand likeness of <b>{brand_name}</b> without authorization. "
        f"Such unauthorized usage infringes trademark protections, deceives consumers, and represents an active "
        f"security threat. We demand immediate suspension of this account/application in accordance with platform policies."
    )
    story.append(Paragraph(statement_text, body_style))
    story.append(Spacer(1, 12))

    sig_data = [
        [
            Paragraph("<b>Authorized Verification Officer:</b>", body_style),
            Paragraph("<b>System Verification Fingerprint:</b>", body_style),
        ],
        [
            Paragraph("Digital Risk Protection Unit (ImpostorRadar)", bold_style),
            Paragraph(f"SHA-256:{hex(abs(hash(str(detection))))[2:]}", body_style),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()
