import re


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _cosine_counts(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    vocab = set(left) | set(right)
    a = [left.count(word) for word in vocab]
    b = [right.count(word) for word in vocab]
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if not norm_a or not norm_b:
        return 0.0
    return float(dot / (norm_a * norm_b))


def cosine_vs_keywords(text: str, keywords: list[str]) -> float:
    corpus_keywords = " ".join(keywords)
    if not text.strip() or not corpus_keywords.strip():
        return 0.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer()
        matrix = vectorizer.fit_transform([corpus_keywords, text])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0, 0])
    except Exception:  # noqa: BLE001 — sklearn optional at runtime
        return _cosine_counts(_tokens(corpus_keywords), _tokens(text))
