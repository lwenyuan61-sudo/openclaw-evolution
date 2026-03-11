"""Call OpenClaw agent (GPT) from BrainFlow.

This lets BrainFlow delegate subgoal generation, decomposition, web search, and message drafting
back to OpenClaw's main model/tool stack.

Implementation:
- Uses `openclaw.cmd agent --session-id brainflow-gpt --message ... --thinking minimal --json`.
- Returns the concatenated text payloads.

Safety:
- This plugin only *asks* OpenClaw agent to think/search; it does not directly execute OS commands.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from plugins._json_extract import extract_first_json_object

OPENCLAW = r"C:\Users\15305\AppData\Roaming\npm\openclaw.cmd"

# Gateway HTTP Chat Completions endpoint (enabled in openclaw.json)
GATEWAY_HTTP_BASE = "http://127.0.0.1:18789"


def _build_message(user_message: str, strict_json: bool) -> str:
    if not strict_json:
        return user_message

    # Keep this prefix short to avoid Windows command-line length issues.
    prefix = (
        "You are executing a task for an automated pipeline.\n"
        "Return STRICT JSON only. No markdown, no code fences, no commentary.\n"
        "If you are missing information, still return JSON with best-effort fields.\n"
        "\n"
    )
    # Avoid embedded raw newlines in Windows argv which can cause odd CLI parsing in some shells.
    msg = (user_message or "").replace("\r", "")
    msg = msg.replace("\n", "\\n")
    # Hard cap to reduce Windows argv-too-long failures when falling back to CLI.
    if len(msg) > 4000:
        msg = msg[:4000] + "..."
    return prefix + msg


def _extract_json_best_effort(text: str) -> tuple[dict | None, str | None]:
    # Try to recover the first JSON object from a response.
    obj, err = extract_first_json_object(text or "")
    if isinstance(obj, dict):
        return obj, None
    return None, err or "json_extract_failed"


def _safe_read_text(path: str, max_chars: int = 200000) -> str:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_chars)
    except Exception:
        pass
    return ""


def _read_gateway_token() -> str:
    """Read gateway token from ~/.openclaw/openclaw.json (same host) or env var."""
    tok = os.environ.get("OPENCLAW_GATEWAY_TOKEN") or os.environ.get("OPENCLAW_GATEWAY_AUTH_TOKEN")
    if tok:
        return tok.strip()

    # Default config path
    try:
        cfg_path = os.path.expanduser(r"~\.openclaw\openclaw.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8", errors="replace") as f:
                cfg = json.load(f)
            tok2 = (((cfg or {}).get("gateway") or {}).get("auth") or {}).get("token")
            if isinstance(tok2, str) and tok2.strip():
                return tok2.strip()
    except Exception:
        pass

    return ""


def _http_chat_completions(
    prompt: str,
    *,
    agent_id: str = "main",
    timeout_sec: int = 120,
    strict_json: bool = False,
) -> Dict[str, Any]:
    """Call the gateway HTTP /v1/chat/completions endpoint and return assistant text.

    strict_json=True adds a system message to suppress persona/style and force JSON-only output.

    NOTE: When strict_json=True, we first attempt to request a JSON object response format.
    If the gateway/model does not support that parameter, we fall back to a plain call.
    """
    token = _read_gateway_token()
    if not token:
        return {"ok": False, "error": "missing_gateway_token"}

    url = GATEWAY_HTTP_BASE.rstrip("/") + "/v1/chat/completions"

    def _do_call(with_response_format: bool) -> Dict[str, Any]:
        messages = []
        if strict_json:
            messages.append(
                {
                    "role": "system",
                    "content": "You are a backend worker for an automated pipeline. Output STRICT JSON only. No markdown, no code fences, no commentary.",
                }
            )
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model": "openclaw",
            "messages": messages,
        }

        # Prefer a transport-level JSON enforcement when available to reduce parse failures.
        # (Not all backends support response_format; we fall back gracefully.)
        if strict_json and with_response_format:
            body["response_format"] = {"type": "json_object"}

        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-openclaw-agent-id", agent_id)

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            try:
                body_txt = e.read().decode("utf-8", errors="replace")
            except Exception:
                body_txt = ""
            return {"ok": False, "error": f"http_status_{getattr(e, 'code', 'unknown')}", "raw_text": body_txt[:2000]}
        except Exception as e:
            return {"ok": False, "error": f"http_call_failed:{e}"}

        try:
            j = json.loads(raw)
            txt = (((j.get("choices") or [])[0] or {}).get("message") or {}).get("content")
            if isinstance(txt, str):
                return {"ok": True, "text": txt, "raw": j}
        except Exception as e:
            return {"ok": False, "error": f"http_json_parse_failed:{e}", "raw_text": raw[:2000]}

        return {"ok": False, "error": "http_unexpected_response", "raw_text": raw[:2000]}

    # Attempt with response_format first; fall back if unsupported or rejected.
    if strict_json:
        r1 = _do_call(with_response_format=True)
        if r1.get("ok"):
            return r1
        r2 = _do_call(with_response_format=False)
        return r2

    return _do_call(with_response_format=False)


def _debug_dump(base_dir: str, session_id: str, cmd: list[str], stdout: str, stderr: str):
    """Persist raw subprocess output for debugging (local only)."""
    try:
        logs_dir = os.path.join(base_dir, "logs", "oc_agent")
        os.makedirs(logs_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        prefix = f"oc_agent_{ts}_{session_id}".replace(":", "-").replace("/", "-")
        meta_path = os.path.join(logs_dir, prefix + ".meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"t": int(time.time()), "session_id": session_id, "cmd": cmd}, f, ensure_ascii=False, indent=2)
        with open(os.path.join(logs_dir, prefix + ".stdout.txt"), "w", encoding="utf-8", errors="replace") as f:
            f.write(stdout or "")
        with open(os.path.join(logs_dir, prefix + ".stderr.txt"), "w", encoding="utf-8", errors="replace") as f:
            f.write(stderr or "")
    except Exception:
        pass


def run(
    message: str,
    thinking: str = "minimal",
    session_id: str = "brainflow-gpt",
    timeout_sec: int = 60,
    *,
    strict_json: bool = True,
    expect_json: bool = False,
    repair_attempts: int = 1,
    debug: bool = True,
    prefer_http: bool = True,
    agent_id: str = "main",
) -> Dict[str, Any]:
    """Call OpenClaw agent.

    strict_json: prepend a short JSON-only instruction prefix.
    expect_json: if True, attempt to extract a JSON object from the model text and (optionally) repair once.
    """

    # Use a fresh-ish session_id if caller passes an empty string.
    # This reduces "context drift" where the agent starts asking meta-questions instead of returning JSON.
    if not session_id:
        session_id = f"brainflow-{int(__import__('time').time())}"

    # For HTTP calls we want raw newlines (no argv escaping). For CLI calls we still escape.
    built_http = message if not strict_json else (
        "You are executing a task for an automated pipeline.\n"
        "Return STRICT JSON only. No markdown, no code fences, no commentary.\n"
        "If you are missing information, still return JSON with best-effort fields.\n\n"
        + (message or "")
    )
    built = _build_message(message, strict_json=strict_json)

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Prefer HTTP whenever strict_json is requested (the common BrainFlow mode):
    # it's more stable on Windows and avoids command-line length limits.
    if prefer_http and (strict_json or expect_json or len(built) > 6000):
        http_r = _http_chat_completions(
            built_http,
            agent_id=agent_id,
            timeout_sec=int(timeout_sec),
            strict_json=strict_json,
        )
        if http_r.get("ok"):
            text = str(http_r.get("text") or "").strip()
            result: Dict[str, Any] = {"ok": True, "text": text, "raw": http_r.get("raw"), "via": "http"}

            if not expect_json:
                return result

            # JSON extraction + optional repair using HTTP only (no subprocess).
            obj, err = _extract_json_best_effort(text)
            if obj is not None:
                result["json"] = obj
                return result

            attempts = max(0, int(repair_attempts))
            if attempts <= 0:
                result["json"] = None
                result["json_error"] = err
                return result

            prev = text
            if len(prev) > 1800:
                prev = prev[:1800] + "..."

            repair_prompt = (
                "Your previous response did not contain valid JSON. "
                "Re-output ONLY the JSON object required by the task instructions. "
                "No markdown, no commentary, no code fences.\n\n"
                "Previous response:\n" + prev
            )

            http_r2 = _http_chat_completions(
                built_http + "\n\n[JSON_REPAIR]\n" + repair_prompt,
                agent_id=agent_id,
                timeout_sec=int(timeout_sec),
                strict_json=True,
            )
            if http_r2.get("ok"):
                text2 = str(http_r2.get("text") or "").strip()
                obj2, err2 = _extract_json_best_effort(text2)
                result["repair"] = {"ok": True, "text": text2[:2000]}
                result["json"] = obj2
                result["json_error"] = err2 or err
            else:
                result["repair"] = {"ok": False, "error": http_r2.get("error")}
                result["json"] = None
                result["json_error"] = err

            return result

        # Prefer HTTP only to avoid CLI hangs in long-running loops.
        return {"ok": False, "error": http_r.get("error") or "http_failed", "via": "http"}

    # IMPORTANT (Windows): openclaw.cmd is a batch file; calling it directly with shell=False
    # can yield unexpected output. Prefer cmd.exe /c.
    cmd = [
        "cmd",
        "/c",
        OPENCLAW,
        "agent",
        "--channel",
        "last",
        "--session-id",
        session_id,
        "--message",
        built,
        "--thinking",
        thinking,
        "--json",
        "--timeout",
        str(int(timeout_sec)),
    ]

    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
    if debug:
        _debug_dump(base_dir, session_id, cmd, p.stdout or "", p.stderr or "")

    if p.returncode != 0:
        return {
            "ok": False,
            "returncode": p.returncode,
            "stderr": (p.stderr or "")[-4000:],
            "stdout": (p.stdout or "")[-4000:],
            "cmd": cmd,
        }

    out = (p.stdout or "").strip()

    # Some Windows pipe/capture situations appear to collapse OpenClaw JSON output into a single
    # summary word like "completed". If so, re-run with stdout redirected to a file, then read it.
    if out.strip().lower() in ("completed", "ok", "done"):
        try:
            logs_dir = os.path.join(base_dir, "logs", "oc_agent")
            os.makedirs(logs_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d-%H%M%S")
            capture_path = os.path.join(logs_dir, f"oc_agent_{ts}_{session_id}.stdout_capture.json")
            with open(capture_path, "w", encoding="utf-8", errors="replace") as f:
                p2 = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", shell=False)
            if debug:
                _debug_dump(base_dir, session_id + "_rerun", cmd, _safe_read_text(capture_path, 200000), p2.stderr or "")
            out2 = _safe_read_text(capture_path, 200000).strip()
            if out2:
                out = out2
        except Exception:
            pass

    try:
        data = json.loads(out)
    except Exception:
        # Sometimes non-JSON prelude text precedes the JSON.
        data, _ = extract_first_json_object(out)

    # If stdout is unexpectedly just a summary like "completed", fall back to stderr scan.
    if (not data) and (out.strip().lower() in ("completed", "ok", "done")):
        data2, _ = extract_first_json_object((p.stderr or "") + "\n" + (p.stdout or ""))
        data = data2

    # Last-resort fallback: use the Gateway HTTP chat-completions endpoint.
    # This avoids a Windows subprocess capture quirk where openclaw.cmd collapses JSON output.
    if (not data) and (out.strip().lower() in ("completed", "ok", "done")):
        http_r = _http_chat_completions(built, agent_id="main", timeout_sec=int(timeout_sec))
        if http_r.get("ok"):
            text = str(http_r.get("text") or "").strip()
            warn = "openclaw_agent_fallback_http"
            out = text
            data = None
        else:
            warn = f"openclaw_agent_fallback_http_failed:{http_r.get('error')}"

    # Unwrap the OpenClaw JSON envelope -> plain text.
    # NOTE: Newer OpenClaw versions may output either:
    # (A) an envelope: { ok, result: { payloads:[{text,...}], ... } }
    # (B) direct model output (often already JSON when strict_json is used)
    if isinstance(data, dict):
        payloads = None
        try:
            payloads = (((data or {}).get("result") or {}).get("payloads") or None)
        except Exception:
            payloads = None

        if isinstance(payloads, list):
            text = "\n".join([str(x.get("text", "")) for x in payloads if isinstance(x, dict)]).strip()
            warn = None
            # If payloads exist but are empty, fall back to raw output.
            if not text:
                text = out
                warn = "openclaw_agent_empty_payloads_fallback_raw"
        else:
            # Direct-output mode: treat stdout as the model text.
            text = out
            warn = "openclaw_agent_direct_output"
    else:
        text = out
        warn = "openclaw_agent_json_parse_failed"

    result: Dict[str, Any] = {"ok": True, "text": text, "raw": data if isinstance(data, dict) else None, "cmd": cmd}
    if warn:
        result["warn"] = warn

    if not expect_json:
        return result

    # Best-effort JSON extraction from the model text.
    obj, err = _extract_json_best_effort(text)
    if obj is not None:
        result["json"] = obj
        return result

    # One small repair loop: ask the model to restate ONLY the JSON object.
    attempts = max(0, int(repair_attempts))
    if attempts <= 0:
        result["json"] = None
        result["json_error"] = err
        return result

    # Trim to keep command length safe.
    prev = (text or "")
    if len(prev) > 1800:
        prev = prev[:1800] + "..."

    repair_msg = (
        "Your previous response did not contain valid JSON.\n"
        "Re-output ONLY the JSON object required by the task instructions.\n"
        "No markdown, no commentary, no code fences.\n"
        "\n"
        "Previous response:\n"
        f"{prev}\n"
    )

    # Keep the same session_id to preserve context of the original task.
    r2 = run(
        message + "\n\n[JSON_REPAIR]\n" + repair_msg,
        thinking=thinking,
        session_id=session_id,
        timeout_sec=timeout_sec,
        strict_json=True,
        expect_json=False,
        repair_attempts=0,
    )

    obj2, err2 = _extract_json_best_effort(r2.get("text") or "")
    result["repair"] = {"ok": bool(r2.get("ok")), "text": (r2.get("text") or "")[:2000]}
    result["json"] = obj2
    result["json_error"] = err2 or err
    return result
