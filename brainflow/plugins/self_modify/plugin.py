"""Self-modification pipeline (scaffold, safe-by-default).

Implements a PR-like flow (safe-by-default):
- propose_change: LLM proposes a change set restricted by allowlist.
- apply_and_test: apply change into a sandbox, run smoke tests, then promote (if enabled).
- promote: copy sandbox files back.

Design choice:
- We prefer *full-file replacements* over unified diffs to avoid brittle patching.
- Everything is logged and reversible (backup + restore on failure).

Promotion is controlled by world_model.risk_posture.self_modify.enabled.
"""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
import time
from typing import Any, Dict, List, Tuple

from plugins.openclaw_agent.plugin import run as oc_run
from plugins._json_extract import extract_first_json_object


def _load_world_model(base_dir: str) -> Dict[str, Any]:
    wm_path = os.path.join(base_dir, "state", "world_model.json")
    try:
        if os.path.exists(wm_path):
            return json.load(open(wm_path, "r", encoding="utf-8"))
    except Exception:
        pass
    return {}


def _allow(path_rel: str, allowlist: List[str]) -> bool:
    path_rel = path_rel.replace("\\", "/")
    for pat in allowlist:
        if fnmatch.fnmatch(path_rel, pat):
            return True
    return False


def _proposal_root(base_dir: str, status: str, proposal_id: str) -> str:
    return os.path.join(base_dir, "self_rewrite", status, proposal_id)


def _write_proposal_folder(base_dir: str, proposal_id: str, goal: str, allowlist: List[str], change_set: Dict[str, Any]) -> str:
    pdir = _proposal_root(base_dir, "proposals", proposal_id)
    os.makedirs(pdir, exist_ok=True)
    proposal_md = os.path.join(pdir, "proposal.md")
    edits = change_set.get("edits") or []
    files = [e.get("path") for e in edits if isinstance(e, dict)]
    rationale = str(change_set.get("rationale") or "")
    risks = change_set.get("risks") or []
    expected = change_set.get("expected_benefit") or []
    with open(proposal_md, "w", encoding="utf-8") as f:
        f.write(
            "# Self-Rewrite Proposal\n\n"
            f"- proposal_id: {proposal_id}\n"
            f"- goal: {goal}\n"
            f"- allowlist: {allowlist}\n"
            f"- files: {files}\n\n"
            f"## Rationale\n{rationale}\n\n"
            f"## Risks\n{risks}\n\n"
            f"## Expected Benefit\n{expected}\n\n"
            "## Verification Plan\n"
            "1) python -m compileall -q <sandbox>\n"
            "2) python -c \"import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')\"\n\n"
            "## Rollback Plan\n"
            "- Restore from backup_dir created during promote\n"
        )
    with open(os.path.join(pdir, "change_set.json"), "w", encoding="utf-8") as f:
        json.dump(change_set, f, ensure_ascii=False, indent=2)
    with open(os.path.join(pdir, "edits.json"), "w", encoding="utf-8") as f:
        json.dump(edits, f, ensure_ascii=False, indent=2)
    return pdir


def _move_proposal(base_dir: str, proposal_id: str, new_status: str) -> str:
    src = _proposal_root(base_dir, "proposals", proposal_id)
    dst = _proposal_root(base_dir, new_status, proposal_id)
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.move(src, dst)
    return dst


def _write_result(folder: str, result: Dict[str, Any]) -> None:
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def _restore_from_backup(base_dir: str, backup_dir: str, promoted: List[str]) -> None:
    for rel in promoted:
        src = os.path.join(backup_dir, rel)
        dst = os.path.join(base_dir, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def rollback_if_needed(scorecard_path: str | None = None, evals_path: str | None = None) -> Dict[str, Any]:
    """Rollback to latest backup if scorecard fails pass threshold.

    Returns a summary dict. Safe no-op when scorecard passes or is missing.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    scorecard_path = scorecard_path or os.path.join(base_dir, "memory", "procedural", "scorecard_latest.json")
    evals_path = evals_path or os.path.join(base_dir, "memory", "procedural", "evals.json")

    def _load(path: str) -> Dict[str, Any]:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                    if isinstance(obj, dict):
                        return obj
        except Exception:
            pass
        return {}

    scorecard = _load(scorecard_path)
    if not scorecard:
        return {"ok": True, "action": "no_rollback", "note": "scorecard_missing"}

    evals = _load(evals_path)
    pass_threshold = int(evals.get("pass_threshold") or 70)
    overall = int(scorecard.get("overall_score") or 0)
    passed = bool(scorecard.get("pass")) or overall >= pass_threshold

    if passed:
        return {"ok": True, "action": "no_rollback", "overall": overall, "threshold": pass_threshold}

    backup_root = os.path.join(base_dir, "_backup")
    if not os.path.isdir(backup_root):
        return {"ok": False, "action": "rollback", "error": "no_backup_root"}

    # pick latest backup dir
    latest_dir = None
    latest_ts = 0.0
    for name in os.listdir(backup_root):
        p = os.path.join(backup_root, name)
        if os.path.isdir(p):
            ts = os.path.getmtime(p)
            if ts > latest_ts:
                latest_ts = ts
                latest_dir = p

    if not latest_dir:
        return {"ok": False, "action": "rollback", "error": "no_backup_dir"}

    restored = []
    for root, _, files in os.walk(latest_dir):
        for fn in files:
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, latest_dir)
            dst = os.path.join(base_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            restored.append(rel.replace("\\", "/"))

    # log rollback
    log_path = os.path.join(base_dir, "memory", "procedural", "rollback_log.jsonl")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "t": int(time.time()),
                "overall": overall,
                "threshold": pass_threshold,
                "backup_dir": latest_dir,
                "restored": restored,
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return {
        "ok": True,
        "action": "rollback",
        "overall": overall,
        "threshold": pass_threshold,
        "backup_dir": latest_dir,
        "restored": restored,
    }


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        return [x]
    return [x]


def propose_change(goal: str, context_paths: List[str] | None = None, thinking: str = "minimal") -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    wm = _load_world_model(base_dir)
    allowlist = (((wm.get("risk_posture") or {}).get("self_modify") or {}).get("allowlist") or [])
    if not allowlist:
        allowlist = ["workflows/*.yaml", "memory/procedural/*.json", "POLICY.md", "VALUE_SYSTEM.md"]

    # IMPORTANT: keep prompt SHORT to avoid Windows CLI arg-length failures.
    # Do NOT inline large files. Provide only minimal failure context.
    score_path = os.path.join(base_dir, "memory", "procedural", "scorecard_latest.json")
    evals_path = os.path.join(base_dir, "memory", "procedural", "evals.json")
    last_score = {}
    evals = {}
    try:
        if os.path.exists(score_path):
            last_score = json.load(open(score_path, "r", encoding="utf-8"))
    except Exception:
        last_score = {}
    try:
        if os.path.exists(evals_path):
            evals = json.load(open(evals_path, "r", encoding="utf-8"))
    except Exception:
        evals = {}

    # Summarize failures from last scorecard / known bottlenecks.
    score_notes = str((last_score or {}).get("notes") or "")
    score_evidence = (last_score or {}).get("evidence")
    if not isinstance(score_evidence, list):
        score_evidence = []

    overall_score = int((last_score or {}).get("overall_score") or 0)
    pass_threshold = int((evals or {}).get("pass_threshold") or 70)
    score_pass = bool((last_score or {}).get("pass")) or (overall_score >= pass_threshold)
    evidence_text = " ".join([str(x) for x in score_evidence])
    has_issue = any(k in (score_notes + " " + evidence_text).lower() for k in ["error", "fail", "repeat", "pending", "loop", "parse"])

    # If metrics are healthy, skip change (self-eval gating for L4).
    if score_pass and not has_issue:
        now = int(time.time())
        cs = {
            "schema": "brainflow.change_set.v2",
            "t": now,
            "rationale": "Scorecard healthy; skip self-modify this cycle.",
            "edits": [],
            "risks": [],
            "expected_benefit": [],
        }
        out_dir = os.path.join(base_dir, "memory", "procedural")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "change_set_latest.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cs, f, ensure_ascii=False, indent=2)
        return {"ok": True, "path": out_path, "change_set": cs, "llm": {"ok": False, "skipped": True}}

    # Write a compact payload to file to avoid Windows CLI argument length limits.
    payload_dir = os.path.join(base_dir, "memory", "procedural")
    os.makedirs(payload_dir, exist_ok=True)
    payload_path = os.path.join(payload_dir, "self_modify_payload_latest.json")

    payload = {
        "schema": "brainflow.self_modify_payload.v1",
        "t": int(time.time()),
        "goal": goal,
        "allowlist": allowlist,
        "signals": {
            "last_scorecard_overall": overall_score,
            "last_scorecard_pass": score_pass,
            "last_scorecard_notes": score_notes[:400],
            "last_scorecard_evidence": score_evidence[:10],
        },
        "output_schema": {
            "schema": "brainflow.change_set.v2",
            "keys": ["schema", "t", "rationale", "edits", "risks", "expected_benefit"],
            "constraints": {
                "max_files": 1,
                "full_file_replacement": True,
            },
        },
    }

    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    prompt = f"""Read local JSON payload file (JSON):
{payload_path}

Return STRICT JSON ONLY matching schema brainflow.change_set.v2.
One edit max; path must be in payload.allowlist.
Prefer changes that reduce Windows CLI arg-length risk and avoid reading any other local files.
No markdown. No code fences. No commentary. No extra keys.
"""

    # Keep timeout short; on failure we record and continue.
    try:
        r = oc_run(
            prompt,
            thinking=thinking,
            session_id="",
            timeout_sec=20,
            strict_json=True,
            expect_json=True,
            repair_attempts=1,
            agent_id="bf-codex",
            prefer_http=True,
        )
    except Exception as e:
        r = {"ok": False, "error": f"oc_run_exception:{e}"}
    now = int(time.time())
    txt = ""
    if not r.get("ok"):
        # Persist an empty change set so the workflow can continue.
        cs = {
            "schema": "brainflow.change_set.v2",
            "t": now,
            "rationale": "LLM call failed; no change proposed.",
            "edits": [],
            "risks": ["llm_call_failed"],
            "expected_benefit": [],
            "llm_error": r,
        }
    else:
        txt = (r.get("text") or "").strip()
        parsed = r.get("json") if isinstance(r.get("json"), dict) else None
        err = None
        if parsed is None:
            parsed, err = extract_first_json_object(txt)
        if not isinstance(parsed, dict):
            # Attempt a short repair pass: convert the prior text into STRICT change_set JSON.
            repair = (
                "Convert the following into STRICT JSON ONLY matching schema brainflow.change_set.v2. "
                "Do not include any commentary, markdown, or code fences. "
                "Return exactly one edit.\n\n"
                "Required JSON keys: schema,t,rationale,edits,risks,expected_benefit\n"
                "edits must be an array with ONE object {path, content} where content is FULL new file content.\n\n"
                + txt[:1800]
            )
            try:
                rr = oc_run(
                    repair,
                    thinking=thinking,
                    session_id="",
                    timeout_sec=15,
                    strict_json=True,
                    expect_json=True,
                    repair_attempts=1,
                    prefer_http=True,
                    agent_id="bf-codex",
                )
            except Exception as e:
                rr = {"ok": False, "error": f"oc_run_exception:{e}"}
            if rr.get("ok"):
                reparsed = rr.get("json") if isinstance(rr.get("json"), dict) else None
                if reparsed is None:
                    rtxt = (rr.get("text") or "").strip()
                    reparsed, _ = extract_first_json_object(rtxt)
                if isinstance(reparsed, dict):
                    cs = reparsed
                else:
                    cs = {
                        "schema": "brainflow.change_set.v2",
                        "t": now,
                        "rationale": "LLM output not JSON (repair failed); no change proposed.",
                        "edits": [],
                        "risks": ["llm_json_parse_failed"],
                        "expected_benefit": [],
                        "llm_parse_error": err,
                        "llm_text_tail": txt[-2000:],
                    }
            else:
                cs = {
                    "schema": "brainflow.change_set.v2",
                    "t": now,
                    "rationale": "LLM output not JSON (repair call failed); no change proposed.",
                    "edits": [],
                    "risks": ["llm_json_parse_failed"],
                    "expected_benefit": [],
                    "llm_parse_error": err,
                    "llm_text_tail": txt[-2000:],
                }
        else:
            cs = parsed

    # Enforce allowlist and normalize (and enforce ONLY ONE edit).
    edits = []
    for e in (cs.get("edits") or []):
        if not isinstance(e, dict):
            continue
        p = str(e.get("path") or "")
        c = e.get("content")
        if not p or not isinstance(c, str):
            continue
        if _allow(p, allowlist):
            edits.append({"path": p, "content": c})
        if len(edits) >= 1:
            break

    # If we got a parsed dict, enforce allowlist & normalize; otherwise keep empty edits.
    if isinstance(cs, dict) and cs.get("edits"):
        cs = {
            "schema": "brainflow.change_set.v2",
            "t": now,
            "rationale": str(cs.get("rationale") or ""),
            "edits": edits,
            "risks": _as_list(cs.get("risks")),
            "expected_benefit": _as_list(cs.get("expected_benefit")),
        }
    else:
        cs.setdefault("schema", "brainflow.change_set.v2")
        cs["t"] = now
        cs["edits"] = []

    # Attach proposal_id and persist into self_rewrite/proposals
    proposal_id = time.strftime("proposal-%Y%m%d-%H%M%S")
    cs["proposal_id"] = proposal_id
    try:
        _write_proposal_folder(base_dir, proposal_id, goal, allowlist, cs)
    except Exception:
        pass

    out_dir = os.path.join(base_dir, "memory", "procedural")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "change_set_latest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cs, f, ensure_ascii=False, indent=2)

    return {"ok": True, "path": out_path, "change_set": cs, "llm": r}


def apply_and_test(change_set_path: str = "", sandbox_name: str = "") -> Dict[str, Any]:
    """Apply a change_set (full-file edits) in a sandbox, smoke test, then promote if enabled.

    Smoke tests (safe, offline):
    - python -m compileall on sandbox
    - import core.engine

    If tests fail, nothing is promoted.
    """

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if not change_set_path:
        change_set_path = os.path.join(base_dir, "memory", "procedural", "change_set_latest.json")

    try:
        cs = json.load(open(change_set_path, "r", encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"failed_to_load_change_set: {e}"}

    proposal_id = str(cs.get("proposal_id") or "")

    edits = cs.get("edits") or []
    if not isinstance(edits, list) or not edits:
        # mark as rejected (no-op) if a proposal exists
        if proposal_id:
            dst = _move_proposal(base_dir, proposal_id, "rejected")
            _write_result(dst, {"ok": True, "note": "no_edits_skip"})
        return {"ok": True, "note": "no_edits_skip"}

    if not sandbox_name:
        sandbox_name = time.strftime("sandbox-%Y%m%d-%H%M%S")
    sb_dir = os.path.join(base_dir, "_sandbox", sandbox_name)
    os.makedirs(sb_dir, exist_ok=True)

    # Copy a minimal runnable tree.
    for rel in ["core", "plugins", "registry", "workflows", "memory/procedural", "POLICY.md", "VALUE_SYSTEM.md", "state"]:
        src = os.path.join(base_dir, rel)
        dst = os.path.join(sb_dir, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    # Apply edits into sandbox.
    applied: List[str] = []
    for e in edits:
        if not isinstance(e, dict):
            continue
        p = str(e.get("path") or "").replace("\\", "/")
        c = e.get("content")
        if not p or not isinstance(c, str):
            continue
        dst = os.path.join(sb_dir, p)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(c)
        applied.append(p)

    # Persist change_set into sandbox.
    os.makedirs(sb_dir, exist_ok=True)
    shutil.copy2(change_set_path, os.path.join(sb_dir, "change_set.json"))

    # Smoke test
    import subprocess, sys

    py = sys.executable
    try:
        p1 = subprocess.run([py, "-m", "compileall", "-q", sb_dir], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p1.returncode != 0:
            res = {"ok": False, "sandbox_dir": sb_dir, "applied": applied, "error": "compileall_failed", "stderr": p1.stderr[-2000:], "stdout": p1.stdout[-2000:]}
            if proposal_id:
                dst = _move_proposal(base_dir, proposal_id, "rejected")
                _write_result(dst, res)
            return res

        p2 = subprocess.run([py, "-c", "import sys; sys.path.insert(0, r'" + sb_dir.replace("'", "''") + "'); import core.engine; print('import_ok')"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p2.returncode != 0 or "import_ok" not in (p2.stdout or ""):
            res = {"ok": False, "sandbox_dir": sb_dir, "applied": applied, "error": "import_failed", "stderr": p2.stderr[-2000:], "stdout": p2.stdout[-2000:]}
            if proposal_id:
                dst = _move_proposal(base_dir, proposal_id, "rejected")
                _write_result(dst, res)
            return res
    except Exception as e:
        res = {"ok": False, "sandbox_dir": sb_dir, "applied": applied, "error": f"smoke_test_exception:{e}"}
        if proposal_id:
            dst = _move_proposal(base_dir, proposal_id, "rejected")
            _write_result(dst, res)
        return res

    # Promote if enabled
    promo = promote(sb_dir)
    res = {"ok": bool(promo.get("ok")), "sandbox_dir": sb_dir, "applied": applied, "promote": promo}
    if proposal_id:
        dst = _move_proposal(base_dir, proposal_id, "applied" if res.get("ok") else "rejected")
        _write_result(dst, res)
    return res


def promote(sandbox_dir: str) -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    wm = _load_world_model(base_dir)
    sm = ((wm.get("risk_posture") or {}).get("self_modify") or {})
    enabled = bool(sm.get("enabled"))
    allowlist = sm.get("allowlist") or []
    if not enabled:
        return {"ok": False, "error": "self_modify disabled by world_model.risk_posture.self_modify.enabled"}

    # Backup originals for allowlisted files we might overwrite.
    backup_dir = os.path.join(base_dir, "_backup", time.strftime("backup-%Y%m%d-%H%M%S"))
    os.makedirs(backup_dir, exist_ok=True)

    promoted: List[str] = []
    for root, _, files in os.walk(sandbox_dir):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, sandbox_dir).replace("\\", "/")
            if not _allow(rel, allowlist):
                continue
            src = full
            dst = os.path.join(base_dir, rel)
            # backup existing
            if os.path.exists(dst):
                bdst = os.path.join(backup_dir, rel)
                os.makedirs(os.path.dirname(bdst), exist_ok=True)
                shutil.copy2(dst, bdst)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            promoted.append(rel)

    # Post-promote smoke test on base_dir; rollback on failure
    import subprocess, sys

    py = sys.executable
    try:
        p1 = subprocess.run([py, "-m", "compileall", "-q", base_dir], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p1.returncode != 0:
            _restore_from_backup(base_dir, backup_dir, promoted)
            return {"ok": False, "error": "post_promote_compileall_failed", "stderr": p1.stderr[-2000:], "stdout": p1.stdout[-2000:], "backup_dir": backup_dir, "promoted": promoted}

        p2 = subprocess.run([py, "-c", "import sys; sys.path.insert(0, r'" + base_dir.replace("'", "''") + "'); import core.engine; print('import_ok')"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p2.returncode != 0 or "import_ok" not in (p2.stdout or ""):
            _restore_from_backup(base_dir, backup_dir, promoted)
            return {"ok": False, "error": "post_promote_import_failed", "stderr": p2.stderr[-2000:], "stdout": p2.stdout[-2000:], "backup_dir": backup_dir, "promoted": promoted}
    except Exception as e:
        _restore_from_backup(base_dir, backup_dir, promoted)
        return {"ok": False, "error": f"post_promote_exception:{e}", "backup_dir": backup_dir, "promoted": promoted}

    return {"ok": True, "note": "Promoted sandbox changes (allowlisted files only).", "backup_dir": backup_dir, "promoted": promoted}
