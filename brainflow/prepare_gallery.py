"""Prepare a small gallery of UI images for the launcher.

Downloads a few Wikimedia Commons fitness photos (non-explicit) and resizes them
so they don't cover UI controls.

Run:
  .venv\\Scripts\\python.exe prepare_gallery.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

BASE = Path(r"C:\Users\15305\.openclaw\workspace\brainflow")
GDIR = BASE / "ui_gallery"
GDIR.mkdir(parents=True, exist_ok=True)

URLS = [
    # Existing choice (CC0)
    "https://commons.wikimedia.org/wiki/Special:FilePath/Hattie_James_Women%27s_fitness_Gym_girl,_Gym_Model,_Fitness_model_15.jpg",
    # Try nearby files (may or may not exist; script will skip failures)
    "https://commons.wikimedia.org/wiki/Special:FilePath/Hattie_James_Women%27s_fitness_Gym_girl,_Gym_Model,_Fitness_model_14.jpg",
    "https://commons.wikimedia.org/wiki/Special:FilePath/Hattie_James_Women%27s_fitness_Gym_girl,_Gym_Model,_Fitness_model_16.jpg",
]


def download(url: str, out: Path) -> bool:
    try:
        subprocess.check_call(["curl.exe", "-L", url, "-o", str(out)])
        return True
    except Exception:
        return False


def make_thumb(in_path: Path, out_path: Path, size: int = 96):
    img = Image.open(in_path).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size), Image.LANCZOS)
    img.save(out_path, format="PNG")


def main():
    thumbs = []
    for i, url in enumerate(URLS, start=1):
        raw = GDIR / f"img{i}.jpg"
        if not raw.exists():
            ok = download(url, raw)
            if not ok:
                continue
        thumb = GDIR / f"img{i}.png"
        make_thumb(raw, thumb, size=96)
        thumbs.append(str(thumb))

    index = GDIR / "index.txt"
    index.write_text("\n".join(thumbs) + "\n", encoding="utf-8")
    print(f"Prepared {len(thumbs)} thumbnails.")


if __name__ == "__main__":
    main()
