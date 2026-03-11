"""Send a WhatsApp message via OpenClaw CLI.

Safety: this is a thin wrapper around `openclaw message send`.
Use only for self-chat or approved recipients.
"""

from __future__ import annotations

import subprocess
from typing import Any, Optional


OPENCLAW = r"C:\Users\15305\AppData\Roaming\npm\openclaw.cmd"


def run(target: str, message: str, account: Optional[str] = None) -> Any:
    cmd = [OPENCLAW, "message", "send", "--channel", "whatsapp", "--target", target, "--message", message]
    if account:
        cmd.extend(["--account", account])
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": (p.stdout or "")[-4000:],
            "stderr": (p.stderr or "")[-4000:],
            "cmd": cmd,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": cmd}
