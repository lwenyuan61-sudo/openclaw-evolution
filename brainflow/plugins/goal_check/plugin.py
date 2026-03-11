"""Goal/Task achievement checker (local command based).

The owner requested: prefer local command execution for state verification.

This plugin is intentionally conservative:
- It only runs a provided command (list of strings) via subprocess.
- It blocks obviously destructive commands by a denylist.
- Success is determined by exit code (0) and optional stdout/stderr regex match.

Input schema (suggested):
{
  "cmd": ["powershell", "-NoProfile", "-Command", "..."],
  "cwd": "..." (optional),
  "timeout_sec": 20 (optional),
  "expect_regex": "..." (optional),
  "expect_in": "stdout"|"stderr"|"both" (optional)
}

Returns:
{ ok, achieved, returncode, stdout_tail, stderr_tail, reason }
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List, Optional


_DENY_PATTERNS = [
    r"\brm\b",
    r"\bdel\b",
    r"\berase\b",
    r"\brmdir\b",
    r"\brd\b",
    r"Remove-Item",
    r"format\.com",
    r"\bformat\b",
    r"shutdown",
    r"reboot",

    # Prevent self-reentrancy / accidental daemon spawning.
    r"\bdaemon\.py\b",
    r"supervisor\.ps1",
    r"brainflow\\daemon\.py",
]


def _is_allowed(cmd: List[str]) -> tuple[bool, str]:
    s = " ".join(cmd)
    for pat in _DENY_PATTERNS:
        if re.search(pat, s, flags=re.IGNORECASE):
            return False, f"blocked by deny pattern: {pat}"
    return True, ""


def run(
    cmd: List[str],
    cwd: str | None = None,
    timeout_sec: int = 20,
    expect_regex: str | None = None,
    expect_in: str = "stdout",
) -> Dict[str, Any]:
    if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
        return {"ok": False, "achieved": False, "reason": "cmd must be a non-empty list[str]"}

    ok_allowed, why = _is_allowed(cmd)
    if not ok_allowed:
        return {"ok": False, "achieved": False, "reason": why, "cmd": cmd}

    try:
        p = subprocess.run(
            cmd,
            cwd=cwd or None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(timeout_sec),
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": True, "achieved": False, "reason": "timeout"}
    except Exception as e:
        return {"ok": False, "achieved": False, "reason": f"exec failed: {e}", "cmd": cmd}

    stdout = p.stdout or ""
    stderr = p.stderr or ""

    achieved = (p.returncode == 0)
    reason = "exitcode==0" if achieved else f"exitcode=={p.returncode}"

    if expect_regex:
        try:
            target = stdout if expect_in == "stdout" else stderr if expect_in == "stderr" else (stdout + "\n" + stderr)
            if re.search(expect_regex, target, flags=re.IGNORECASE | re.MULTILINE):
                achieved = achieved and True
                reason += "+regex_match"
            else:
                achieved = False
                reason = "regex_miss"
        except Exception as _e:
            achieved = False
            reason = "regex_error"

    return {
        "ok": True,
        "achieved": bool(achieved),
        "returncode": int(p.returncode),
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "reason": reason,
        "cmd": cmd,
    }
