"""ImpostorRadar backend application package."""

from __future__ import annotations

import sys
from pathlib import Path

__version__ = "0.1.0"

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
