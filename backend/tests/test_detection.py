"""Comprehensive pytest tests for ImpostorRadar detection engine and takedown pack."""

import pytest
from app.services.lookalike import detect_technique, generate_variants, is_innocent_compound
from app.services.normalize import normalize_handle, normalize_name
from app.services.scoring import is_official_asset, score_candidate
from app.services.takedown import build_takedown_pdf, build_takedown_text


@pytest.fixture
def sample_brand():
    return {
        "company_name": "Paytm",
        "logo_path": "backend/uploads/paytm_official.png",
        "keywords": ["wallet", "payments", "upi", "soundbox", "recharge"],
        "social_accounts": [
            {"platform": "twitter", "handle": "paytm"},
            {"platform": "instagram", "handle": "paytm"},
            {"platform": "youtube", "handle": "paytm"},
        ],
        "official_apps": [
            {
                "store": "play",
                "package_id": "net.one97.paytm",
                "developer_name": "One97 Communications Ltd.",
            },
            {
                "store": "appstore",
                "package_id": "id473941634",
                "developer_name": "One97 Communications",
            },
        ],
    }


def test_official_social_never_flagged(sample_brand):
    """Rule 4: Official assets must NEVER be flagged (allowlist exclusion BEFORE scoring)."""
    official_cand = {
        "platform": "twitter",
        "name": "Paytm",
        "handle": "paytm",
        "bio": "Official Twitter handle of Paytm. #PaytmKaro",
    }
    is_off, reason = is_official_asset(sample_brand, official_cand)
    assert is_off is True
    assert "paytm" in reason

    scored = score_candidate(sample_brand, official_cand)
    assert scored["score"] == 0.0
    assert scored["verdict"] == "Safe"
    assert scored["is_official"] is True


def test_official_app_never_flagged(sample_brand):
    """Rule 4: Official apps excluded by package id and developer allowlist."""
    official_app = {
        "store": "play",
        "title": "Paytm: Secure UPI Payments",
        "package_id": "net.one97.paytm",
        "developer_name": "One97 Communications Ltd.",
        "description": "India's payments app.",
    }
    is_off, reason = is_official_asset(sample_brand, official_app)
    assert is_off is True

    scored = score_candidate(sample_brand, official_app)
    assert scored["score"] == 0.0
    assert scored["verdict"] == "Safe"
    assert scored["is_official"] is True


def test_lookalike_swap_detected():
    """Rule 5: Character swaps / typos must be detected."""
    tech = detect_technique("Paytm", "Paytn")
    assert tech == "swap"

    tech_transposition = detect_technique("Paytm", "Pyatm")
    assert tech_transposition == "swap"


def test_lookalike_spacing_and_punctuation_detected():
    """Rule 5: Spacing and punctuation tricks detected."""
    assert detect_technique("Paytm", "Pay tm") == "spacing"
    assert detect_technique("Paytm", "Pay.tm") == "punctuation"
    assert detect_technique("Paytm", "Pay_tm") == "punctuation"


def test_lookalike_homoglyph_detected():
    """Rule 5: Homoglyph Cyrillic confusable characters detected."""
    # Cyrillic 'а' (U+0430)
    assert detect_technique("Paytm", "p\u0430ytm") == "homoglyph"


def test_lookalike_leetspeak_detected():
    """Rule 5: Leetspeak numbers substituted for letters."""
    assert detect_technique("Paytm", "paytm_0fficial") == "leetspeak"


def test_lookalike_added_words_detected():
    """Rule 5: Added bait words (official, support, care, rewards, login, helpdesk)."""
    assert detect_technique("Paytm", "Paytm Official") == "added-word"
    assert detect_technique("Paytm", "Paytm Customer Support Care") == "added-word"
    assert detect_technique("Paytm", "Paytm Rewards Club") == "added-word"
    assert detect_technique("Paytm", "Paytm Urgent KYC Helpline") == "added-word"


def test_innocent_compounds_not_overflagged(sample_brand):
    """Rule 5: Avoid over-flagging normal names (e.g. Paytm Valley Farms)."""
    assert is_innocent_compound("Paytm", "Paytm Valley Farms") is True
    assert detect_technique("Paytm", "Paytm Valley Farms") is None

    candidate = {
        "platform": "instagram",
        "name": "Paytm Valley Farms",
        "handle": "paytm_valley_farms",
        "bio": "Fresh organic farm vegetables and apples from Himachal.",
        "avatar_url": "backend/uploads/neutral_farm.png",
        "followers_count": 5200,
        "is_verified": False,
    }
    scored = score_candidate(sample_brand, candidate)
    assert scored["verdict"] == "Safe"
    assert scored["score"] < 30.0


def test_app_detection_uses_name_logo_publisher_description(sample_brand):
    """Checklist: App detection uses name + logo + publisher + description."""
    fake_app = {
        "store": "play",
        "title": "Paytn Fast Wallet & Cashback",
        "package_id": "com.paytn.wallet.rewards",
        "developer_name": "FastTech Solutions",
        "description": "Instant loan, UPI payments, wallet rewards and cashback. Enter UPI PIN to claim 5000 cashback! Giveaway.",
        "icon_url": "backend/uploads/paytm_clone.png",
    }
    scored = score_candidate(sample_brand, fake_app)
    assert scored["score"] >= 75
    assert scored["verdict"] == "High"
    assert scored["breakdown"]["name_similarity"] > 0
    assert scored["breakdown"]["publisher_mismatch"] == 10.0
    assert scored["breakdown"]["logo_hash"] > 0
    assert scored["breakdown"]["scam_indicators"] > 0
    assert any("Publisher mismatch" in e for e in scored["evidence"])


def test_takedown_pack_outputs(sample_brand):
    """Unique feature: Takedown Pack text and PDF generation."""
    detection = {
        "id": 42,
        "score": 88.0,
        "verdict": "High",
        "candidate_type": "social",
        "candidate": {
            "platform": "twitter",
            "name": "Paytn Official Care",
            "handle": "paytn_care",
            "profile_url": "https://twitter.com/paytn_care",
            "bio": "Official 24x7 customer support. DM us your UPI PIN.",
        },
        "evidence": [
            "Name differs by 1 swapped character: 'Paytm' vs 'Paytn'",
            "Near-identical logo perceptual hash",
            "Unverified profile claiming official support",
        ],
        "breakdown": {
            "name_similarity": 28.0,
            "lookalike_technique": 15.0,
            "logo_hash": 20.0,
            "text_similarity": 5.0,
            "publisher_mismatch": 10.0,
            "scam_indicators": 10.0,
        },
        "lookalike_technique": "swap",
    }

    text = build_takedown_text(detection, sample_brand)
    assert "TO: X / Twitter Trust & Safety" in text
    assert "@paytn_care" in text
    assert "Paytm" in text
    assert "Forensic Evidence Findings" in text

    pdf_bytes = build_takedown_pdf(detection, sample_brand)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_lookalike_variant_generation():
    """Look-alike Lab: Generate variants across all techniques."""
    variants = generate_variants("Paytm")
    assert len(variants) > 10
    techniques = {v["technique"] for v in variants}
    assert "swap" in techniques
    assert "homoglyph" in techniques
    assert "spacing" in techniques
    assert "added-word" in techniques
