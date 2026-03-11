"""Append a note to a markdown file inside brainflow/memory.

Safety: only writes under brainflow/memory.
"""

from __future__ import annotations

import os
import time
from typing import Any


def run(filename: str, text: str) -> Any:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    mem_dir = os.path.join(base_dir, "memory")
    os.makedirs(mem_dir, exist_ok=True)

    # basic path safety
    if ".." in filename or filename.startswith("/") or filename.startswith("\\") or ":" in filename:
        raise ValueError("invalid filename")

    path = os.path.join(mem_dir, filename)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n- [{ts}] {text}\n")

    return {"ok": True, "path": path}
