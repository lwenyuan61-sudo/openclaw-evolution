"""NaoChao Launcher (Windows)

GUI with three buttons:
- Start OpenClaw Gateway
- Open Dashboard
- Start NaoChao (BrainFlow daemon)

Notes:
- Uses openclaw.cmd and the existing start scripts.
- Embeds a small stylized avatar image (non-real person) for decoration.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk

BASE = r"C:\Users\15305\.openclaw\workspace\brainflow"
DASHBOARD_URL = "http://127.0.0.1:18789/"


def _run_detached(cmd, cwd=None):
    """Run a command in a new console window (Windows)."""
    creationflags = 0
    try:
        creationflags = subprocess.CREATE_NEW_CONSOLE
    except Exception:
        creationflags = 0
    subprocess.Popen(cmd, cwd=cwd, creationflags=creationflags)


def start_gateway(status_var: tk.StringVar):
    try:
        status_var.set("Starting OpenClaw Gateway...")
        _run_detached(["openclaw.cmd", "gateway"], cwd=BASE)
        status_var.set("Gateway start requested.")
    except Exception as e:
        status_var.set(f"Gateway failed: {e}")


def open_dashboard(status_var: tk.StringVar):
    try:
        webbrowser.open(DASHBOARD_URL)
        status_var.set("Dashboard opened in browser.")
    except Exception as e:
        status_var.set(f"Dashboard failed: {e}")


def start_naochao(status_var: tk.StringVar):
    try:
        status_var.set("Starting NaoChao daemon + QinWan proactive loop...")
        bat = os.path.join(BASE, "start_naochao.bat")
        _run_detached(["cmd.exe", "/c", bat], cwd=BASE)

        # NOTE: start_naochao.bat already starts qinwan_mode.py.
        # Avoid starting a duplicate QinWan window here.
        status_var.set("NaoChao start requested (daemon + QinWan loop).")
    except Exception as e:
        status_var.set(f"NaoChao failed: {e}")


def _load_avatar_photo():
    """Load avatar image.

    Uses brainflow/girl_ui.png (prepared & resized) if present.
    Falls back to no image.
    """
    try:
        p = os.path.join(BASE, "girl_ui.png")
        if os.path.exists(p):
            return tk.PhotoImage(file=p)
    except Exception:
        pass
    return None


def main():
    root = tk.Tk()
    root.title("NaoChao Launcher")
    root.geometry("520x320")
    root.minsize(520, 320)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    status_var = tk.StringVar(value="Ready.")

    # Layout
    frm = ttk.Frame(root, padding=16)
    frm.pack(fill=tk.BOTH, expand=True)

    header = ttk.Frame(frm)
    header.pack(fill=tk.X)

    # left: title block
    title_block = ttk.Frame(header)
    title_block.pack(side=tk.LEFT, fill=tk.X, expand=True)

    title = ttk.Label(title_block, text="NaoChao 控制台", font=("Segoe UI", 16, "bold"))
    title.pack(anchor="w")
    subtitle = ttk.Label(title_block, text="一键启动：OpenClaw 网关 / Dashboard / 脑潮持续运行", foreground="#555")
    subtitle.pack(anchor="w", pady=(4, 0))

    # right: small gallery (does NOT cover buttons)
    gallery = ttk.Frame(header)
    gallery.pack(side=tk.RIGHT)

    def load_gallery():
        paths = []
        try:
            idx = os.path.join(BASE, "ui_gallery", "index.txt")
            if os.path.exists(idx):
                paths = [p.strip() for p in open(idx, "r", encoding="utf-8", errors="replace").read().splitlines() if p.strip()]
        except Exception:
            paths = []
        photos = []
        for p in paths[:3]:
            try:
                ph = tk.PhotoImage(file=p)
                photos.append(ph)
            except Exception:
                pass
        return photos

    photos = load_gallery()
    for ph in photos:
        lbl = ttk.Label(gallery, image=ph)
        lbl.image = ph
        lbl.pack(side=tk.LEFT, padx=4)

    ttk.Separator(frm).pack(fill=tk.X, pady=12)

    btns = ttk.Frame(frm)
    btns.pack(fill=tk.X)

    def wrap(fn):
        # run in thread to keep UI responsive
        threading.Thread(target=fn, daemon=True).start()

    b1 = ttk.Button(btns, text="启动 OpenClaw 网关", command=lambda: wrap(lambda: start_gateway(status_var)))
    b1.pack(fill=tk.X, pady=6)

    b2 = ttk.Button(btns, text="打开 Dashboard", command=lambda: open_dashboard(status_var))
    b2.pack(fill=tk.X, pady=6)

    b3 = ttk.Button(btns, text="启动 脑潮（持续运行 + 主动触达）", command=lambda: wrap(lambda: start_naochao(status_var)))
    b3.pack(fill=tk.X, pady=6)

    ttk.Separator(frm).pack(fill=tk.X, pady=12)

    status = ttk.Label(frm, textvariable=status_var, foreground="#333")
    status.pack(anchor="w")

    note = ttk.Label(
        frm,
        text="提示：如果你已在别的窗口运行过网关/脑潮，重复点击可能会启动多个实例。",
        foreground="#777",
        wraplength=480,
    )
    note.pack(anchor="w", pady=(6, 0))

    root.mainloop()


if __name__ == "__main__":
    main()
