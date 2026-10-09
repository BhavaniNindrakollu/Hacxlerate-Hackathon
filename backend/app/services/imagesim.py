from pathlib import Path
from PIL import Image

try:
    import imagehash
except ImportError:  # pragma: no cover
    imagehash = None


def _resolve_image_path(path: str | Path | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    if p.exists() and p.is_file():
        return p

    cleaned = str(path).replace("\\", "/").strip().lstrip("/")
    if cleaned.startswith("uploads/"):
        sub = cleaned[len("uploads/") :]
    else:
        sub = Path(cleaned).name

    candidates = [
        Path("backend/uploads") / sub,
        Path("uploads") / sub,
        Path("backend/app/uploads") / sub,
        Path(".") / sub,
    ]
    for cand in candidates:
        if cand.exists() and cand.is_file():
            return cand
    return None


def phash_distance(path_a: str | Path | None, path_b: str | Path | None) -> int | None:
    if not path_a or not path_b or imagehash is None:
        return None
    file_a = _resolve_image_path(path_a)
    file_b = _resolve_image_path(path_b)
    if not file_a or not file_b:
        return None
    try:
        hash_a = imagehash.phash(Image.open(file_a).convert("RGB"))
        hash_b = imagehash.phash(Image.open(file_b).convert("RGB"))
        return int(hash_a - hash_b)
    except Exception:  # noqa: BLE001
        return None


def logo_score_unit(distance: int | None) -> float:
    """Map Hamming distance to 0–1. Identical logos → 1, far logos → 0."""
    if distance is None:
        return 0.0
    # 64-bit pHash; distance 0–6 is visually very close.
    if distance <= 2:
        return 1.0
    if distance <= 8:
        return 0.75
    if distance <= 14:
        return 0.4
    if distance <= 22:
        return 0.15
    return 0.0
