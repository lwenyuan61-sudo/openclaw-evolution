"""Read a text file inside brainflow directory.

Safety: restricts reads to the brainflow base dir.
"""

from __future__ import annotations

import os
from typing import Any


def run(rel_path: str, max_chars: int = 8000) -> Any:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    # normalize
    rel_path = rel_path.replace("/", "\\")
    if rel_path.startswith("..") or ":" in rel_path or rel_path.startswith("\\"):
        raise ValueError("invalid path")

    path = os.path.abspath(os.path.join(base_dir, rel_path))
    if not path.startswith(base_dir):
        raise ValueError("path escape")

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()

    if len(data) > int(max_chars):
        data = data[: int(max_chars)] + "\n...[truncated]"

    return {"ok": True, "path": path, "text": data}
