"""Utility: robustly extract a JSON value from an LLM response.

BrainFlow frequently asks OpenClaw agent for STRICT JSON, but models sometimes add prose,
markdown fences, or multiple JSON blocks.

This helper tries hard to recover the *first* valid JSON value (object OR array) from text.

Constraints:
- Standard library only.

Design goals:
- Be conservative (don't "invent" structure).
- Prefer extracting an actually-parseable JSON substring.
- Provide a compact error string for logging/telemetry.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple


def _strip_code_fences(s: str) -> str:
    # If the model wrapped JSON in a markdown fence, prefer the first fenced block.
    # Examples:
    # ```json\n{...}\n```
    # ```\n[...]\n```
    if "```" not in s:
        return s

    # Find first fence.
    i = s.find("```")
    if i == -1:
        return s
    j = s.find("\n", i + 3)
    if j == -1:
        return s

    # Find closing fence.
    k = s.find("```", j + 1)
    if k == -1:
        return s

    inner = s[j + 1 : k]
    return inner.strip() or s


def _try_json_loads(s: str) -> Tuple[Any | None, str | None]:
    try:
        return json.loads(s), None
    except Exception as e:
        return None, f"json_parse_failed:{e}"


def _remove_trailing_commas(candidate: str) -> str:
    # Common near-JSON: trailing commas before '}' or ']'.
    # Apply a few times to catch nested cases.
    out = candidate
    for _ in range(3):
        out2 = re.sub(r",(\s*[}\]])", r"\1", out)
        if out2 == out:
            break
        out = out2
    return out


def extract_first_json_value(text: str) -> Tuple[Any | None, str | None]:
    """Return (value, error). Value is None if not found/parse failed.

    - Accepts object or array.
    - Attempts: whole string, fenced block, balanced substring scan.
    """

    if not text:
        return None, "empty_text"

    s = (text or "").strip().lstrip("\ufeff")
    if not s:
        return None, "empty_text"

    # 1) Fast path: whole string.
    v, err = _try_json_loads(s)
    if err is None:
        return v, None

    # 2) If code fences exist, try inside fence.
    fenced = _strip_code_fences(s)
    if fenced != s:
        v2, err2 = _try_json_loads(fenced)
        if err2 is None:
            return v2, None

    # 3) Balanced scan for first {...} or [...], respecting JSON strings.
    # Find earliest start of object/array.
    starts = [p for p in [s.find("{"), s.find("[")] if p != -1]
    if not starts:
        return None, "no_json_start"
    start = min(starts)

    in_str = False
    esc = False
    depth_obj = 0
    depth_arr = 0
    end = -1

    for i in range(start, len(s)):
        ch = s[i]

        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == "{":
            depth_obj += 1
        elif ch == "}":
            depth_obj -= 1
        elif ch == "[":
            depth_arr += 1
        elif ch == "]":
            depth_arr -= 1

        if depth_obj < 0 or depth_arr < 0:
            return None, "unbalanced_close"

        if (depth_obj + depth_arr) == 0 and i >= start:
            end = i
            break

    if end == -1:
        return None, "no_balanced_json"

    candidate = s[start : end + 1].strip()

    # 3a) Parse candidate.
    v3, err3 = _try_json_loads(candidate)
    if err3 is None:
        return v3, None

    # 3b) Small heuristic repair: remove trailing commas.
    repaired = _remove_trailing_commas(candidate)
    if repaired != candidate:
        v4, err4 = _try_json_loads(repaired)
        if err4 is None:
            return v4, None

    return None, err3


def extract_first_json_object(text: str) -> Tuple[Dict[str, Any] | None, str | None]:
    """Compatibility wrapper: return first JSON object."""

    v, err = extract_first_json_value(text)
    if isinstance(v, dict):
        return v, None
    if v is None:
        return None, err
    return None, "json_not_object"


def extract_first_json_array(text: str) -> Tuple[List[Any] | None, str | None]:
    """Return first JSON array."""

    v, err = extract_first_json_value(text)
    if isinstance(v, list):
        return v, None
    if v is None:
        return None, err
    return None, "json_not_array"
