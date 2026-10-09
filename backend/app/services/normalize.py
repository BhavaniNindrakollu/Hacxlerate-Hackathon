import re
import unicodedata

HOMOGLYPHS = {
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "у": "y",
    "х": "x",
    "і": "i",
    "ԁ": "d",
    "ɡ": "g",
    "０": "0",
    "１": "1",
    "@": "a",
    "$": "s",
    "€": "e",
}

LEET = {
    "0": "o",
    "1": "l",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
}


def fold_homoglyphs(text: str) -> str:
    chars: list[str] = []
    for char in text:
        mapped = HOMOGLYPHS.get(char, char)
        chars.append(mapped)
    return "".join(chars)


def apply_leetspeak(text: str) -> str:
    return "".join(LEET.get(char, char) for char in text)


def collapse_confusables(text: str) -> str:
    """rn -> m and similar multi-char tricks after single-char maps."""
    return text.replace("rn", "m").replace("vv", "w")


def strip_noise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text)


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.strip().lower()
    text = fold_homoglyphs(text)
    text = apply_leetspeak(text)
    text = collapse_confusables(text)
    return strip_noise(text)


def normalize_handle(value: str) -> str:
    text = (value or "").strip()
    if text.startswith("@"):
        text = text[1:]
    return normalize_name(text)


def tokenize(value: str) -> list[str]:
    text = unicodedata.normalize("NFKC", value or "").strip().lower()
    text = fold_homoglyphs(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [part for part in text.split() if part]


def display_name(value: str) -> str:
    return (value or "").strip()
