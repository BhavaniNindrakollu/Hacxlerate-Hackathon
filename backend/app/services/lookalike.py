from pathlib import Path

from rapidfuzz.distance import DamerauLevenshtein

from app.config import get_settings
from app.services.normalize import normalize_name, tokenize

BAIT_WORDS = {
    "official",
    "support",
    "care",
    "rewards",
    "login",
    "helpdesk",
    "india",
    "verify",
    "kyc",
    "customer",
    "helpline",
    "bonus",
    "giveaway",
    "claim",
    "refund",
    "dispute",
    "cashback",
    "alert",
    "desk",
    "portal",
    "bank",
    "wallet",
}

MIN_BRAND_LEN = 3


def load_common_words() -> set[str]:
    path = get_settings().data_path / "common_words.txt"
    if not path.exists():
        return set()
    return {line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _common() -> set[str]:
    return load_common_words() | {
        "the",
        "and",
        "for",
        "app",
        "inc",
        "ltd",
        "llc",
        "news",
        "tv",
        "radio",
        "music",
        "coffee",
        "travel",
        "food",
        "score",
        "live",
        "hub",
        "team",
        "page",
        "store",
        "wallet",
        "pay",
        "time",
    }


def is_innocent_compound(brand: str, candidate: str) -> bool:
    """True when brand is a token plus generic words (e.g. Paytm Valley Farms)."""
    brand_tokens = tokenize(brand)
    cand_tokens = tokenize(candidate)
    if not brand_tokens or not cand_tokens:
        return False
    brand_core = brand_tokens[0]
    if brand_core not in cand_tokens:
        return False
    extras = [tok for tok in cand_tokens if tok != brand_core]
    if not extras:
        return False
    common = _common()
    bait_hits = [tok for tok in extras if tok in BAIT_WORDS]
    generic_hits = [tok for tok in extras if tok in common and tok not in BAIT_WORDS]
    return bool(generic_hits) and not bait_hits


def detect_technique(brand_name: str, candidate_name: str) -> str | None:
    if not brand_name or not candidate_name:
        return None
    if len(brand_name.strip()) < MIN_BRAND_LEN:
        return None
    if is_innocent_compound(brand_name, candidate_name):
        return None

    brand_n = normalize_name(brand_name)
    cand_n = normalize_name(candidate_name)
    if not brand_n or not cand_n:
        return None

    raw_brand = brand_name.strip()
    raw_cand = candidate_name.strip()
    brand_tokens = tokenize(brand_name)
    cand_tokens = tokenize(candidate_name)

    # Check for homoglyphs (Cyrillic or special confusables)
    has_homoglyph_char = any(
        ord(ch) > 127 and ch in "аеорсухіԁɡ０１@$€" for ch in raw_cand
    )
    if has_homoglyph_char and (brand_n in cand_n or cand_n in brand_n):
        return "homoglyph"

    # Check for leetspeak substitution (e.g. 0 for o, 1 for i/l, rn for m)
    if ("rn" in raw_cand.lower() and "m" in raw_brand.lower()) or any(
        d in raw_cand for d in "013457"
    ):
        if brand_n in cand_n or any(tok in BAIT_WORDS for tok in cand_tokens):
            return "leetspeak"

    # Check token-level lookalikes
    for tok in cand_tokens:
        tok_n = normalize_name(tok)
        if tok_n == brand_n and tok.lower() != raw_brand.lower():
            if any(ch in "013457" for ch in tok):
                return "leetspeak"
            return "homoglyph"
        if tok_n != brand_n:
            dist = DamerauLevenshtein.distance(brand_n, tok_n)
            if dist == 1:
                return "swap"
            if dist == 2 and abs(len(brand_n) - len(tok_n)) <= 1:
                return "typo"

    # Spacing and punctuation tricks
    compact_brand = raw_brand.lower().replace(" ", "")
    compact_cand = (
        raw_cand.lower()
        .replace(" ", "")
        .replace(".", "")
        .replace("_", "")
        .replace("-", "")
    )
    if compact_brand == compact_cand and raw_brand.lower() != raw_cand.lower():
        if " " in raw_cand or " " in raw_brand:
            return "spacing"
        if any(ch in raw_cand for ch in ".-_"):
            return "punctuation"

    # Added bait words
    extras = [tok for tok in cand_tokens if tok not in brand_tokens]
    if extras and any(tok in BAIT_WORDS for tok in extras):
        if brand_n in cand_n or any(
            DamerauLevenshtein.distance(brand_n, tok) <= 1 for tok in cand_tokens
        ):
            return "added-word"

    # Handle concatenation (e.g. paytmofficial, paytmcare)
    for bait in BAIT_WORDS:
        if cand_n.startswith(brand_n + bait) or cand_n.endswith(bait + brand_n):
            return "added-word"

    # Homoglyph direct match
    if brand_n == cand_n and raw_brand.lower() != raw_cand.lower():
        return "homoglyph"

    # Overall Levenshtein distance
    distance = DamerauLevenshtein.distance(brand_n, cand_n)
    if distance == 1:
        return "swap"
    if distance == 2 and abs(len(brand_n) - len(cand_n)) <= 1:
        return "typo"

    return None


def generate_variants(name: str) -> list[dict[str, str]]:
    name = name.strip()
    if len(name) < 2:
        return []
    variants: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(variant: str, technique: str) -> None:
        key = variant.strip()
        if not key or key.lower() == name.lower() or key.lower() in seen:
            return
        seen.add(key.lower())
        variants.append({"variant": key, "technique": technique})

    letters = list(name)
    # Character swaps
    for i in range(len(letters) - 1):
        swapped = letters.copy()
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        add("".join(swapped), "swap")

    # End character swap / single typo
    if len(letters) >= 3:
        var1 = list(letters)
        var1[-1] = "n" if var1[-1].lower() != "n" else "m"
        add("".join(var1), "swap")

        var2 = list(letters)
        var2[0] = "b" if var2[0].lower() != "b" else "p"
        add("".join(var2), "swap")

    # Homoglyphs
    homoglyph_pairs = [("a", "а"), ("e", "е"), ("o", "о"), ("p", "р"), ("c", "с")]
    lower = name.lower()
    for latin, cyr in homoglyph_pairs:
        if latin in lower:
            add("".join(cyr if ch.lower() == latin else ch for ch in name), "homoglyph")
            break

    # Leetspeak
    if "o" in lower:
        add(name.replace("o", "0").replace("O", "0"), "leetspeak")
    if "l" in lower or "i" in lower:
        add(
            name.replace("l", "1")
            .replace("i", "1")
            .replace("L", "1")
            .replace("I", "1"),
            "leetspeak",
        )
    if "m" in lower:
        add(name.replace("m", "rn").replace("M", "rn"), "leetspeak")

    # Spacing and punctuation
    if len(name) >= 4:
        mid = len(name) // 2
        add(f"{name[:mid]} {name[mid:]}", "spacing")
        add(f"{name[:mid]}.{name[mid:]}", "punctuation")
        add(f"{name}_{name[-2:]}", "punctuation")
        add(f"{name}.official", "punctuation")

    # Added words
    for word in (
        "Official",
        "Support",
        "Care",
        "Rewards",
        "Login",
        "Helpdesk",
        "India",
        "KYC",
        "Helpline",
    ):
        add(f"{name} {word}", "added-word")
        add(f"{word} {name}", "added-word")
        add(f"{name}_{word.lower()}", "added-word")

    # Typos
    add(name + name[-1], "typo")

    return variants[:50]


def technique_score_unit(technique: str | None, brand: str, candidate: str) -> float:
    if is_innocent_compound(brand, candidate):
        return 0.0
    mapping = {
        "swap": 1.0,
        "homoglyph": 1.0,
        "leetspeak": 0.95,
        "spacing": 0.85,
        "punctuation": 0.8,
        "added-word": 0.95,
        "typo": 0.7,
    }
    if not technique:
        return 0.0
    return mapping.get(technique, 0.5)
