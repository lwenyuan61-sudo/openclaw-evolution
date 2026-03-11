"""Prepare a UI avatar image for NaoChao Launcher.

- Downloads a chosen image URL to girl_raw.*
- Resizes to a UI-friendly PNG (girl_ui.png)

Run:
  .venv\\Scripts\\python.exe prepare_avatar.py

If you want a different URL, edit IMAGE_URL.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PIL import Image

BASE = Path(r"C:\Users\15305\.openclaw\workspace\brainflow")

# Real-photo-style fitness woman in sportswear, Wikimedia Commons (CC0)
# NOTE: This is a normal fitness photo (non-explicit) sourced from Wikimedia Commons.
# File page:
# https://commons.wikimedia.org/wiki/File:Hattie_James_Women%27s_fitness_Gym_girl,_Gym_Model,_Fitness_model_15.jpg
IMAGE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/Hattie_James_Women%27s_fitness_Gym_girl,_Gym_Model,_Fitness_model_15.jpg"

RAW_PATH = BASE / "girl_raw.jpg"
UI_PATH = BASE / "girl_ui.png"


def download(url: str, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    # Use curl.exe on Windows
    subprocess.check_call([
        "curl.exe",
        "-L",
        url,
        "-o",
        str(out),
    ])


def resize_to_square(in_path: Path, out_path: Path, size: int = 128):
    img = Image.open(in_path).convert("RGBA")
    w, h = img.size
    # center crop to square
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size), Image.LANCZOS)
    img.save(out_path, format="PNG")


def main():
    if not RAW_PATH.exists():
        print(f"Downloading: {IMAGE_URL}")
        download(IMAGE_URL, RAW_PATH)

    print(f"Resizing -> {UI_PATH}")
    resize_to_square(RAW_PATH, UI_PATH, size=128)
    print("Done.")


if __name__ == "__main__":
    main()
