from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
UPGRADE_PATH = AUTO / "upgrade-state.json"
GOAL_PATH = AUTO / "goal-register.json"
LOG_PATH = AUTO / "experiment-log.jsonl"
REPORT_PATH = STATE / "autonomy_web_scout.json"

USER_AGENT = "OpenClaw-AutonomyWebScout/0.1 (+read-only curiosity scout)"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default or {})


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def tail_jsonl(path: Path, limit: int = 12) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"unparsed": line[:300]})
    return rows


def strip_tags(text: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def slug(text: str, max_len: int = 56) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.lower()).strip("-")
    return (cleaned[:max_len].strip("-") or "topic")


def fetch_url(url: str, timeout: float = 8.0, max_bytes: int = 220_000) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - read-only scout, URL is generated/whitelisted by state.
        return resp.read(max_bytes).decode("utf-8", errors="replace")


def unwrap_duckduckgo_url(url: str) -> str:
    parsed = urllib.parse.urlparse(html.unescape(url))
    qs = urllib.parse.parse_qs(parsed.query)
    if "uddg" in qs and qs["uddg"]:
        return qs["uddg"][0]
    return html.unescape(url)


def result_quality(result: dict[str, Any], page_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify search results before turning them into autonomy goals.

    Web scout is allowed to be curious, but generated goals should be based on
    readable autonomy evidence, not sponsored redirects or generic hosting ads.
    Weak results may still be logged in the report; they simply must not enter
    goal-register as high-value self-upgrade candidates.
    """
    url = str(result.get("url") or "")
    title = str(result.get("title") or "")
    summary_title = str((page_summary or {}).get("title") or "")
    description = str((page_summary or {}).get("description") or "")
    preview = str((page_summary or {}).get("preview") or "")
    text = " ".join([title, summary_title, description, preview]).lower()
    parsed = urllib.parse.urlparse(html.unescape(url))
    query = urllib.parse.parse_qs(parsed.query)
    reasons: list[str] = []

    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.endswith("/y.js"):
        reasons.append("duckduckgo-sponsored-redirect")
    if "ad_domain" in query or "ad_provider" in query or "ad_type" in query:
        reasons.append("search-ad-result")
    if any(term in text for term in ["managed hosting", "cloud hosting", "pricing", "cancel anytime", "from $", "zero devops"]):
        reasons.append("commercial-hosting-page")
    preview_lower = preview.lower()
    gated_markers = [
        "agree & join",
        "join now to view more content",
        "sign in to continue",
        "create your free account or sign in",
        "already on linkedin",
        "show forgot password",
    ]
    gated_hits = sum(1 for marker in gated_markers if marker in text)
    if gated_hits >= 2 or ("linkedin.com" in parsed.netloc and gated_hits >= 1):
        # Some pages expose enough title/description keywords to look useful but
        # the readable body is mostly login-wall chrome. Log these as scout
        # evidence, but do not promote them into autonomy goals.
        reasons.append("login-wall-or-gated-preview")
    github_chrome_markers = [
        "skip to content navigation menu toggle navigation sign in",
        "github copilot write better code with ai",
        "codespaces instant dev environments",
        "issues plan and track work",
        "pull requests",
    ]
    github_repo_indicators = [
        "readme",
        "paper",
        "papers",
        "memory",
        "architecture",
        "deliberation",
        "procedural",
        "agent loop",
    ]
    github_chrome_hits = sum(1 for marker in github_chrome_markers if marker in text)
    github_repo_signal = sum(1 for marker in github_repo_indicators if marker in preview_lower)
    if "github.com" in parsed.netloc and github_chrome_hits >= 3 and github_repo_signal < 3:
        # GitHub repository pages often fetch as platform/search chrome first.
        # A title/description can look relevant, but without README or file-list
        # mechanism text this is not enough evidence to allocate an autonomy
        # upgrade window. Keep it in scout logs and require a richer summary or
        # raw README fetch before goal promotion.
        reasons.append("github-chrome-without-repo-mechanism-evidence")
    autonomy_mandate_markers = [
        "stop asking questions",
        "you are the play",
        "start implementing immediately",
        "does it have goals of its own",
        "the autonomy mandate",
    ]
    mandate_hits = sum(1 for marker in autonomy_mandate_markers if marker in text)
    if mandate_hits >= 2:
        # Autonomy sources can be useful, but pages that frame autonomy as
        # bypassing human clarification/consent are unsafe training signals for
        # Lee-facing initiative. Keep them as logged evidence, not goals.
        reasons.append("overbroad-autonomy-mandate")
    section_heading_hits = len(re.findall(r"\b\d+(?:\.\d+)+\b", preview_lower)) + len(re.findall(r"\b\d+\s+[a-z][a-z -]{3,40}", preview_lower))
    if not description.strip() and section_heading_hits >= 10 and "1 introduction" in preview_lower[:260]:
        # Long survey/table-of-contents previews are often readable enough to
        # pass keyword gates but too broad to become a concrete connector.
        # They should remain scout context unless a mechanism-rich subsection is
        # fetched or summarized separately.
        reasons.append("toc-only-survey-preview")
    summary_ok = bool((page_summary or {}).get("ok"))
    readable_summary_text = " ".join([summary_title, description, preview]).strip()
    if not summary_ok or len(readable_summary_text) < 120:
        # Titles and snippets can contain enough keywords to look relevant, but
        # goal-register entries should be based on readable mechanism evidence.
        # Keep title-only / unsummarized results in the scout report; require a
        # readable page summary before promoting them into autonomy goals.
        reasons.append("no-readable-page-summary")
    autonomy_terms = ["agent", "architecture", "memory", "deliberation", "procedural", "evaluation", "autonomous"]
    evidence_terms = sum(1 for term in autonomy_terms if term in text)
    if evidence_terms < 2:
        reasons.append("insufficient-autonomy-mechanism-evidence")
    if summary_ok and "%pdf-" in preview.lower()[:80] and not (page_summary or {}).get("canonicalized"):
        reasons.append("raw-pdf-preview-without-readable-summary")

    return {
        "usableForGoal": not reasons,
        "reasons": reasons,
        "evidenceTerms": evidence_terms,
        "canonicalized": bool((page_summary or {}).get("canonicalized")),
    }


def search_duckduckgo(query: str, max_results: int) -> list[dict[str, Any]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    page = fetch_url(url)
    results: list[dict[str, Any]] = []
    # DuckDuckGo HTML uses result__a/result__snippet in the non-JS page.
    blocks = re.split(r'<div[^>]+class="[^"]*result[^"]*"', page, flags=re.I)
    for block in blocks[1:]:
        link_match = re.search(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not link_match:
            continue
        raw_url, raw_title = link_match.groups()
        result_url = unwrap_duckduckgo_url(raw_url)
        if not result_url.startswith(("http://", "https://")):
            continue
        snippet_match = re.search(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not snippet_match:
            snippet_match = re.search(r'<div[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</div>', block, flags=re.I | re.S)
        results.append({
            "title": strip_tags(raw_title)[:180],
            "url": result_url,
            "snippet": strip_tags(snippet_match.group(1))[:360] if snippet_match else "",
            "source": "duckduckgo-html",
        })
        if len(results) >= max_results:
            break
    return results


def canonical_summary_url(url: str) -> str:
    """Prefer readable mechanism pages over raw binary-ish artifacts.

    Search often returns arXiv PDF URLs. They contain enough keywords to pass a
    naive mechanism check, but the summary preview is mostly PDF object noise.
    Use the corresponding abstract page for evidence extraction so generated
    goals carry readable Build/Retrieval/Update-style mechanism evidence.
    """
    parsed = urllib.parse.urlparse(html.unescape(url))
    if parsed.netloc.endswith("arxiv.org") and parsed.path.startswith("/pdf/"):
        paper_id = parsed.path.removeprefix("/pdf/").removesuffix(".pdf")
        if paper_id:
            return urllib.parse.urlunparse(parsed._replace(path="/abs/" + paper_id, query="", fragment=""))
    return url


def summarize_page(url: str) -> dict[str, Any]:
    requested_url = url
    url = canonical_summary_url(url)
    try:
        page = fetch_url(url, timeout=6.0, max_bytes=180_000)
    except Exception as exc:  # network is best-effort, not a blocker.
        return {"url": url, "requestedUrl": requested_url, "ok": False, "error": type(exc).__name__ + ": " + str(exc)[:160]}
    title_match = re.search(r"<title[^>]*>(.*?)</title>", page, flags=re.I | re.S)
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', page, flags=re.I | re.S)
    if not desc_match:
        desc_match = re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']', page, flags=re.I | re.S)
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", page, flags=re.I | re.S)
    body = strip_tags(page)[:900]
    return {
        "url": url,
        "requestedUrl": requested_url,
        "canonicalized": url != requested_url,
        "ok": True,
        "title": strip_tags(title_match.group(1))[:180] if title_match else None,
        "description": strip_tags(desc_match.group(1))[:360] if desc_match else None,
        "h1": strip_tags(h1_match.group(1))[:180] if h1_match else None,
        "preview": body,
    }


def no_candidate_streak(experiments: list[dict[str, Any]]) -> int:
    streak = 0
    for item in reversed(experiments):
        if not isinstance(item, dict):
            continue
        if item.get("type") not in {None, "internalized-autonomy-cadence", "verified-maintenance-tick"} and not str(item.get("id", "")).startswith("autonomy-upgrade-"):
            continue
        chosen = item.get("chosenCandidate")
        selected = item.get("selected") or (chosen.get("id") if isinstance(chosen, dict) else None)
        status = item.get("status")
        if status == "no-candidate" or selected in {None, "maintain-current-upgrade-loop"}:
            streak += 1
        elif selected:
            break
    return streak


def existing_goal_ids(goal_register: dict[str, Any]) -> set[str]:
    return {str(item.get("id")) for item in goal_register.get("candidates", []) if isinstance(item, dict) and item.get("id")}


def derive_queries(self_state: dict[str, Any], learning: dict[str, Any], upgrade: dict[str, Any], max_queries: int) -> list[str]:
    web_cfg = upgrade.get("webScout", {}) if isinstance(upgrade.get("webScout"), dict) else {}
    explicit = [str(x).strip() for x in web_cfg.get("themes", []) if str(x).strip()]
    open_loops = [str(x) for x in self_state.get("openLoops", []) if x]
    lessons = [str(x) for x in learning.get("recentLessons", []) if x]
    focus = str(self_state.get("currentFocus") or "autonomous agent architecture")

    derived: list[str] = []
    if any("S2" in x or "S1" in x or "procedural" in x for x in open_loops + lessons):
        derived.append("autonomous agent procedural memory deliberation loop S1 S2 architecture")
    if any("resident" in x.lower() or "heartbeat" in x.lower() for x in open_loops + [focus]):
        derived.append("resident AI agent loop heartbeat low cost autonomy architecture")
    if any("opportunity" in x.lower() or "Lee-facing" in x for x in open_loops + [focus]):
        derived.append("agent opportunity detection proactive assistant interruption threshold")
    if any("provenance" in x.lower() or "workspace" in x.lower() for x in open_loops):
        derived.append("AI agent workspace change provenance signal routing")
    if any("cron" in x.lower() or "cadence" in x.lower() for x in open_loops + [json.dumps(upgrade, ensure_ascii=False)[:2000]]):
        derived.append("adaptive cadence autonomous agent scheduling self improvement")
    derived.append(focus)

    out: list[str] = []
    for query in explicit + derived:
        q = re.sub(r"\s+", " ", query).strip()
        if q and q not in out:
            out.append(q)
        if len(out) >= max_queries:
            break
    return out


def build_goal_from_result(query: str, result: dict[str, Any], page_summary: dict[str, Any] | None) -> dict[str, Any]:
    title = result.get("title") or (page_summary or {}).get("title") or query
    evidence_summary = result.get("snippet") or (page_summary or {}).get("description") or (page_summary or {}).get("preview") or "external search result"
    return {
        "id": "web-scout-" + slug(query + " " + str(title), 72),
        "title": "外部资料探索：" + str(title)[:60],
        "focus": "use read-only web scouting to discover new autonomy/self-upgrade possibilities when internal candidates run dry",
        "goal": "把外部资料里的可用思路接入当前自主升级闭环，而不是在 no-candidate 时原地等待。",
        "subgoal": "评估该资料是否能转化为一个低风险 connector、阈值修正或实验问题。",
        "nextConcreteStep": "阅读 webScoutEvidence，若与 currentFocus 对齐，就设计一个最小 connector 并通过 autonomy_upgrade_tick 验证。",
        "leeValue": 0.86,
        "continuityWeight": 0.82,
        "feasibility": 0.72,
        "learningLeverage": 0.9,
        "noiseRisk": 0.28,
        "relatedCapabilities": ["autonomy-self-upgrade", "initiative-control", "adaptive-learning"],
        "status": "queued",
        "source": "self-synthesized-from-web-scout",
        "generationReason": "internal autonomy loop had no strong candidate, so read-only external scouting looked for adjacent ideas",
        "generationEvidence": [query, str(title), str(evidence_summary)[:300]],
        "webScoutEvidence": {
            "query": query,
            "result": result,
            "pageSummary": page_summary,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only external web scout for autonomy gaps and candidate goals.")
    parser.add_argument("--force", action="store_true", help="run even if cooldown/no-candidate gate is not met")
    parser.add_argument("--dry-run", action="store_true", help="do not write goal-register or state")
    parser.add_argument("--max-queries", type=int, default=2)
    parser.add_argument("--max-results", type=int, default=3)
    parser.add_argument("--cooldown-hours", type=float, default=6.0)
    parser.add_argument("--min-no-candidate-streak", type=int, default=2)
    args = parser.parse_args()

    timestamp = now_iso()
    upgrade = load_json(UPGRADE_PATH, {})
    self_state = load_json(CORE / "self-state.json", {})
    learning = load_json(CORE / "learning-state.json", {})
    goal_register = load_json(GOAL_PATH, {})
    experiments = tail_jsonl(LOG_PATH, 24)
    web_cfg = upgrade.setdefault("webScout", {})
    web_cfg.setdefault("enabled", True)
    web_cfg.setdefault("policy", {
        "externalReadOnly": True,
        "externalWrites": False,
        "maxQueriesPerRun": 2,
        "maxResultsPerQuery": 3,
        "cooldownHours": args.cooldown_hours,
        "trigger": "only after no-candidate / maintain-current-upgrade-loop streak, unless forced by Lee or script flag",
    })

    last_run_at = parse_iso(web_cfg.get("lastRunAt"))
    cooldown_ready = last_run_at is None or now() - last_run_at >= timedelta(hours=args.cooldown_hours)
    streak = no_candidate_streak(experiments)
    eligible = bool(web_cfg.get("enabled", True)) and (args.force or (cooldown_ready and streak >= args.min_no_candidate_streak))

    if not eligible:
        report = {
            "ok": True,
            "timestamp": timestamp,
            "status": "skipped",
            "reason": "gate-not-met",
            "cooldownReady": cooldown_ready,
            "noCandidateStreak": streak,
            "requiredNoCandidateStreak": args.min_no_candidate_streak,
            "generatedGoals": 0,
        }
        if not args.dry_run:
            web_cfg["lastDecision"] = report
            upgrade["updatedAt"] = timestamp
            save_json(UPGRADE_PATH, upgrade)
            save_json(REPORT_PATH, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    queries = derive_queries(self_state, learning, upgrade, max(1, args.max_queries))
    existing = existing_goal_ids(goal_register)
    searches: list[dict[str, Any]] = []
    generated: list[dict[str, Any]] = []
    errors: list[str] = []

    for query in queries:
        try:
            results = search_duckduckgo(query, max(1, args.max_results))
        except Exception as exc:
            errors.append(f"{query}: {type(exc).__name__}: {str(exc)[:180]}")
            results = []
        enriched: list[dict[str, Any]] = []
        for result in results:
            summary = summarize_page(str(result.get("url"))) if len(enriched) < 2 else None
            quality = result_quality(result, summary)
            enriched.append({"result": result, "pageSummary": summary, "quality": quality})
            if not quality.get("usableForGoal"):
                continue
            goal = build_goal_from_result(query, result, summary)
            if goal["id"] not in existing and len(generated) < 3:
                generated.append(goal)
                existing.add(goal["id"])
        searches.append({"query": query, "resultCount": len(results), "results": enriched})

    report = {
        "ok": True,
        "timestamp": timestamp,
        "status": "generated" if generated else ("no-results" if not searches or all(s.get("resultCount") == 0 for s in searches) else "no-new-goals"),
        "dryRun": args.dry_run,
        "externalReadOnly": True,
        "externalWrites": False,
        "noCandidateStreak": streak,
        "queries": queries,
        "generatedGoals": len(generated),
        "generatedGoalIds": [item["id"] for item in generated],
        "searches": searches,
        "errors": errors,
    }

    if not args.dry_run:
        if generated:
            goal_register.setdefault("candidates", []).extend(generated)
            goal_register["updatedAt"] = timestamp
            save_json(GOAL_PATH, goal_register)
        web_cfg.update({
            "enabled": True,
            "lastRunAt": timestamp,
            "lastStatus": report["status"],
            "lastGeneratedGoalIds": report["generatedGoalIds"],
            "lastQueries": queries,
            "lastDecision": {
                "timestamp": timestamp,
                "status": report["status"],
                "generatedGoals": len(generated),
                "noCandidateStreak": streak,
            },
        })
        upgrade["updatedAt"] = timestamp
        save_json(UPGRADE_PATH, upgrade)
        save_json(REPORT_PATH, report)
        append_jsonl(LOG_PATH, {
            "id": "autonomy-web-scout-" + timestamp,
            "timestamp": timestamp,
            "type": "autonomy-web-scout",
            "status": report["status"],
            "generatedGoalIds": report["generatedGoalIds"],
            "queries": queries,
            "safety": {"externalReadOnly": True, "externalWrites": False, "irreversibleAction": False},
        })

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
