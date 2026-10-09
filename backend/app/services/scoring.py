"""Weighted threat scoring 0–100, verdict bands, and human-readable evidence reasons."""

import re
from datetime import datetime, timezone
from typing import Any

from rapidfuzz import fuzz

from app.services.imagesim import logo_score_unit, phash_distance
from app.services.lookalike import detect_technique, is_innocent_compound, technique_score_unit
from app.services.normalize import normalize_handle, normalize_name
from app.services.textsim import cosine_vs_keywords

WEIGHTS = {
    "name_similarity": 35,
    "lookalike_technique": 15,
    "logo_hash": 20,
    "text_similarity": 10,
    "publisher_mismatch": 10,
    "scam_indicators": 10,
}

SCAM_TRIGGERS = [
    "dm to claim",
    "dm us",
    "giveaway",
    "lottery",
    "cashback",
    "claim bonus",
    "claim reward",
    "pending refund",
    "urgent kyc",
    "wallet freeze",
    "unblock",
    "send otp",
    "enter upi pin",
    "instant loan",
    "whatsapp call",
    "bit.ly",
    "tinyurl",
    "scratch card",
    "free money",
    "100% cashback",
]


def verdict_for_score(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Medium"
    if score >= 30:
        return "Low"
    return "Safe"


def is_official_asset(brand: dict[str, Any], candidate: dict[str, Any]) -> tuple[bool, str]:
    """Check if candidate matches brand allowlist before scoring."""
    social_accounts = brand.get("social_accounts") or []
    official_apps = brand.get("official_apps") or []

    # Check social
    cand_platform = (candidate.get("platform") or "").strip().lower()
    if cand_platform == "x":
        cand_platform = "twitter"
    cand_handle = (candidate.get("handle") or "").strip().lstrip("@").lower()

    if cand_handle:
        for official in social_accounts:
            off_plat = (
                getattr(official, "platform", None) or (official.get("platform") if isinstance(official, dict) else "")
            ).strip().lower()
            if off_plat == "x":
                off_plat = "twitter"
            off_handle = (
                getattr(official, "handle", None) or (official.get("handle") if isinstance(official, dict) else "")
            ).strip().lstrip("@").lower()

            if off_handle and cand_handle == off_handle and (not off_plat or cand_platform == off_plat):
                return True, f"Official verified handle @{cand_handle} on {cand_platform}"

    # Check apps
    cand_pkg = (candidate.get("package_id") or "").strip().lower()
    cand_dev = (candidate.get("developer_name") or "").strip().lower()
    cand_store = (candidate.get("store") or "").strip().lower()

    if cand_pkg or cand_dev:
        for official in official_apps:
            off_pkg = (
                getattr(official, "package_id", None) or (official.get("package_id") if isinstance(official, dict) else "")
            ).strip().lower()
            off_dev = (
                getattr(official, "developer_name", None)
                or (official.get("developer_name") if isinstance(official, dict) else "")
            ).strip().lower()
            off_store = (
                getattr(official, "store", None) or (official.get("store") if isinstance(official, dict) else "")
            ).strip().lower()

            if off_pkg and cand_pkg == off_pkg:
                return True, f"Official verified package ID '{cand_pkg}'"
            if off_dev and cand_dev == off_dev and (not off_store or cand_store == off_store):
                return True, f"Official verified developer '{cand_dev}'"

    return False, ""


def score_candidate(brand: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Calculate 0-100 score, evidence reasons, breakdown, and verdict."""
    brand_name = (brand.get("company_name") or "").strip()
    brand_norm = normalize_name(brand_name)
    brand_keywords = brand.get("keywords") or []
    if isinstance(brand_keywords, str):
        brand_keywords = [k.strip() for k in brand_keywords.split(",") if k.strip()]

    # 1. Official Asset Exclusion (BEFORE SCORING)
    is_official, official_reason = is_official_asset(brand, candidate)
    if is_official:
        return {
            "score": 0.0,
            "verdict": "Safe",
            "is_official": True,
            "breakdown": {key: 0.0 for key in WEIGHTS},
            "evidence": [f"Official verified brand asset ({official_reason}) — excluded from threat scoring."],
            "lookalike_technique": None,
        }

    evidence: list[str] = []
    breakdown: dict[str, float] = {key: 0.0 for key in WEIGHTS}

    cand_name = candidate.get("name") or candidate.get("title") or ""
    cand_handle = candidate.get("handle") or candidate.get("package_id") or ""
    cand_text = candidate.get("bio") or candidate.get("description") or ""

    innocent = is_innocent_compound(brand_name, cand_name)

    # 2. Name Similarity (35 points)
    if innocent:
        # Common word compound without bait words (e.g. Paytm Valley Farms)
        breakdown["name_similarity"] = 2.0
    else:
        norm_cand_name = normalize_name(cand_name)
        norm_cand_handle = normalize_handle(cand_handle)

        ratio_name = fuzz.ratio(brand_norm, norm_cand_name) if norm_cand_name else 0.0
        ratio_handle = fuzz.ratio(brand_norm, norm_cand_handle) if norm_cand_handle else 0.0
        partial_name = fuzz.partial_ratio(brand_norm, norm_cand_name) if norm_cand_name else 0.0

        best_ratio = max(ratio_name, ratio_handle, partial_name * 0.9)

        if brand_norm and (brand_norm in norm_cand_name or brand_norm in norm_cand_handle):
            best_ratio = max(best_ratio, 92.0)

        unit_name = min(1.0, max(0.0, best_ratio / 100.0))
        breakdown["name_similarity"] = round(unit_name * WEIGHTS["name_similarity"], 1)

        if best_ratio >= 70:
            evidence.append(
                f"High name lexical similarity ({best_ratio:.0f}%) to brand '{brand_name}' on candidate '{cand_name or cand_handle}'"
            )
        elif best_ratio >= 45:
            evidence.append(
                f"Moderate lexical resemblance ({best_ratio:.0f}%) to brand '{brand_name}'"
            )

    # 3. Look-alike Technique (15 points)
    technique = None
    if not innocent:
        technique = detect_technique(brand_name, cand_name) or detect_technique(brand_name, cand_handle)
        if technique:
            unit_tech = technique_score_unit(technique, brand_name, cand_name)
            breakdown["lookalike_technique"] = round(unit_tech * WEIGHTS["lookalike_technique"], 1)

            tech_descriptions = {
                "swap": f"Character transposition / swap identified ('{brand_name}' vs '{cand_name or cand_handle}')",
                "homoglyph": "Cyrillic or visual confusable characters (homoglyph attack) detected",
                "leetspeak": "Leetspeak / number-letter substitution detected (e.g., 0 for o, 1 for i, rn for m)",
                "spacing": "Manipulated whitespace used to bypass keyword filters",
                "punctuation": "Punctuation delimiters inserted (e.g., dots or underscores)",
                "added-word": "High-risk bait keyword appended (e.g., official, support, care, rewards, kyc)",
                "typo": "Typo squatting pattern detected (edit distance within threshold)",
            }
            evidence.append(
                f"Look-alike technique [{technique}]: {tech_descriptions.get(technique, 'Suspicious spelling variation')}"
            )

    # 4. Logo Perceptual Hash (20 points)
    brand_logo = brand.get("logo_path")
    cand_logo = candidate.get("avatar_url") or candidate.get("icon_url")
    if brand_logo and cand_logo:
        dist = phash_distance(brand_logo, cand_logo)
        if dist is not None:
            unit_logo = logo_score_unit(dist)
            breakdown["logo_hash"] = round(unit_logo * WEIGHTS["logo_hash"], 1)
            if dist <= 3:
                evidence.append(
                    f"Perceptual logo hash distance {dist}/64: Near-identical clone of official logo"
                )
            elif dist <= 12:
                evidence.append(
                    f"Perceptual logo hash distance {dist}/64: Deceptive visual similarity to brand logo"
                )

    # 5. Text / Bio Similarity (10 points)
    if cand_text:
        corpus = brand_keywords + [brand_name]
        sim_cos = cosine_vs_keywords(cand_text, corpus)
        unit_text = min(1.0, max(0.0, sim_cos * 1.4))
        breakdown["text_similarity"] = round(unit_text * WEIGHTS["text_similarity"], 1)
        if sim_cos >= 0.25:
            evidence.append(
                f"Bio / description contains significant brand-relevant terminology (TF-IDF similarity: {sim_cos:.2f})"
            )

    # 6. Publisher / Verification Mismatch (10 points)
    cand_dev = candidate.get("developer_name")
    if cand_dev:  # App candidate
        official_apps = brand.get("official_apps") or []
        off_devs = [
            (getattr(a, "developer_name", "") or a.get("developer_name", "")).strip().lower()
            for a in official_apps
            if getattr(a, "developer_name", None) or (isinstance(a, dict) and a.get("developer_name"))
        ]
        if off_devs and cand_dev.strip().lower() not in off_devs:
            if breakdown["name_similarity"] >= 15.0 or technique:
                breakdown["publisher_mismatch"] = float(WEIGHTS["publisher_mismatch"])
                evidence.append(
                    f"Publisher mismatch: Developed by unverified entity '{cand_dev}' instead of official publisher"
                )
    else:  # Social candidate
        cand_bio_lower = cand_text.lower()
        claims_authority = any(
            word in cand_bio_lower for word in ["official", "support", "care", "helpline", "authorized", "dispute"]
        )
        is_verified = bool(candidate.get("is_verified"))
        if claims_authority and not is_verified:
            breakdown["publisher_mismatch"] = float(WEIGHTS["publisher_mismatch"])
            evidence.append("Unverified profile claiming official customer support or helpline authority")

    # 7. Scam Indicators (10 points)
    text_to_check = f"{cand_name} {cand_handle} {cand_text}".lower()
    links_to_check = " ".join(candidate.get("links") or []).lower()
    full_haystack = f"{text_to_check} {links_to_check}"

    scam_hits = [trig for trig in SCAM_TRIGGERS if trig in full_haystack]

    followers = candidate.get("followers_count")
    is_low_follower_claim = (
        followers is not None and followers < 150 and any(w in text_to_check for w in ["support", "care", "helpline", "bonus", "claim"])
    )

    created_at_str = candidate.get("created_at")
    is_very_new = False
    if created_at_str:
        try:
            dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - dt).days
            if age_days <= 30 and (scam_hits or technique):
                is_very_new = True
        except Exception:
            pass

    scam_score_val = min(10.0, len(scam_hits) * 3.5 + (3.0 if is_low_follower_claim else 0.0) + (2.5 if is_very_new else 0.0))
    breakdown["scam_indicators"] = round(scam_score_val, 1)

    if scam_hits:
        evidence.append(f"Scam phrases / deceptive bait detected: {', '.join(scam_hits[:3])}")
    if is_low_follower_claim:
        evidence.append(f"Suspicious account metrics: Low follower count ({followers}) claiming official role or offering funds")
    if is_very_new:
        evidence.append("Recently created profile mimicking established brand")

    # Final tally
    total_score = min(100.0, max(0.0, round(sum(breakdown.values()), 1)))
    verdict = verdict_for_score(total_score)

    if not evidence and verdict == "Safe":
        evidence.append("No impersonation or deceptive signals detected.")

    return {
        "score": total_score,
        "verdict": verdict,
        "is_official": False,
        "breakdown": breakdown,
        "evidence": evidence,
        "lookalike_technique": technique,
    }
