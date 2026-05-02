from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
CANVAS_ROOT = Path.home() / ".openclaw" / "canvas"
DOC_ID = "local-evolution-agent_companion_status"
CANVAS_DOC = CANVAS_ROOT / "documents" / DOC_ID / "index.html"
HTML_OUT = STATE / "app_shell_dashboard.html"
JSON_OUT = STATE / "app_shell_status.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def pick_runtime_actions(runtime: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    actions = []
    for item in runtime.get("actions", []) or []:
        if not isinstance(item, dict):
            continue
        actions.append({"action": item.get("action"), "rc": item.get("rc")})
    return actions[-limit:]


def status_level(ok: bool | None) -> str:
    if ok is True:
        return "ok"
    if ok is False:
        return "warn"
    return "unknown"


def build_status() -> dict[str, Any]:
    resource = load(CORE / "resource-state.json")
    runtime = load(STATE / "resident_runtime.json")
    consistency = load(STATE / "consistency_report.json")
    multi = load(CORE / "multi-agent-mode.json")
    voice = load(STATE / "voice_wake_plan.json")
    voice_calibration = load(STATE / "voice_calibration_status.json")
    voice_indicator = load(STATE / "voice_listening_indicator.json")
    voice_runner = load(STATE / "voice_manual_calibration_runner_status.json")
    app_plan = load(STATE / "app_productization_plan.json")
    embodied = load(STATE / "embodied_intelligence_roadmap.json")
    organ = load(STATE / "organ_link_graph.json")
    gateway = load(STATE / "gateway_watchdog_status.json")
    ocr = load(STATE / "screen_ocr_availability_probe.json")
    controls = load(STATE / "app_control_state.json")
    resource_gate = load(STATE / "desktop_wrapper_resource_budget_gate_status.json")
    resource_trend = load(STATE / "desktop_wrapper_resource_trend_gate_status.json")
    resource_response = load(STATE / "desktop_wrapper_resource_pressure_response_status.json")
    resource_recovery = load(STATE / "desktop_wrapper_resource_recovery_gate_status.json")
    resource_profile_sync = load(STATE / "desktop_wrapper_resource_profile_sync_status.json")
    resource_gate_consistency = load(STATE / "desktop_wrapper_resource_gate_consistency_audit_status.json")
    resource_serialized_refresh = load(STATE / "desktop_wrapper_resource_gate_serialized_refresh_status.json")
    sensitive_preflight = load(STATE / "desktop_wrapper_sensitive_action_resource_preflight_status.json")
    resource_action_ticket = load(STATE / "desktop_wrapper_resource_action_clearance_ticket_status.json")
    resource_action_verifier = load(STATE / "desktop_wrapper_resource_action_clearance_verifier_status.json")
    resource_guarded_wrapper = load(STATE / "desktop_wrapper_resource_guarded_action_wrapper_status.json")
    resource_guard_map = load(STATE / "desktop_wrapper_resource_guard_integration_map_status.json")
    resource_guard_scorecard = load(STATE / "desktop_wrapper_resource_guard_enforcement_scorecard_status.json")
    external_action_guard = load(STATE / "desktop_wrapper_external_action_guard_status.json")
    quiet_hours_gate = load(STATE / "desktop_wrapper_quiet_hours_action_gate_status.json")
    deferred_organ_queue = load(STATE / "desktop_wrapper_deferred_organ_calibration_queue_status.json")
    organ_resume_packet = load(STATE / "desktop_wrapper_organ_calibration_resume_packet_status.json")
    organ_resume_audit = load(STATE / "desktop_wrapper_organ_calibration_resume_readiness_audit_status.json")
    quiet_progress_batcher = load(STATE / "desktop_wrapper_quiet_hours_progress_batcher_status.json")
    self_funding_value = load(STATE / "desktop_wrapper_self_funding_value_ledger_status.json")
    self_funding_offer = load(STATE / "desktop_wrapper_self_funding_offer_draft_status.json")
    self_funding_demo = load(STATE / "desktop_wrapper_self_funding_demo_pack_status.json")
    self_funding_privacy = load(STATE / "desktop_wrapper_self_funding_demo_privacy_verifier_status.json")
    self_funding_roi = load(STATE / "desktop_wrapper_self_funding_roi_calculator_status.json")
    self_funding_runbook = load(STATE / "desktop_wrapper_self_funding_buyer_runbook_status.json")
    self_funding_sample = load(STATE / "desktop_wrapper_self_funding_sample_workflow_demo_status.json")
    self_funding_checklist = load(STATE / "desktop_wrapper_self_funding_pilot_checklist_status.json")
    usage_window_gate = load(STATE / "desktop_wrapper_usage_window_pressure_gate_status.json")
    resource_safe_queue = load(STATE / "desktop_wrapper_resource_safe_connector_queue_status.json")
    resource_policy_summary = load(STATE / "desktop_wrapper_resource_policy_state_summary_status.json")
    physical_allowlist = load(STATE / "physical_actuation_allowlist.json")
    physical_status = load(STATE / "physical_actuation_simulator_status.json")
    service_health = load(STATE / "service_health_status.json")
    service_control = load(STATE / "service_control_schema.json")
    service_control_state = load(STATE / "service_control_state.json")
    desktop_wrapper = load(STATE / "desktop_app_wrapper_status.json")
    wrapper_control_preview = load(STATE / "desktop_wrapper_control_preview_status.json")
    diagnostics = load(STATE / "desktop_wrapper_diagnostics_status.json")
    tray_contract = load(STATE / "desktop_wrapper_tray_contract_status.json")
    tray_readiness = load(STATE / "desktop_wrapper_tray_readiness_status.json")
    packaging_preflight = load(STATE / "desktop_wrapper_packaging_preflight_status.json")
    electron_fallback = load(STATE / "desktop_wrapper_electron_fallback_status.json")
    test_matrix = load(STATE / "desktop_wrapper_test_matrix_status.json")
    docs_status = load(STATE / "desktop_wrapper_docs_status.json")
    audit_view = load(STATE / "desktop_wrapper_audit_view_status.json")
    audit_compaction = load(STATE / "desktop_wrapper_audit_log_compaction_plan_status.json")
    audit_tail_fingerprint = load(STATE / "desktop_wrapper_audit_log_tail_fingerprint_status.json")
    audit_streaming_manifest = load(STATE / "desktop_wrapper_audit_log_streaming_manifest_status.json")
    home_summary = load(STATE / "desktop_wrapper_home_summary.json")
    home_routes = load(STATE / "desktop_wrapper_home_routes_status.json")
    recovery_drill = load(STATE / "desktop_wrapper_service_recovery_drill_status.json")
    multi_agent_board = load(STATE / "desktop_wrapper_multi_agent_board_status.json")
    physical_matrix = load(STATE / "desktop_wrapper_physical_scenario_matrix_status.json")
    next_queue = load(STATE / "desktop_wrapper_next_connector_queue_status.json")
    voice_body = load(STATE / "desktop_wrapper_voice_body_readiness_status.json")
    voice_wake_boundary = load(STATE / "desktop_wrapper_voice_wake_boundary_status.json")
    voice_vad_dry_run = load(STATE / "desktop_wrapper_voice_vad_measurement_dry_run_status.json")
    voice_vad_runner = load(STATE / "desktop_wrapper_voice_vad_measurement_runner_status.json")
    voice_vad_baseline = load(STATE / "desktop_wrapper_voice_vad_baseline_evaluator_status.json")
    voice_spoken_wake = load(STATE / "desktop_wrapper_voice_spoken_wake_boundary_status.json")
    voice_wake_engine = load(STATE / "desktop_wrapper_voice_wake_engine_readiness_status.json")
    voice_spoken_runner = load(STATE / "desktop_wrapper_voice_spoken_wake_calibration_runner_status.json")
    voice_phrase_retention = load(STATE / "desktop_wrapper_voice_phrase_retention_verifier_status.json")
    voice_phrase_match = load(STATE / "desktop_wrapper_voice_phrase_match_verifier_status.json")
    voice_wake_e2e = load(STATE / "desktop_wrapper_voice_wake_end_to_end_gate_status.json")
    handoff_rules = load(STATE / "desktop_wrapper_multi_agent_handoff_rules_status.json")
    approval_gates = load(STATE / "desktop_wrapper_approval_gate_register_status.json")
    release_readiness = load(STATE / "desktop_wrapper_release_readiness_status.json")
    morning_digest = load(STATE / "desktop_wrapper_morning_progress_digest_status.json")
    decision_packet = load(STATE / "desktop_wrapper_decision_boundary_packet_status.json")
    body_indicators = load(STATE / "desktop_wrapper_body_indicator_status.json")
    body_control_contract = load(STATE / "desktop_wrapper_body_control_contract_status.json")
    camera_single_frame = load(STATE / "desktop_wrapper_camera_single_frame_dry_run_status.json")
    camera_single_frame_capture = load(STATE / "desktop_wrapper_camera_single_frame_capture_status.json")
    camera_privacy = load(STATE / "desktop_wrapper_camera_privacy_verifier_status.json")
    camera_visual_boundary = load(STATE / "desktop_wrapper_camera_visual_analysis_boundary_status.json")
    camera_visual_semantics = load(STATE / "desktop_wrapper_camera_visual_semantic_extractor_status.json")
    electron_scaffold = load(STATE / "desktop_electron_scaffold_status.json")
    electron_menu = load(STATE / "desktop_electron_menu_status.json")
    electron_tray = load(STATE / "desktop_electron_tray_status.json")
    electron_autostart = load(STATE / "desktop_electron_autostart_control_status.json")
    electron_autostart_readiness = load(STATE / "desktop_electron_autostart_readiness_status.json")
    electron_autostart_rollback = load(STATE / "desktop_electron_autostart_rollback_drill_status.json")

    resource_pressure = resource.get("resourcePressure", {}) if isinstance(resource.get("resourcePressure"), dict) else {}
    gpus = resource.get("gpus", []) if isinstance(resource.get("gpus"), list) else []
    gpu = gpus[0] if gpus and isinstance(gpus[0], dict) else {}
    memory = resource.get("memory", {}) if isinstance(resource.get("memory"), dict) else {}
    disks = resource.get("disks", []) if isinstance(resource.get("disks"), list) else []
    workspace_disk = next((d for d in disks if isinstance(d, dict) and d.get("isWorkspaceDrive")), disks[0] if disks and isinstance(disks[0], dict) else {})
    consistency_ok = consistency.get("status") == "ok" and not consistency.get("errors") and not consistency.get("warnings")
    runtime_ok = runtime.get("status") == "ok"
    gateway_ok = gateway.get("gatewayReachableBefore") is True or gateway.get("status") == "ok"
    camera_capture_payload = camera_single_frame_capture.get("capture") if isinstance(camera_single_frame_capture.get("capture"), dict) else {}
    camera_capture_parsed = camera_capture_payload.get("parsed") if isinstance(camera_capture_payload.get("parsed"), dict) else {}

    cards = [
        {
            "id": "resident",
            "title": "Resident",
            "level": status_level(runtime_ok),
            "summary": f"pulse {runtime.get('pulseIndex', '?')} · {runtime.get('status', 'unknown')} · {runtime.get('timestamp', 'n/a')}",
        },
        {
            "id": "resource",
            "title": "Resource / VRAM/RAM/Disk",
            "level": resource_pressure.get("level", "unknown"),
            "summary": f"{gpu.get('name', 'GPU')} VRAM {gpu.get('memoryUsedMiB', '?')}/{gpu.get('memoryTotalMiB', '?')} MiB · RAM {memory.get('usedMiB', '?')}/{memory.get('totalMiB', '?')} MiB · {workspace_disk.get('root', 'disk')} free {workspace_disk.get('freeMiB', '?')} MiB · {resource_pressure.get('recommendedMode', 'n/a')}",
        },
        {
            "id": "resource-budget-gate",
            "title": "Resource budget gate",
            "level": "ok" if resource_gate.get("status") == "ready" else "warn" if resource_gate.get("status") == "warning" else resource_gate.get("status", "unknown"),
            "summary": f"mode={resource_gate.get('recommendedMode', 'n/a')} · gpuHeavy={resource_gate.get('allowedWorkModes', {}).get('gpuHeavy', False)} · warnings={len(resource_gate.get('warnings', []) or [])} · blocked={len(resource_gate.get('blocked', []) or [])}",
        },
        {
            "id": "resource-trend-gate",
            "title": "Resource trend gate",
            "level": "ok" if resource_trend.get("status") == "ready" else "warn" if resource_trend.get("status") == "warning" else resource_trend.get("status", "unknown"),
            "summary": f"mode={resource_trend.get('recommendedMode', 'n/a')} · memTrend={resource_trend.get('trends', {}).get('memory', {}).get('direction', 'n/a')} · warnings={len(resource_trend.get('warnings', []) or [])} · blocked={len(resource_trend.get('blocked', []) or [])}",
        },
        {
            "id": "resource-pressure-response",
            "title": "Resource pressure response",
            "level": "ok" if resource_response.get("status") == "ready" else "warn" if resource_response.get("status") == "warning" else resource_response.get("status", "unknown"),
            "summary": f"profile={resource_response.get('profile', 'n/a')} · suppress={len(resource_response.get('recommendations', {}).get('suppressed', []) or [])} · unsafe={len(resource_response.get('unsafeActive', []) or [])}",
        },
        {
            "id": "resource-recovery-gate",
            "title": "Resource recovery gate",
            "level": "ok" if resource_recovery.get("status") == "ready" else resource_recovery.get("status", "unknown"),
            "summary": f"profile={resource_recovery.get('recommendedProfile', 'n/a')} · okStreak={resource_recovery.get('recovery', {}).get('okStreak', 'n/a')} · stable={resource_recovery.get('recovery', {}).get('stableRecovered', False)}",
        },
        {
            "id": "resource-profile-sync",
            "title": "Resource profile sync",
            "level": "ok" if resource_profile_sync.get("status") == "ready" else resource_profile_sync.get("status", "unknown"),
            "summary": f"effective={resource_profile_sync.get('effectiveProfile', 'n/a')} · reason={resource_profile_sync.get('reason', 'n/a')} · warnings={len(resource_profile_sync.get('warnings', []) or [])}",
        },
        {
            "id": "resource-gate-consistency",
            "title": "Resource gate consistency",
            "level": "warn" if resource_gate_consistency.get("requiresRerunOrder") else "ok" if resource_gate_consistency.get("status") == "ready" else resource_gate_consistency.get("status", "unknown"),
            "summary": f"skew={resource_gate_consistency.get('timestampSkewSeconds', 'n/a')}s · mismatches={len(resource_gate_consistency.get('inconsistencies', []) or [])} · serialize={resource_gate_consistency.get('requiresRerunOrder', False)}",
        },
        {
            "id": "resource-serialized-refresh",
            "title": "Resource serialized refresh",
            "level": "ok" if resource_serialized_refresh.get("status") == "ready" else resource_serialized_refresh.get("status", "unknown"),
            "summary": f"steps={len(resource_serialized_refresh.get('steps', []) or [])} · profile={resource_serialized_refresh.get('final', {}).get('effectiveProfile', 'n/a')} · mismatches={len(resource_serialized_refresh.get('final', {}).get('inconsistencies', []) or [])}",
        },
        {
            "id": "sensitive-resource-preflight",
            "title": "Sensitive resource preflight",
            "level": "ok" if sensitive_preflight.get("status") == "ready" else sensitive_preflight.get("status", "unknown"),
            "summary": f"fresh={sensitive_preflight.get('freshness', {}).get('fresh', False)} · allowed={sensitive_preflight.get('summary', {}).get('allowedNowCount', 0)} · blocked={sensitive_preflight.get('summary', {}).get('blockedCount', 0)}",
        },
        {
            "id": "resource-action-ticket",
            "title": "Resource action clearance ticket",
            "level": "ok" if resource_action_ticket.get("status") == "ready" and resource_action_ticket.get("valid") else resource_action_ticket.get("status", "unknown"),
            "summary": f"valid={resource_action_ticket.get('valid', False)} · profile={resource_action_ticket.get('profile', 'n/a')} · allowed={len(resource_action_ticket.get('allowedWorkClasses', []) or [])} · denied={resource_action_ticket.get('deniedWorkClassCount', 'n/a')}",
        },
        {
            "id": "resource-action-verifier",
            "title": "Resource action verifier",
            "level": "ok" if resource_action_verifier.get("status") == "ready" and resource_action_verifier.get("selfTest", {}).get("paidApiDenied") else resource_action_verifier.get("status", "unknown"),
            "summary": f"requested={resource_action_verifier.get('requested', {}).get('requestedClass', 'n/a')} · allowed={resource_action_verifier.get('requested', {}).get('allowedNow', False)} · paidDenied={resource_action_verifier.get('selfTest', {}).get('paidApiDenied', False)}",
        },
        {
            "id": "resource-guarded-wrapper",
            "title": "Resource guarded action wrapper",
            "level": "ok" if resource_guarded_wrapper.get("status") == "ready" and resource_guarded_wrapper.get("selfTest", {}).get("paidApiDenied") else resource_guarded_wrapper.get("status", "unknown"),
            "summary": f"class={resource_guarded_wrapper.get('requested', {}).get('actionClass', 'n/a')} · allowed={resource_guarded_wrapper.get('requested', {}).get('allowedByTicket', False)} · dryRun={resource_guarded_wrapper.get('safety', {}).get('dryRunOnly', True)}",
        },
        {
            "id": "resource-guard-map",
            "title": "Resource guard integration map",
            "level": "ok" if resource_guard_map.get("status") == "ready" and not resource_guard_map.get("mismatches") else resource_guard_map.get("status", "unknown"),
            "summary": f"mapped={resource_guard_map.get('integrationCount', 0)} · allowed={resource_guard_map.get('allowedCount', 0)} · denied={resource_guard_map.get('deniedCount', 0)} · leaks={len(resource_guard_map.get('sensitiveLeaks', []) or [])}",
        },
        {
            "id": "resource-guard-scorecard",
            "title": "Resource guard enforcement scorecard",
            "level": "ok" if resource_guard_scorecard.get("status") == "ready" else resource_guard_scorecard.get("status", "unknown"),
            "summary": f"coverage={resource_guard_scorecard.get('hookedCount', 0)}/{resource_guard_scorecard.get('totalCount', 0)} · score={resource_guard_scorecard.get('score', 'n/a')} · missing={len(resource_guard_scorecard.get('missing', []) or [])}",
        },
        {
            "id": "external-action-guard",
            "title": "External / paid action guard",
            "level": "ok" if external_action_guard.get("status") == "ready" and not external_action_guard.get("mismatches") else external_action_guard.get("status", "unknown"),
            "summary": f"decisions={external_action_guard.get('decisionCount', 0)} · blockedExternal={external_action_guard.get('blockedExternalCount', 0)} · allowed={external_action_guard.get('allowedCount', 0)}",
        },
        {
            "id": "quiet-hours-action-gate",
            "title": "Quiet-hours action gate",
            "level": "ok" if quiet_hours_gate.get("status") == "ready" else quiet_hours_gate.get("status", "unknown"),
            "summary": f"quiet={quiet_hours_gate.get('quietHours', False)} · selected={quiet_hours_gate.get('selected', 'none')} · suppressed={len(quiet_hours_gate.get('suppressions', []) or [])}",
        },
        {
            "id": "deferred-organ-queue",
            "title": "Deferred organ calibration queue",
            "level": "ok" if deferred_organ_queue.get("status") == "ready" else deferred_organ_queue.get("status", "unknown"),
            "summary": f"next={deferred_organ_queue.get('selectedWhenAllowed', 'none')} · deferred={deferred_organ_queue.get('deferredCount', 0)} · executable={deferred_organ_queue.get('executableNowCount', 0)}",
        },
        {
            "id": "organ-resume-packet",
            "title": "Organ calibration resume packet",
            "level": "ok" if organ_resume_packet.get("status") == "ready" else organ_resume_packet.get("status", "unknown"),
            "summary": f"when={organ_resume_packet.get('resumeWhen', 'n/a')} · executable={organ_resume_packet.get('executableNow', False)} · selected={organ_resume_packet.get('readiness', {}).get('selectedDeferredItem', 'none')}",
        },
        {
            "id": "organ-resume-audit",
            "title": "Organ resume readiness audit",
            "level": "ok" if organ_resume_audit.get("status") == "ready" else organ_resume_audit.get("status", "unknown"),
            "summary": f"quiet={organ_resume_audit.get('quietHours', False)} · failed={len(organ_resume_audit.get('failed', []) or [])} · rec={organ_resume_audit.get('recommendation', 'n/a')}",
        },
        {
            "id": "quiet-progress-batcher",
            "title": "Quiet-hours progress batcher",
            "level": "ok" if quiet_progress_batcher.get("status") == "ready" else quiet_progress_batcher.get("status", "unknown"),
            "summary": f"quiet={quiet_progress_batcher.get('quietHours', False)} · reportNow={quiet_progress_batcher.get('shouldReportNow', False)} · batched={quiet_progress_batcher.get('batchCount', 0)}",
        },
        {
            "id": "self-funding-value-ledger",
            "title": "Self-funding value ledger",
            "level": "ok" if self_funding_value.get("status") == "ready" else self_funding_value.get("status", "unknown"),
            "summary": f"entries={self_funding_value.get('entryCount', 0)} · hours={self_funding_value.get('totalEstimatedHours', 0)} · weekLeft={self_funding_value.get('quota', {}).get('weeklyLeftPercent', 'n/a')}%",
        },
        {
            "id": "self-funding-offer-draft",
            "title": "Self-funding offer draft",
            "level": "ok" if self_funding_offer.get("status") == "ready" else self_funding_offer.get("status", "unknown"),
            "summary": f"title={self_funding_offer.get('offerTitle', 'n/a')} · prices={self_funding_offer.get('pricingHypothesisCount', 0)} · localOnly={self_funding_offer.get('safety', {}).get('localDraftOnly', False)}",
        },
        {
            "id": "self-funding-demo-pack",
            "title": "Self-funding demo pack",
            "level": "ok" if self_funding_demo.get("status") == "ready" else self_funding_demo.get("status", "unknown"),
            "summary": f"cards={len(self_funding_demo.get('demoCards', []) or [])} · assets={len(self_funding_demo.get('assets', []) or [])} · localOnly={self_funding_demo.get('safety', {}).get('localDraftOnly', False)}",
        },
        {
            "id": "self-funding-demo-privacy",
            "title": "Self-funding demo privacy verifier",
            "level": "ok" if self_funding_privacy.get("status") == "passed" else self_funding_privacy.get("status", "unknown"),
            "summary": f"files={self_funding_privacy.get('filesScanned', 0)} · findings={self_funding_privacy.get('totalFindings', 0)} · missing={len(self_funding_privacy.get('missing', []) or [])}",
        },
        {
            "id": "self-funding-roi",
            "title": "Self-funding ROI calculator",
            "level": "ok" if self_funding_roi.get("status") == "ready" else self_funding_roi.get("status", "unknown"),
            "summary": f"target=AUD ${self_funding_roi.get('targetMonthlyQuotaBudgetAud', 0)} · best={self_funding_roi.get('bestScenarioId', 'n/a')} · scenarios={len(self_funding_roi.get('scenarios', []) or [])}",
        },
        {
            "id": "self-funding-buyer-runbook",
            "title": "Self-funding buyer runbook",
            "level": "ok" if self_funding_runbook.get("status") == "ready" else self_funding_runbook.get("status", "unknown"),
            "summary": f"pilot={self_funding_runbook.get('selectedPilot', 'n/a')} · sections={len(self_funding_runbook.get('sections', []) or [])} · localOnly={self_funding_runbook.get('safety', {}).get('localDraftOnly', False)}",
        },
        {
            "id": "self-funding-sample-workflow",
            "title": "Self-funding sample workflow",
            "level": "ok" if self_funding_sample.get("status") == "ready" else self_funding_sample.get("status", "unknown"),
            "summary": f"pilot={self_funding_sample.get('selectedPilot', 'n/a')} · inputs={len(self_funding_sample.get('inputItems', []) or [])} · generated={self_funding_sample.get('safety', {}).get('generatedSampleOnly', False)}",
        },
        {
            "id": "self-funding-pilot-checklist",
            "title": "Self-funding pilot checklist",
            "level": "ok" if self_funding_checklist.get("status") == "ready" else self_funding_checklist.get("status", "unknown"),
            "summary": f"pilot={self_funding_checklist.get('selectedPilot', 'n/a')} · gates={len(self_funding_checklist.get('goNoGoGates', []) or [])} · privacy={self_funding_checklist.get('readiness', {}).get('privacyPassed', False)}",
        },
        {
            "id": "usage-window-pressure",
            "title": "Usage / context pressure gate",
            "level": "ok" if usage_window_gate.get("status") == "ready" else usage_window_gate.get("status", "unknown"),
            "summary": f"mode={usage_window_gate.get('decision', {}).get('mode', 'n/a')} · week={usage_window_gate.get('quota', {}).get('weeklyLeftPercent', 'n/a')}% · ctx={usage_window_gate.get('quota', {}).get('contextUsedPercentApprox', 'n/a')}%",
        },
        {
            "id": "resource-safe-queue",
            "title": "Resource-safe connector queue",
            "level": "ok" if resource_safe_queue.get("status") == "ready" else resource_safe_queue.get("status", "unknown"),
            "summary": f"selected={resource_safe_queue.get('selected', {}).get('id', 'none') if isinstance(resource_safe_queue.get('selected'), dict) else 'none'} · profile={resource_safe_queue.get('profile', 'n/a')} · ranked={len(resource_safe_queue.get('ranked', []) or [])}",
        },
        {
            "id": "resource-policy-summary",
            "title": "Resource policy summary",
            "level": "ok" if resource_policy_summary.get("status") == "ready" else resource_policy_summary.get("status", "unknown"),
            "summary": f"profile={resource_policy_summary.get('profile', 'n/a')} · selected={resource_policy_summary.get('selectedConnector', 'none')} · warnings={len(resource_policy_summary.get('warnings', []) or [])}",
        },
        {
            "id": "audit-compaction-plan",
            "title": "Audit compaction plan",
            "level": "ok" if audit_compaction.get("status") == "ready" else audit_compaction.get("status", "unknown"),
            "summary": f"candidates={audit_compaction.get('candidateCount', 0)} · size={audit_compaction.get('totalCandidateMiB', 0)} MiB · proposalOnly={audit_compaction.get('safety', {}).get('proposalOnly', False)}",
        },
        {
            "id": "audit-tail-fingerprint",
            "title": "Audit tail fingerprint",
            "level": "ok" if audit_tail_fingerprint.get("status") == "ready" else audit_tail_fingerprint.get("status", "unknown"),
            "summary": f"files={audit_tail_fingerprint.get('fingerprintCount', 0)} · rawTail={audit_tail_fingerprint.get('safety', {}).get('storesRawTailContent', True)} · fullRead={audit_tail_fingerprint.get('safety', {}).get('fullFileRead', True)}",
        },
        {
            "id": "audit-streaming-manifest",
            "title": "Audit streaming manifest",
            "level": "ok" if audit_streaming_manifest.get("status") == "ready" else audit_streaming_manifest.get("status", "unknown"),
            "summary": f"files={audit_streaming_manifest.get('entryCount', 0)} · streamed={audit_streaming_manifest.get('totalStreamedBytes', 0)} bytes · mutated={audit_streaming_manifest.get('safety', {}).get('deletesFiles', True)}",
        },
        {
            "id": "multi-agent",
            "title": "Multi-agent",
            "level": status_level(bool(multi.get("enabled"))),
            "summary": f"{len(multi.get('roles', []) or [])} roles · main persona owns judgment",
        },
        {
            "id": "voice",
            "title": "Voice wake",
            "level": "warn" if not voice.get("enabled") else "ok",
            "summary": voice.get("reason") or voice.get("mode") or "unknown",
        },
        {
            "id": "voice-calibration",
            "title": "Voice calibration",
            "level": "ok" if voice_calibration.get("status") == "ready" and not voice_indicator.get("recordingNow") else "warn",
            "summary": f"{voice_calibration.get('mode', 'missing')} · inputs={voice_calibration.get('deviceEnumeration', {}).get('inputCount', 'n/a') if isinstance(voice_calibration.get('deviceEnumeration'), dict) else 'n/a'} · recordingNow={voice_indicator.get('recordingNow', False)} · last={voice_runner.get('status', 'n/a')}",
        },
        {
            "id": "gateway",
            "title": "Gateway watchdog",
            "level": status_level(gateway_ok) if gateway else "unknown",
            "summary": gateway.get("status", "not yet persistent") if gateway else "watchdog script exists; scheduled task needs approval",
        },
        {
            "id": "consistency",
            "title": "Consistency",
            "level": status_level(consistency_ok),
            "summary": f"{len(consistency.get('errors', []) or [])} errors · {len(consistency.get('warnings', []) or [])} warnings",
        },
        {
            "id": "app",
            "title": "App path",
            "level": "ok" if app_plan.get("status") else "unknown",
            "summary": app_plan.get("maturityAssessment", {}).get("level", "advanced-prototype"),
        },
        {
            "id": "embodied",
            "title": "Embodiment",
            "level": "ok" if embodied.get("status") else "unknown",
            "summary": embodied.get("currentLevel", {}).get("name", "desktop embodied prototype"),
        },
        {
            "id": "ocr",
            "title": "Screen OCR",
            "level": "ok" if ocr.get("ocrAvailable") else "warn",
            "summary": ocr.get("reason", "not probed"),
        },
        {
            "id": "controls",
            "title": "Permission controls",
            "level": "ok" if controls.get("status") == "ready" else "unknown",
            "summary": f"{len(controls.get('enabledControls', []) or [])} enabled · {len(controls.get('dryRunControls', []) or [])} dry-run · {len(controls.get('confirmationRequired', []) or [])} confirmation-gated",
        },
        {
            "id": "physical",
            "title": "Physical actuation",
            "level": "ok" if physical_allowlist.get("status") else "unknown",
            "summary": f"{len(physical_allowlist.get('devices', []) or [])} allowlisted simulator targets · last {physical_status.get('status', 'n/a')} · realDeviceCalled={physical_status.get('realDeviceCalled', False)}",
        },
        {
            "id": "service-health",
            "title": "Service health",
            "level": service_health.get("status", "unknown"),
            "summary": f"gateway={service_health.get('gatewayConnectivityOk', 'n/a')} · watchdog={service_health.get('watchdogLastStatusOk', 'n/a')} · missing={len(service_health.get('missingRequiredTasks', []) or [])}",
        },
        {
            "id": "service-controls",
            "title": "Service controls",
            "level": "ok" if service_control.get("status") == "ready" else "unknown",
            "summary": f"{len(service_control.get('safeActions', {}) or {})} safe previews · blocked last={service_control_state.get('action', 'n/a')}:{service_control_state.get('status', 'n/a')}",
        },
        {
            "id": "desktop-wrapper",
            "title": "Desktop wrapper",
            "level": "ok" if desktop_wrapper.get("status") == "ready" else desktop_wrapper.get("status", "unknown"),
            "summary": f"{desktop_wrapper.get('mode', 'missing')} · cards={desktop_wrapper.get('appShellStatus', {}).get('cardCount', 'n/a') if isinstance(desktop_wrapper.get('appShellStatus'), dict) else 'n/a'} · deps=0",
        },
        {
            "id": "wrapper-controls",
            "title": "Wrapper controls",
            "level": "ok" if wrapper_control_preview.get("status") in {"ready", "previewed", "requires-gate"} else wrapper_control_preview.get("status", "unknown"),
            "summary": f"{wrapper_control_preview.get('event', wrapper_control_preview.get('mode', 'missing'))} · mutates={wrapper_control_preview.get('mutatesAppControlState', False)} · sensitive={wrapper_control_preview.get('executesSensitiveAction', False)}",
        },
        {
            "id": "control-endpoint",
            "title": "Control endpoint",
            "level": "ok" if desktop_wrapper.get("controlEndpoint", {}).get("status") in {"ready", "passed"} else desktop_wrapper.get("controlEndpoint", {}).get("status", "unknown") if isinstance(desktop_wrapper.get("controlEndpoint"), dict) else "unknown",
            "summary": f"{desktop_wrapper.get('controlEndpoint', {}).get('mode', 'missing') if isinstance(desktop_wrapper.get('controlEndpoint'), dict) else 'missing'} · mutates={desktop_wrapper.get('controlEndpoint', {}).get('mutatesAppControlState', False) if isinstance(desktop_wrapper.get('controlEndpoint'), dict) else False}",
        },
        {
            "id": "diagnostics",
            "title": "Diagnostics export",
            "level": diagnostics.get("status", "unknown"),
            "summary": f"{diagnostics.get('fileCount', 0)} files · warnings={diagnostics.get('warningCount', 'n/a')} · localOnly={diagnostics.get('privacy', {}).get('localOnly', True) if isinstance(diagnostics.get('privacy'), dict) else True}",
        },
        {
            "id": "native-tray",
            "title": "Native tray",
            "level": "ok" if tray_contract.get("status") == "ready-for-packaging-design" else tray_contract.get("status", "unknown"),
            "summary": f"{len(tray_contract.get('trayItems', []) or [])} tray items · noInstall={not tray_contract.get('safety', {}).get('persistentInstall', True) if isinstance(tray_contract.get('safety'), dict) else True}",
        },
        {
            "id": "tray-readiness",
            "title": "Tray readiness",
            "level": "ok" if tray_readiness.get("status") == "ready-for-native-scaffold-decision" else tray_readiness.get("status", "unknown"),
            "summary": f"{tray_readiness.get('passedCount', 0)}/{tray_readiness.get('totalCount', 0)} gates · failed={len(tray_readiness.get('failedGateIds', []) or [])}",
        },
        {
            "id": "packaging-preflight",
            "title": "Packaging preflight",
            "level": "ok" if packaging_preflight.get("status") == "preflight-complete" else packaging_preflight.get("status", "unknown"),
            "summary": f"recommend={packaging_preflight.get('recommendation', 'n/a')} · install={packaging_preflight.get('safety', {}).get('dependencyInstall', False) if isinstance(packaging_preflight.get('safety'), dict) else False}",
        },
        {
            "id": "electron-fallback",
            "title": "Electron fallback",
            "level": "ok" if electron_fallback.get("status") == "planned-no-install" else electron_fallback.get("status", "unknown"),
            "summary": f"{electron_fallback.get('recommendation', 'n/a')} · scaffold={electron_fallback.get('scaffoldCreatedNow', False)} · install={electron_fallback.get('packageInstallPerformedNow', False)}",
        },
        {
            "id": "test-matrix",
            "title": "Wrapper test matrix",
            "level": "ok" if test_matrix.get("status") == "passed" else test_matrix.get("status", "unknown"),
            "summary": f"{test_matrix.get('passedCount', 0)}/{test_matrix.get('totalCount', 0)} tests · failed={len(test_matrix.get('failedIds', []) or [])}",
        },
        {
            "id": "ops-docs",
            "title": "Operations docs",
            "level": docs_status.get("status", "unknown"),
            "summary": f"{docs_status.get('commandCount', 0)} commands · matrix={docs_status.get('testMatrixStatus', 'n/a')} · tray={docs_status.get('trayReadinessStatus', 'n/a')}",
        },
        {
            "id": "audit-view",
            "title": "Audit viewer",
            "level": audit_view.get("status", "unknown"),
            "summary": f"{audit_view.get('eventCount', 0)} events · blocked={audit_view.get('blockedCount', 0)} · sensitive={audit_view.get('sensitiveCount', 0)}",
        },
        {
            "id": "home-summary",
            "title": "Companion home",
            "level": home_summary.get("status", "unknown"),
            "summary": f"cards={home_summary.get('cardCount', 0)} · resource={home_summary.get('resourcePressure', 'n/a')} · warnings={len(home_summary.get('warnings', []) or [])}",
        },
        {
            "id": "home-routes",
            "title": "Home routes",
            "level": "ok" if home_routes.get("status") == "passed" else home_routes.get("status", "unknown"),
            "summary": f"/home-summary.json={home_routes.get('routes', {}).get('/home-summary.json', {}).get('exists', False)} · /home.md={home_routes.get('routes', {}).get('/home.md', {}).get('exists', False)}",
        },
        {
            "id": "service-recovery-drill",
            "title": "Service recovery drill",
            "level": "ok" if recovery_drill.get("status") == "ready" else recovery_drill.get("status", "unknown"),
            "summary": f"{recovery_drill.get('passedCount', 0)}/{recovery_drill.get('checkCount', 0)} checks · warnings={len(recovery_drill.get('warningIds', []) or [])} · drillOnly={recovery_drill.get('safety', {}).get('drillOnly', False)}",
        },
        {
            "id": "multi-agent-board",
            "title": "Multi-agent board",
            "level": "ok" if multi_agent_board.get("status") == "ready" else multi_agent_board.get("status", "unknown"),
            "summary": f"{multi_agent_board.get('activeRoleCount', 0)}/{multi_agent_board.get('roleCount', 0)} roles · reports={len([r for r in multi_agent_board.get('reports', []) if r.get('exists')])} · resource={multi_agent_board.get('resourcePressure', 'n/a')}",
        },
        {
            "id": "physical-scenario-matrix",
            "title": "Physical scenario matrix",
            "level": "ok" if physical_matrix.get("status") == "passed" else physical_matrix.get("status", "unknown"),
            "summary": f"{physical_matrix.get('passedCount', 0)}/{physical_matrix.get('scenarioCount', 0)} scenarios · failed={len(physical_matrix.get('failedIds', []) or [])} · realDevice=False",
        },
        {
            "id": "next-connector-queue",
            "title": "Next connector queue",
            "level": "ok" if next_queue.get("status") == "ready" else next_queue.get("status", "unknown"),
            "summary": f"selected={(next_queue.get('selected') or {}).get('id', 'none')} · ranked={len(next_queue.get('ranked', []) or [])} · completed={len(next_queue.get('completed', []) or [])} · gated={len(next_queue.get('blockedImportant', []) or [])}",
        },
        {
            "id": "voice-body-readiness",
            "title": "Voice/body readiness",
            "level": "ok" if voice_body.get("status") == "ready" else voice_body.get("status", "unknown"),
            "summary": f"{voice_body.get('readiness', {}).get('readyCount', 0)}/{voice_body.get('readiness', {}).get('gateCount', 0)} gates · recording={voice_body.get('summary', {}).get('recordingNow', False)} · alwaysOn={voice_body.get('summary', {}).get('alwaysOnMicEnabled', False)}",
        },
        {
            "id": "voice-wake-boundary",
            "title": "Voice wake boundary",
            "level": "ok" if voice_wake_boundary.get("status") == "ready" else voice_wake_boundary.get("status", "unknown"),
            "summary": f"boundaryOnly={voice_wake_boundary.get('safety', {}).get('boundaryOnly', False)} · micStarted={voice_wake_boundary.get('safety', {}).get('startsMicrophone', False)} · warnings={len(voice_wake_boundary.get('warnings', []) or [])}",
        },
        {
            "id": "voice-vad-dry-run",
            "title": "Voice VAD dry-run",
            "level": "ok" if voice_vad_dry_run.get("status") == "ready" else voice_vad_dry_run.get("status", "unknown"),
            "summary": f"dryRun={voice_vad_dry_run.get('safety', {}).get('dryRunOnly', False)} · micStarted={voice_vad_dry_run.get('safety', {}).get('startsMicrophone', False)} · warnings={len(voice_vad_dry_run.get('warnings', []) or [])}",
        },
        {
            "id": "voice-vad-runner",
            "title": "Voice VAD runner",
            "level": "ok" if voice_vad_runner.get("status") in {"ready", "measured-metrics-only"} else voice_vad_runner.get("status", "unknown"),
            "summary": f"status={voice_vad_runner.get('status', 'n/a')} · rawStored={voice_vad_runner.get('safety', {}).get('storesRawAudio', False)} · persistent={voice_vad_runner.get('safety', {}).get('startsPersistentProcess', False)}",
        },
        {
            "id": "voice-vad-baseline",
            "title": "Voice VAD baseline",
            "level": "ok" if voice_vad_baseline.get("status") == "ready" else voice_vad_baseline.get("status", "unknown"),
            "summary": f"candidates={voice_vad_baseline.get('evaluator', {}).get('aggregate', {}).get('totalCandidateWakeCount', 'n/a')} · evaluatorOnly={voice_vad_baseline.get('safety', {}).get('evaluatorOnly', False)} · warnings={len(voice_vad_baseline.get('warnings', []) or [])}",
        },
        {
            "id": "voice-spoken-wake-boundary",
            "title": "Voice spoken wake boundary",
            "level": "ok" if voice_spoken_wake.get("status") == "ready" else voice_spoken_wake.get("status", "unknown"),
            "summary": f"boundaryOnly={voice_spoken_wake.get('safety', {}).get('boundaryOnly', False)} · micStarted={voice_spoken_wake.get('safety', {}).get('startsMicrophone', False)} · blocked={len(voice_spoken_wake.get('blocked', []) or [])}",
        },
        {
            "id": "voice-wake-engine-readiness",
            "title": "Voice wake engine readiness",
            "level": "ok" if voice_wake_engine.get("status") == "ready" else voice_wake_engine.get("status", "unknown"),
            "summary": f"recommended={voice_wake_engine.get('recommendedNext', {}).get('id', 'n/a')} · installNow={voice_wake_engine.get('installDecision', {}).get('installPerformedNow', False)} · warnings={len(voice_wake_engine.get('warnings', []) or [])}",
        },
        {
            "id": "voice-spoken-wake-runner",
            "title": "Voice spoken wake runner",
            "level": "ok" if voice_spoken_runner.get("status") in {"ready", "measured-needs-phrase-confirmation-backend"} else voice_spoken_runner.get("status", "unknown"),
            "summary": f"status={voice_spoken_runner.get('status', 'n/a')} · armed={voice_spoken_runner.get('arming', {}).get('armedThisRun', False)} · micStarted={voice_spoken_runner.get('safety', {}).get('startsMicrophone', False)}",
        },
        {
            "id": "voice-phrase-retention",
            "title": "Voice phrase retention",
            "level": "ok" if voice_phrase_retention.get("status") == "ready" else voice_phrase_retention.get("status", "unknown"),
            "summary": f"rawLeftovers={len([item for item in voice_phrase_retention.get('rawCandidates', []) if item.get('exists')])} · verifierOnly={voice_phrase_retention.get('safety', {}).get('verifierOnly', False)} · blocked={len(voice_phrase_retention.get('blocked', []) or [])}",
        },
        {
            "id": "voice-phrase-match",
            "title": "Voice phrase match",
            "level": "ok" if voice_phrase_match.get("status") == "ready" else voice_phrase_match.get("status", "unknown"),
            "summary": f"selfTest={voice_phrase_match.get('normalizer', {}).get('examples', []) and all(item.get('passed') for item in voice_phrase_match.get('normalizer', {}).get('examples', []))} · micStarted={voice_phrase_match.get('safety', {}).get('startsMicrophone', False)} · transcriptStored={not voice_phrase_match.get('safety', {}).get('storesTranscriptByDefault', True)}",
        },
        {
            "id": "voice-wake-e2e",
            "title": "Voice wake E2E gate",
            "level": "ok" if voice_wake_e2e.get("status") == "ready-for-armed-calibration" else voice_wake_e2e.get("status", "unknown"),
            "summary": f"ready={voice_wake_e2e.get('readyFor', {}).get('armedSpokenWakeCalibration', False)} · continuous={voice_wake_e2e.get('readyFor', {}).get('continuousAlwaysOnListener', False)} · blocked={len(voice_wake_e2e.get('blocked', []) or [])}",
        },
        {
            "id": "body-indicators",
            "title": "Body indicators",
            "level": "ok" if body_indicators.get("status") == "ready" else body_indicators.get("status", "unknown"),
            "summary": f"mic={body_indicators.get('summary', {}).get('microphoneIndicatorState', 'n/a')} active={body_indicators.get('summary', {}).get('microphoneActive', False)} · camera={body_indicators.get('summary', {}).get('cameraIndicatorState', 'n/a')} active={body_indicators.get('summary', {}).get('cameraActive', False)} · noCapture={body_indicators.get('safety', {}).get('noCapture', False)}",
        },
        {
            "id": "body-control-contract",
            "title": "Body control contract",
            "level": "ok" if body_control_contract.get("status") == "ready" else body_control_contract.get("status", "unknown"),
            "summary": f"action={body_control_contract.get('selectedAction', 'n/a')} · previewOnly={body_control_contract.get('safety', {}).get('previewOnly', False)} · activeNow={body_control_contract.get('currentState', {}).get('activeNow', False)} · target={body_control_contract.get('actionPreview', {}).get('target', 'none')}",
        },
        {
            "id": "camera-single-frame-dry-run",
            "title": "Camera single-frame dry-run",
            "level": "ok" if camera_single_frame.get("status") == "ready" else camera_single_frame.get("status", "unknown"),
            "summary": f"device={camera_single_frame.get('selectedDevice', {}).get('index', 'n/a')} · dryRun={camera_single_frame.get('safety', {}).get('dryRunOnly', False)} · startsCamera={camera_single_frame.get('safety', {}).get('startsCamera', False)} · capturesFrame={camera_single_frame.get('safety', {}).get('capturesFrame', False)}",
        },
        {
            "id": "camera-single-frame-capture",
            "title": "Camera single-frame capture",
            "level": "ok" if camera_single_frame_capture.get("status") in {"ready", "captured-and-deleted"} else camera_single_frame_capture.get("status", "unknown"),
            "summary": f"status={camera_single_frame_capture.get('status', 'n/a')} · rawDeleted={camera_single_frame_capture.get('safety', {}).get('rawImageDeleted', False)} · indicatorRestored={camera_single_frame_capture.get('indicatorRestored', False)} · size={camera_capture_parsed.get('width', 'n/a')}x{camera_capture_parsed.get('height', 'n/a')}",
        },
        {
            "id": "camera-privacy-verifier",
            "title": "Camera privacy verifier",
            "level": "ok" if camera_privacy.get("status") == "passed" else camera_privacy.get("status", "unknown"),
            "summary": f"rawLeftovers={len([item for item in camera_privacy.get('rawCandidates', []) if item.get('exists')])} · warnings={len(camera_privacy.get('warnings', []) or [])} · verifierOnly={camera_privacy.get('safety', {}).get('verifierOnly', False)}",
        },
        {
            "id": "camera-visual-analysis-boundary",
            "title": "Camera visual analysis boundary",
            "level": "ok" if camera_visual_boundary.get("status") == "ready" else camera_visual_boundary.get("status", "unknown"),
            "summary": f"boundaryOnly={camera_visual_boundary.get('safety', {}).get('boundaryOnly', False)} · analyzesNow={camera_visual_boundary.get('safety', {}).get('analyzesImageNow', False)} · blocked={len(camera_visual_boundary.get('blocked', []) or [])}",
        },
        {
            "id": "camera-visual-semantics",
            "title": "Camera visual semantics",
            "level": "ok" if camera_visual_semantics.get("status") in {"ready", "captured-analyzed-and-deleted"} else camera_visual_semantics.get("status", "unknown"),
            "summary": f"status={camera_visual_semantics.get('status', 'n/a')} · rawDeleted={camera_visual_semantics.get('safety', {}).get('rawImageDeleted', False)} · model={camera_visual_semantics.get('safety', {}).get('modelInference', False)} · persistent={camera_visual_semantics.get('safety', {}).get('startsPersistentProcess', False)}",
        },
        {
            "id": "multi-agent-handoff-rules",
            "title": "Multi-agent handoff rules",
            "level": "ok" if handoff_rules.get("status") == "ready" else handoff_rules.get("status", "unknown"),
            "summary": f"{handoff_rules.get('ruleCount', 0)} rules · activeRoles={handoff_rules.get('activeRoles', 0)}/{handoff_rules.get('roleCount', 0)} · selectedByQueue={handoff_rules.get('selectedByQueue', False)}",
        },
        {
            "id": "approval-gate-register",
            "title": "Approval gate register",
            "level": "ok" if approval_gates.get("status") == "ready" else approval_gates.get("status", "unknown"),
            "summary": f"{approval_gates.get('approvalGatedCount', 0)}/{approval_gates.get('gateCount', 0)} gated · queueBlocked={len(approval_gates.get('queueBlockedImportant', []) or [])}",
        },
        {
            "id": "release-readiness",
            "title": "Release readiness",
            "level": "ok" if release_readiness.get("status") == "ready" else release_readiness.get("status", "unknown"),
            "summary": f"{release_readiness.get('overall', {}).get('level', 'n/a')} · {release_readiness.get('overall', {}).get('percent', 0)}% · blockers={len(release_readiness.get('hardBlockers', []) or [])}",
        },
        {
            "id": "morning-digest",
            "title": "Morning progress digest",
            "level": "ok" if morning_digest.get("status") == "ready" else morning_digest.get("status", "unknown"),
            "summary": f"{morning_digest.get('release', {}).get('level', 'n/a')} · completed={morning_digest.get('queue', {}).get('completedCount', 0)} · blockers={len(morning_digest.get('hardBlockers', []) or [])}",
        },
        {
            "id": "decision-boundary-packet",
            "title": "Decision boundary packet",
            "level": "ok" if decision_packet.get("status") == "ready" else decision_packet.get("status", "unknown"),
            "summary": f"options={len(decision_packet.get('options', []) or [])} · approvalGates={decision_packet.get('approvalGatedCount', 0)}/{decision_packet.get('approvalGateCount', 0)} · release={decision_packet.get('release', {}).get('level', 'n/a')}",
        },
        {
            "id": "electron-scaffold",
            "title": "Electron scaffold",
            "level": "ok" if electron_scaffold.get("status") == "scaffold-ready" else electron_scaffold.get("status", "unknown"),
            "summary": f"files={len([f for f in electron_scaffold.get('files', []) if f.get('exists')])}/{len(electron_scaffold.get('files', []) or [])} · depsInstalled={electron_scaffold.get('dependencyInstallPerformed', False)} · canRun={electron_scaffold.get('canRunNow', False)}",
        },
        {
            "id": "electron-menu",
            "title": "Electron menu",
            "level": "ok" if electron_menu.get("status") == "ready" else electron_menu.get("status", "unknown"),
            "summary": f"items={electron_menu.get('menuItemCount', 0)} · wired={electron_menu.get('wiredInMainProcess', False)} · mutates={electron_menu.get('safety', {}).get('mutatesState', 'n/a')}",
        },
        {
            "id": "electron-tray",
            "title": "Electron tray",
            "level": "ok" if electron_tray.get("status") == "ready" else electron_tray.get("status", "unknown"),
            "summary": f"items={electron_tray.get('trayItemCount', 0)} · states={len(electron_tray.get('dynamicStates', []) or [])} · wired={electron_tray.get('wiredInMainProcess', False)}",
        },
        {
            "id": "electron-autostart",
            "title": "Electron autostart",
            "level": "ok" if electron_autostart.get("installed") and electron_autostart_rollback.get("status") == "passed" else electron_autostart.get("status", "unknown"),
            "summary": f"installed={electron_autostart.get('installed', False)} · mechanism={'startup-folder-cmd' if electron_autostart.get('startupCmd', {}).get('installed') else 'scheduled-task' if electron_autostart.get('task', {}).get('installed') else 'none'} · rollback={electron_autostart_rollback.get('status', 'n/a')} · startsNow={electron_autostart.get('safety', {}).get('startsPersistentProcessNow', False)}",
        },
    ]
    return {
        "timestamp": now_iso(),
        "status": "ok",
        "cards": cards,
        "runtimeActions": pick_runtime_actions(runtime),
        "organBindings": [
            {"id": b.get("id"), "abilityId": b.get("abilityId"), "linkCount": b.get("linkCount")}
            for b in (organ.get("bindings", []) or [])
            if isinstance(b, dict)
        ],
        "physicalActuation": {
            "allowlistStatus": physical_allowlist.get("status", "missing"),
            "allowlistedTargets": [
                {
                    "id": item.get("id"),
                    "type": item.get("type"),
                    "realDevice": item.get("realDevice"),
                    "allowedTiers": item.get("allowedTiers", []),
                    "allowedOperations": item.get("allowedOperations", []),
                }
                for item in (physical_allowlist.get("devices", []) or [])
                if isinstance(item, dict)
            ],
            "lastSimulatorStatus": {
                "timestamp": physical_status.get("timestamp"),
                "status": physical_status.get("status"),
                "reason": physical_status.get("reason"),
                "target": (physical_status.get("action", {}) if isinstance(physical_status.get("action"), dict) else {}).get("target"),
                "operation": (physical_status.get("action", {}) if isinstance(physical_status.get("action"), dict) else {}).get("operation"),
                "realDeviceCalled": physical_status.get("realDeviceCalled", False),
            },
        },
        "serviceHealth": {
            "status": service_health.get("status", "missing"),
            "timestamp": service_health.get("timestamp"),
            "gatewayConnectivityOk": service_health.get("gatewayConnectivityOk"),
            "watchdogLastStatusOk": service_health.get("watchdogLastStatusOk"),
            "missingRequiredTasks": service_health.get("missingRequiredTasks", []),
            "tasks": [
                {
                    "id": task.get("id"),
                    "name": task.get("name"),
                    "registered": task.get("registered"),
                    "rollback": task.get("rollback"),
                    "purpose": task.get("purpose"),
                }
                for task in (service_health.get("tasks", []) or [])
                if isinstance(task, dict)
            ],
            "healthContract": service_health.get("healthContract", {}),
        },
        "serviceControls": {
            "status": service_control.get("status", "missing"),
            "safeActions": service_control.get("safeActions", {}),
            "blockedDirectActions": service_control.get("blockedDirectActions", {}),
            "rollbackCommandsPreview": service_control.get("rollbackCommandsPreview", []),
            "safeModePreview": service_control.get("safeModePreview", {}),
            "lastPreview": service_control_state,
        },
        "voiceCalibration": {
            "status": voice_calibration.get("status", "missing"),
            "mode": voice_calibration.get("mode"),
            "alwaysOnMicEnabled": voice_calibration.get("alwaysOnMicEnabled", False),
            "recordingNow": voice_calibration.get("recordingNow", False) or voice_indicator.get("recordingNow", False),
            "deviceEnumeration": voice_calibration.get("deviceEnumeration", {}),
            "manualCalibrationPlan": voice_calibration.get("manualCalibrationPlan", {}),
            "privacyLedger": voice_calibration.get("privacyLedger", {}),
            "indicator": voice_calibration.get("indicator", {}),
            "runner": voice_runner,
            "runnerControls": {
                "previewCommand": "python core/scripts/voice_manual_calibration_runner.py",
                "recordCommandRequiresToken": "python core/scripts/voice_manual_calibration_runner.py --record --confirm LEE_APPROVED_3_SECOND_LOCAL_CALIBRATION",
                "defaultDeletesRawAudio": True,
                "recordingWithoutTokenBlocked": True,
            },
            "blockedModes": voice_calibration.get("blockedModes", {}),
        },
        "desktopWrapper": {
            "status": desktop_wrapper.get("status", "missing"),
            "mode": desktop_wrapper.get("mode"),
            "appRoot": desktop_wrapper.get("appRoot"),
            "dashboard": desktop_wrapper.get("dashboard", {}),
            "appShellStatus": desktop_wrapper.get("appShellStatus", {}),
            "routes": desktop_wrapper.get("routes", {}),
            "controlPreview": wrapper_control_preview,
            "resourceBudgetGate": resource_gate,
            "resourceTrendGate": resource_trend,
            "resourcePressureResponse": resource_response,
            "resourceRecoveryGate": resource_recovery,
            "resourceProfileSync": resource_profile_sync,
            "resourceGateConsistency": resource_gate_consistency,
            "resourceSerializedRefresh": resource_serialized_refresh,
            "sensitiveResourcePreflight": sensitive_preflight,
            "resourceActionClearanceTicket": resource_action_ticket,
            "resourceActionClearanceVerifier": resource_action_verifier,
            "resourceGuardedActionWrapper": resource_guarded_wrapper,
            "resourceGuardIntegrationMap": resource_guard_map,
            "resourceGuardEnforcementScorecard": resource_guard_scorecard,
            "externalActionGuard": external_action_guard,
            "quietHoursActionGate": quiet_hours_gate,
            "deferredOrganCalibrationQueue": deferred_organ_queue,
            "organCalibrationResumePacket": organ_resume_packet,
            "organCalibrationResumeReadinessAudit": organ_resume_audit,
            "quietHoursProgressBatcher": quiet_progress_batcher,
            "selfFundingValueLedger": self_funding_value,
            "selfFundingOfferDraft": self_funding_offer,
            "selfFundingDemoPack": self_funding_demo,
            "selfFundingDemoPrivacyVerifier": self_funding_privacy,
            "selfFundingRoiCalculator": self_funding_roi,
            "selfFundingBuyerRunbook": self_funding_runbook,
            "selfFundingSampleWorkflowDemo": self_funding_sample,
            "selfFundingPilotChecklist": self_funding_checklist,
            "usageWindowPressureGate": usage_window_gate,
            "resourceSafeConnectorQueue": resource_safe_queue,
            "resourcePolicySummary": resource_policy_summary,
            "diagnostics": diagnostics,
            "trayContract": tray_contract,
            "trayReadiness": tray_readiness,
            "packagingPreflight": packaging_preflight,
            "electronFallback": electron_fallback,
            "testMatrix": test_matrix,
            "operationsDocs": docs_status,
            "auditView": audit_view,
            "auditCompactionPlan": audit_compaction,
            "auditTailFingerprint": audit_tail_fingerprint,
            "auditStreamingManifest": audit_streaming_manifest,
            "homeSummary": home_summary,
            "homeRoutes": home_routes,
            "serviceRecoveryDrill": recovery_drill,
            "multiAgentBoard": multi_agent_board,
            "physicalScenarioMatrix": physical_matrix,
            "nextConnectorQueue": next_queue,
            "voiceBodyReadiness": voice_body,
            "voiceWakeBoundary": voice_wake_boundary,
            "voiceVadDryRun": voice_vad_dry_run,
            "voiceVadRunner": voice_vad_runner,
            "voiceVadBaseline": voice_vad_baseline,
            "voiceSpokenWakeBoundary": voice_spoken_wake,
            "voiceWakeEngineReadiness": voice_wake_engine,
            "voiceSpokenWakeRunner": voice_spoken_runner,
            "voicePhraseRetention": voice_phrase_retention,
            "voicePhraseMatch": voice_phrase_match,
            "voiceWakeE2E": voice_wake_e2e,
            "bodyIndicators": body_indicators,
            "bodyControlContract": body_control_contract,
            "cameraSingleFrameDryRun": camera_single_frame,
            "cameraSingleFrameCapture": camera_single_frame_capture,
            "cameraPrivacyVerifier": camera_privacy,
            "cameraVisualAnalysisBoundary": camera_visual_boundary,
            "cameraVisualSemantics": camera_visual_semantics,
            "multiAgentHandoffRules": handoff_rules,
            "approvalGateRegister": approval_gates,
            "releaseReadiness": release_readiness,
            "morningDigest": morning_digest,
            "decisionBoundaryPacket": decision_packet,
            "electronScaffold": electron_scaffold,
            "electronMenu": electron_menu,
            "electronTray": electron_tray,
            "electronAutostart": electron_autostart,
            "electronAutostartReadiness": electron_autostart_readiness,
            "electronAutostartRollbackDrill": electron_autostart_rollback,
            "safety": desktop_wrapper.get("safety", {}),
            "commands": {
                "check": "cd apps/local-desktop-companion && npm run check",
                "status": "cd apps/local-desktop-companion && npm run status",
                "controls": "cd apps/local-desktop-companion && npm run controls",
                "diagnostics": "cd apps/local-desktop-companion && npm run diagnostics",
                "previewPause": "cd apps/local-desktop-companion && npm run preview:pause",
                "previewResume": "cd apps/local-desktop-companion && npm run preview:resume",
                "serve": "cd apps/local-desktop-companion && npm run serve"
            }
        },
        "nextSuggestedActions": [
            "Turn the dependency-free wrapper into a native tray/Tauri/Electron package after controls stabilize.",
            "Run short voice wake calibration before any always-on microphone mode.",
            "Build Tauri/Electron wrapper around this dashboard as the first desktop companion app shell.",
            "Keep using resource guard before multi-agent/gpu-heavy work.",
        ],
        "privacyGates": {
            "alwaysOnMicRequiresApproval": True,
            "persistentServiceApprovedAndEnabled": True,
            "realPhysicalActuationRequiresAllowlistAndGate": True,
            "externalSendRequiresApproval": True,
        },
    }


def render(status: dict[str, Any]) -> str:
    cards_html = []
    for card in status["cards"]:
        level = html.escape(str(card.get("level", "unknown")))
        cards_html.append(
            f'<section class="card {level}"><div class="kicker">{html.escape(str(card.get("id")))}</div>'
            f'<h2>{html.escape(str(card.get("title")))}</h2><p>{html.escape(str(card.get("summary")))}</p></section>'
        )
    actions = "".join(f"<li>{html.escape(str(a))}</li>" for a in status.get("nextSuggestedActions", []))
    runtime = "".join(
        f"<li><code>{html.escape(str(item.get('action')))}</code> rc={html.escape(str(item.get('rc')))}</li>"
        for item in status.get("runtimeActions", [])
    )
    bindings = "".join(
        f"<li><code>{html.escape(str(item.get('id')))}</code> → {html.escape(str(item.get('abilityId')))} ({html.escape(str(item.get('linkCount')))} links)</li>"
        for item in status.get("organBindings", [])
    )
    physical = status.get("physicalActuation", {}) if isinstance(status.get("physicalActuation"), dict) else {}
    physical_targets = "".join(
        f"<li><code>{html.escape(str(item.get('id')))}</code> · {html.escape(str(item.get('type')))} · realDevice={html.escape(str(item.get('realDevice')))} · ops={html.escape(', '.join(map(str, item.get('allowedOperations', []) or [])))}</li>"
        for item in physical.get("allowlistedTargets", [])
        if isinstance(item, dict)
    )
    last_physical = physical.get("lastSimulatorStatus", {}) if isinstance(physical.get("lastSimulatorStatus"), dict) else {}
    service = status.get("serviceHealth", {}) if isinstance(status.get("serviceHealth"), dict) else {}
    service_tasks = "".join(
        f"<li><code>{html.escape(str(item.get('name')))}</code> · registered={html.escape(str(item.get('registered')))} · rollback=<code>{html.escape(str(item.get('rollback')))}</code></li>"
        for item in service.get("tasks", [])
        if isinstance(item, dict)
    )
    service_controls = status.get("serviceControls", {}) if isinstance(status.get("serviceControls"), dict) else {}
    safe_actions = service_controls.get("safeActions", {}) if isinstance(service_controls.get("safeActions"), dict) else {}
    safe_action_items = "".join(
        f"<li><code>{html.escape(str(action_id))}</code> · {html.escape(str(action.get('mode')))} · {html.escape(str(action.get('description')))}</li>"
        for action_id, action in safe_actions.items()
        if isinstance(action, dict)
    )
    blocked_actions = service_controls.get("blockedDirectActions", {}) if isinstance(service_controls.get("blockedDirectActions"), dict) else {}
    blocked_action_items = "".join(
        f"<li><code>{html.escape(str(action_id))}</code> · blocked · {html.escape(str(reason))}</li>"
        for action_id, reason in blocked_actions.items()
    )
    last_service_preview = service_controls.get("lastPreview", {}) if isinstance(service_controls.get("lastPreview"), dict) else {}
    voice_cal = status.get("voiceCalibration", {}) if isinstance(status.get("voiceCalibration"), dict) else {}
    device_enum = voice_cal.get("deviceEnumeration", {}) if isinstance(voice_cal.get("deviceEnumeration"), dict) else {}
    rec_input = device_enum.get("recommendedInput", {}) if isinstance(device_enum.get("recommendedInput"), dict) else {}
    manual_plan = voice_cal.get("manualCalibrationPlan", {}) if isinstance(voice_cal.get("manualCalibrationPlan"), dict) else {}
    blocked_modes = voice_cal.get("blockedModes", {}) if isinstance(voice_cal.get("blockedModes"), dict) else {}
    runner = voice_cal.get("runner", {}) if isinstance(voice_cal.get("runner"), dict) else {}
    runner_controls = voice_cal.get("runnerControls", {}) if isinstance(voice_cal.get("runnerControls"), dict) else {}
    blocked_voice_items = "".join(
        f"<li><code>{html.escape(str(mode))}</code> · {html.escape(str(reason))}</li>"
        for mode, reason in blocked_modes.items()
    )
    wrapper = status.get("desktopWrapper", {}) if isinstance(status.get("desktopWrapper"), dict) else {}
    wrapper_routes = wrapper.get("routes", {}) if isinstance(wrapper.get("routes"), dict) else {}
    wrapper_route_items = "".join(
        f"<li><code>{html.escape(str(route))}</code> · {html.escape(str(desc))}</li>"
        for route, desc in wrapper_routes.items()
    )
    wrapper_safety = wrapper.get("safety", {}) if isinstance(wrapper.get("safety"), dict) else {}
    wrapper_safety_items = "".join(
        f"<li>{html.escape(str(key))}={html.escape(str(value))}</li>"
        for key, value in wrapper_safety.items()
    )
    wrapper_control = wrapper.get("controlPreview", {}) if isinstance(wrapper.get("controlPreview"), dict) else {}
    wrapper_endpoint = wrapper.get("controlEndpoint", {}) if isinstance(wrapper.get("controlEndpoint"), dict) else {}
    wrapper_diagnostics = wrapper.get("diagnostics", {}) if isinstance(wrapper.get("diagnostics"), dict) else {}
    tray = wrapper.get("trayContract", {}) if isinstance(wrapper.get("trayContract"), dict) else {}
    tray_ready = wrapper.get("trayReadiness", {}) if isinstance(wrapper.get("trayReadiness"), dict) else {}
    packaging = wrapper.get("packagingPreflight", {}) if isinstance(wrapper.get("packagingPreflight"), dict) else {}
    electron = wrapper.get("electronFallback", {}) if isinstance(wrapper.get("electronFallback"), dict) else {}
    matrix = wrapper.get("testMatrix", {}) if isinstance(wrapper.get("testMatrix"), dict) else {}
    ops_docs = wrapper.get("operationsDocs", {}) if isinstance(wrapper.get("operationsDocs"), dict) else {}
    audit = wrapper.get("auditView", {}) if isinstance(wrapper.get("auditView"), dict) else {}
    home = wrapper.get("homeSummary", {}) if isinstance(wrapper.get("homeSummary"), dict) else {}
    home_routes_panel = wrapper.get("homeRoutes", {}) if isinstance(wrapper.get("homeRoutes"), dict) else {}
    recovery = wrapper.get("serviceRecoveryDrill", {}) if isinstance(wrapper.get("serviceRecoveryDrill"), dict) else {}
    board = wrapper.get("multiAgentBoard", {}) if isinstance(wrapper.get("multiAgentBoard"), dict) else {}
    physical_scenarios = wrapper.get("physicalScenarioMatrix", {}) if isinstance(wrapper.get("physicalScenarioMatrix"), dict) else {}
    queue = wrapper.get("nextConnectorQueue", {}) if isinstance(wrapper.get("nextConnectorQueue"), dict) else {}
    voice_body_panel = wrapper.get("voiceBodyReadiness", {}) if isinstance(wrapper.get("voiceBodyReadiness"), dict) else {}
    handoff_panel = wrapper.get("multiAgentHandoffRules", {}) if isinstance(wrapper.get("multiAgentHandoffRules"), dict) else {}
    approval_panel = wrapper.get("approvalGateRegister", {}) if isinstance(wrapper.get("approvalGateRegister"), dict) else {}
    release_panel = wrapper.get("releaseReadiness", {}) if isinstance(wrapper.get("releaseReadiness"), dict) else {}
    digest_panel = wrapper.get("morningDigest", {}) if isinstance(wrapper.get("morningDigest"), dict) else {}
    decision_panel = wrapper.get("decisionBoundaryPacket", {}) if isinstance(wrapper.get("decisionBoundaryPacket"), dict) else {}
    electron_panel = wrapper.get("electronScaffold", {}) if isinstance(wrapper.get("electronScaffold"), dict) else {}
    electron_menu_panel = wrapper.get("electronMenu", {}) if isinstance(wrapper.get("electronMenu"), dict) else {}
    electron_tray_panel = wrapper.get("electronTray", {}) if isinstance(wrapper.get("electronTray"), dict) else {}
    tray_items = tray.get("trayItems", []) if isinstance(tray.get("trayItems"), list) else []
    tray_item_html = "".join(
        f"<li><code>{html.escape(str(item.get('id')))}</code> · {html.escape(str(item.get('label')))} · safe={html.escape(str(item.get('safeByDefault')))}</li>"
        for item in tray_items
        if isinstance(item, dict)
    )
    safe_previews = wrapper_control.get("safePreviewActions", {}) if isinstance(wrapper_control.get("safePreviewActions"), dict) else {}
    wrapper_control_items = "".join(
        f"<li><code>{html.escape(str(action))}</code> · {html.escape(str(desc))}</li>"
        for action, desc in safe_previews.items()
    )
    reversible_exec = wrapper_control.get("reversibleExecuteActions", {}) if isinstance(wrapper_control.get("reversibleExecuteActions"), dict) else {}
    reversible_exec_items = "".join(
        f"<li><code>{html.escape(str(action))}</code> · {html.escape(str(desc))}</li>"
        for action, desc in reversible_exec.items()
    )
    blocked_direct = wrapper_control.get("blockedDirectActions", []) if isinstance(wrapper_control.get("blockedDirectActions"), list) else []
    wrapper_blocked_items = "".join(f"<li><code>{html.escape(str(action))}</code></li>" for action in blocked_direct)
    return f"""<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>the agent Companion Status</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, 'Microsoft YaHei', system-ui, sans-serif; background:#0b0f17; color:#e8eefc; }}
body {{ margin:0; padding:28px; }}
header {{ margin-bottom:22px; }} h1 {{ margin:0; font-size:28px; }} .sub {{ color:#9fb0d1; margin-top:6px; }}
.grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:14px; }}
.card {{ border:1px solid #24304a; background:#121a29; border-radius:18px; padding:16px; box-shadow:0 10px 30px #0004; }}
.card.ok {{ border-color:#2a815f; }} .card.warn {{ border-color:#a9852a; }} .card.critical {{ border-color:#b84a4a; }}
.kicker {{ color:#8da2c8; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }} h2 {{ margin:8px 0; font-size:18px; }} p {{ color:#c8d3e8; line-height:1.45; }}
.panel {{ margin-top:18px; border:1px solid #24304a; border-radius:18px; padding:16px; background:#0f1624; }}
code {{ color:#9ee7ff; }} li {{ margin:6px 0; color:#c8d3e8; }}
</style></head><body>
<header><h1>the agent Desktop Companion · Status Snapshot</h1><div class=\"sub\">Generated {html.escape(str(status.get('timestamp')))} · local read-only dashboard prototype</div></header>
<main><div class=\"grid\">{''.join(cards_html)}</div>
<section class=\"panel\"><h2>Next suggested actions</h2><ul>{actions}</ul></section>
<section class=\"panel\"><h2>Recent resident actions</h2><ul>{runtime}</ul></section>
<section class=\"panel\"><h2>Organ bindings</h2><ul>{bindings}</ul></section>
<section class=\"panel\"><h2>Physical actuation simulator</h2><p>Allowlist: {html.escape(str(physical.get('allowlistStatus', 'missing')))} · last={html.escape(str(last_physical.get('status', 'n/a')))} · target={html.escape(str(last_physical.get('target', 'n/a')))} · realDeviceCalled={html.escape(str(last_physical.get('realDeviceCalled', False)))}</p><ul>{physical_targets}</ul></section>
<section class=\"panel\"><h2>Service health / rollback</h2><p>Status: {html.escape(str(service.get('status', 'missing')))} · gateway={html.escape(str(service.get('gatewayConnectivityOk', 'n/a')))} · watchdog={html.escape(str(service.get('watchdogLastStatusOk', 'n/a')))} · missing={html.escape(str(len(service.get('missingRequiredTasks', []) or [])))}</p><ul>{service_tasks}</ul></section>
<section class=\"panel\"><h2>Service control previews</h2><p>Last preview: {html.escape(str(last_service_preview.get('action', 'n/a')))} · {html.escape(str(last_service_preview.get('status', 'n/a')))} · systemChange={html.escape(str(last_service_preview.get('executedSystemChange', False)))}</p><h3>Safe previews</h3><ul>{safe_action_items}</ul><h3>Blocked direct actions</h3><ul>{blocked_action_items}</ul></section>
<section class=\"panel\"><h2>Voice manual calibration</h2><p>Status: {html.escape(str(voice_cal.get('status', 'missing')))} · mode={html.escape(str(voice_cal.get('mode', 'n/a')))} · recordingNow={html.escape(str(voice_cal.get('recordingNow', False)))} · alwaysOn={html.escape(str(voice_cal.get('alwaysOnMicEnabled', False)))}</p><p>Recommended input: <code>{html.escape(str(rec_input.get('index', 'n/a')))}</code> · {html.escape(str(rec_input.get('name', 'n/a')))} · sample={html.escape(str(manual_plan.get('durationSeconds', 'n/a')))}s · rawAudio={html.escape(str(manual_plan.get('rawAudioDefaultRetention', 'n/a')))}</p><p>Runner last: {html.escape(str(runner.get('event', 'n/a')))} · {html.escape(str(runner.get('status', 'n/a')))} · recordingStarted={html.escape(str(runner.get('recordingStarted', False)))} · rawCreated={html.escape(str(runner.get('rawAudioCreated', False)))}</p><p>Preview: <code>{html.escape(str(runner_controls.get('previewCommand', 'n/a')))}</code></p><h3>Blocked voice modes</h3><ul>{blocked_voice_items}</ul></section>
<section class=\"panel\"><h2>Desktop wrapper skeleton</h2><p>Status: {html.escape(str(wrapper.get('status', 'missing')))} · mode={html.escape(str(wrapper.get('mode', 'n/a')))} · appRoot=<code>{html.escape(str(wrapper.get('appRoot', 'n/a')))}</code></p><h3>Routes</h3><ul>{wrapper_route_items}</ul><h3>Safety</h3><ul>{wrapper_safety_items}</ul></section>
<section class=\"panel\"><h2>Wrapper control previews</h2><p>Status: {html.escape(str(wrapper_control.get('status', 'missing')))} · event={html.escape(str(wrapper_control.get('event', wrapper_control.get('mode', 'n/a'))))} · mutatesState={html.escape(str(wrapper_control.get('mutatesAppControlState', False)))} · sensitiveAction={html.escape(str(wrapper_control.get('executesSensitiveAction', False)))}</p><h3>Safe preview actions</h3><ul>{wrapper_control_items}</ul><h3>Reversible execute actions</h3><ul>{reversible_exec_items}</ul><h3>Blocked direct actions</h3><ul>{wrapper_blocked_items}</ul></section>
<section class=\"panel\"><h2>Local control endpoint</h2><p>Status: {html.escape(str(wrapper_endpoint.get('status', 'missing')))} · mode={html.escape(str(wrapper_endpoint.get('mode', 'n/a')))} · lastAction={html.escape(str(wrapper_endpoint.get('lastAction', 'n/a')))} · mutatesState={html.escape(str(wrapper_endpoint.get('mutatesAppControlState', False)))}</p><p>Route: <code>POST /api/control/preview</code> accepts preview-only JSON and blocks execute/sensitive actions.</p></section>
<section class=\"panel\"><h2>Diagnostics export</h2><p>Status: {html.escape(str(wrapper_diagnostics.get('status', 'missing')))} · files={html.escape(str(wrapper_diagnostics.get('fileCount', 'n/a')))} · warnings={html.escape(str(wrapper_diagnostics.get('warningCount', 'n/a')))} · latest=<code>{html.escape(str(wrapper_diagnostics.get('latestPath', 'n/a')))}</code></p><p>Local-only, redacts common secret keys, and excludes raw audio/screenshots/cookies.</p></section>
<section class=\"panel\"><h2>Native tray contract</h2><p>Status: {html.escape(str(tray.get('status', 'missing')))} · mode={html.escape(str(tray.get('mode', 'n/a')))} · recommended={html.escape(str((tray.get('packagingCandidates') or [{}])[0].get('id', 'n/a') if isinstance(tray.get('packagingCandidates'), list) and tray.get('packagingCandidates') else 'n/a'))}</p><ul>{tray_item_html}</ul></section>
<section class=\"panel\"><h2>Tray readiness</h2><p>Status: {html.escape(str(tray_ready.get('status', 'missing')))} · gates={html.escape(str(tray_ready.get('passedCount', 0)))}/{html.escape(str(tray_ready.get('totalCount', 0)))} · failed={html.escape(', '.join(map(str, tray_ready.get('failedGateIds', []) or [])) or 'none')}</p><p>{html.escape(str(tray_ready.get('recommendedNext', 'n/a')))}</p></section>
<section class=\"panel\"><h2>Packaging preflight</h2><p>Status: {html.escape(str(packaging.get('status', 'missing')))} · recommendation={html.escape(str(packaging.get('recommendation', 'n/a')))} · mode={html.escape(str(packaging.get('mode', 'n/a')))}</p><p>{html.escape(str(packaging.get('rationale', 'n/a')))}</p></section>
<section class=\"panel\"><h2>Electron fallback plan</h2><p>Status: {html.escape(str(electron.get('status', 'missing')))} · recommendation={html.escape(str(electron.get('recommendation', 'n/a')))} · target=<code>{html.escape(str(electron.get('intendedDirectoryIfApprovedLater', 'n/a')))}</code></p><p>Planning-only: install={html.escape(str(electron.get('packageInstallPerformedNow', False)))} · scaffold={html.escape(str(electron.get('scaffoldCreatedNow', False)))} · persistent={html.escape(str(electron.get('persistentProcessStartedNow', False)))}</p></section>
<section class=\"panel\"><h2>Wrapper test matrix</h2><p>Status: {html.escape(str(matrix.get('status', 'missing')))} · tests={html.escape(str(matrix.get('passedCount', 0)))}/{html.escape(str(matrix.get('totalCount', 0)))} · failed={html.escape(', '.join(map(str, matrix.get('failedIds', []) or [])) or 'none')} · finalPauseAll={html.escape(str(matrix.get('finalPauseAll', 'n/a')))}</p></section>
<section class=\"panel\"><h2>Operations docs</h2><p>Status: {html.escape(str(ops_docs.get('status', 'missing')))} · commands={html.escape(str(ops_docs.get('commandCount', 'n/a')))} · path=<code>{html.escape(str(ops_docs.get('operationsPath', 'n/a')))}</code></p><p>Consolidates wrapper commands, safety invariants, packaging decision, and rollback path.</p></section>
<section class=\"panel\"><h2>Audit viewer</h2><p>Status: {html.escape(str(audit.get('status', 'missing')))} · sources={html.escape(str(audit.get('sourceCount', 'n/a')))} · events={html.escape(str(audit.get('eventCount', 'n/a')))} · blocked={html.escape(str(audit.get('blockedCount', 'n/a')))} · sensitive={html.escape(str(audit.get('sensitiveCount', 'n/a')))}</p><p>Summarizes local audit ledgers only; no external writes or sensitive actions.</p></section>
<section class=\"panel\"><h2>Companion home</h2><p>Status: {html.escape(str(home.get('status', 'missing')))} · cards={html.escape(str(home.get('cardCount', 'n/a')))} · resource={html.escape(str(home.get('resourcePressure', 'n/a')))} · pauseAll={html.escape(str(home.get('pauseAll', 'n/a')))}</p><p>Compact landing summary for future tray/dashboard UI.</p></section>
<section class=\"panel\"><h2>Home routes</h2><p>Status: {html.escape(str(home_routes_panel.get('status', 'missing')))} · <code>/home-summary.json</code>={html.escape(str((home_routes_panel.get('routes', {}).get('/home-summary.json', {}) or {}).get('exists', 'n/a')))} · <code>/home.md</code>={html.escape(str((home_routes_panel.get('routes', {}).get('/home.md', {}) or {}).get('exists', 'n/a')))}</p><p>Preview-server routes for the compact tray/dashboard landing summary.</p></section>
<section class=\"panel\"><h2>Service recovery drill</h2><p>Status: {html.escape(str(recovery.get('status', 'missing')))} · checks={html.escape(str(recovery.get('passedCount', 0)))}/{html.escape(str(recovery.get('checkCount', 0)))} · warnings={html.escape(', '.join(map(str, recovery.get('warningIds', []) or [])) or 'none')}</p><p>Dry-run playbook only; no service changes are executed.</p></section>
<section class=\"panel\"><h2>Multi-agent board</h2><p>Status: {html.escape(str(board.get('status', 'missing')))} · activeRoles={html.escape(str(board.get('activeRoleCount', 0)))}/{html.escape(str(board.get('roleCount', 0)))} · reports={html.escape(str(len([r for r in board.get('reports', []) if isinstance(r, dict) and r.get('exists')])))} · resource={html.escape(str(board.get('resourcePressure', 'n/a')))}</p><p>Main persona keeps final judgment; specialists remain proposal/build/audit roles.</p></section>
<section class=\"panel\"><h2>Physical scenario matrix</h2><p>Status: {html.escape(str(physical_scenarios.get('status', 'missing')))} · scenarios={html.escape(str(physical_scenarios.get('passedCount', 0)))}/{html.escape(str(physical_scenarios.get('scenarioCount', 0)))} · failed={html.escape(', '.join(map(str, physical_scenarios.get('failedIds', []) or [])) or 'none')}</p><p>Simulator-only coverage for allowlist, T2/T3 blocks, and schema failures.</p></section>
<section class=\"panel\"><h2>Next connector queue</h2><p>Status: {html.escape(str(queue.get('status', 'missing')))} · selected={html.escape(str((queue.get('selected') or {}).get('id', 'none')))} · ranked={html.escape(str(len(queue.get('ranked', []) or [])))} · completed={html.escape(str(len(queue.get('completed', []) or [])))} · gated={html.escape(str(len(queue.get('blockedImportant', []) or [])))}</p><p>Ranks safe reversible follow-up work, skips completed connectors, and keeps approval-gated paths blocked.</p></section>
<section class=\"panel\"><h2>Voice/body readiness</h2><p>Status: {html.escape(str(voice_body_panel.get('status', 'missing')))} · gates={html.escape(str((voice_body_panel.get('readiness') or {}).get('readyCount', 0)))}/{html.escape(str((voice_body_panel.get('readiness') or {}).get('gateCount', 0)))} · recording={html.escape(str((voice_body_panel.get('summary') or {}).get('recordingNow', False)))} · alwaysOn={html.escape(str((voice_body_panel.get('summary') or {}).get('alwaysOnMicEnabled', False)))}</p><p>Manual-calibration-only voice/body path; no recording or persistent listener.</p></section>
<section class=\"panel\"><h2>Multi-agent handoff rules</h2><p>Status: {html.escape(str(handoff_panel.get('status', 'missing')))} · rules={html.escape(str(handoff_panel.get('ruleCount', 0)))} · activeRoles={html.escape(str(handoff_panel.get('activeRoles', 0)))}/{html.escape(str(handoff_panel.get('roleCount', 0)))} · selectedByQueue={html.escape(str(handoff_panel.get('selectedByQueue', False)))}</p><p>Defines when to use specialist agents while main persona keeps final judgment.</p></section>
<section class=\"panel\"><h2>Approval gate register</h2><p>Status: {html.escape(str(approval_panel.get('status', 'missing')))} · gated={html.escape(str(approval_panel.get('approvalGatedCount', 0)))}/{html.escape(str(approval_panel.get('gateCount', 0)))} · queueBlocked={html.escape(str(len(approval_panel.get('queueBlockedImportant', []) or [])))}</p><p>Lists blocked sensitive paths and the exact unblock requirements.</p></section>
<section class=\"panel\"><h2>Release readiness</h2><p>Status: {html.escape(str(release_panel.get('status', 'missing')))} · level={html.escape(str((release_panel.get('overall') or {}).get('level', 'n/a')))} · score={html.escape(str((release_panel.get('overall') or {}).get('score', 0)))}/{html.escape(str((release_panel.get('overall') or {}).get('max', 0)))} · blockers={html.escape(str(len(release_panel.get('hardBlockers', []) or [])))}</p><p>Productization maturity scorecard; no permissions or packaging actions performed.</p></section>
<section class=\"panel\"><h2>Morning progress digest</h2><p>Status: {html.escape(str(digest_panel.get('status', 'missing')))} · level={html.escape(str((digest_panel.get('release') or {}).get('level', 'n/a')))} · completed={html.escape(str((digest_panel.get('queue') or {}).get('completedCount', 0)))} · blockers={html.escape(str(len(digest_panel.get('hardBlockers', []) or [])))}</p><p>Local-only digest for Lee-facing summary; not externally sent by the script.</p></section>
<section class=\"panel\"><h2>Decision boundary packet</h2><p>Status: {html.escape(str(decision_panel.get('status', 'missing')))} · options={html.escape(str(len(decision_panel.get('options', []) or [])))} · gates={html.escape(str(decision_panel.get('approvalGatedCount', 0)))}/{html.escape(str(decision_panel.get('approvalGateCount', 0)))} · release={html.escape(str((decision_panel.get('release') or {}).get('level', 'n/a')))}</p><p>Approval text, rollback, and risk packet for the next productization/privacy boundary.</p></section>
<section class=\"panel\"><h2>Electron scaffold</h2><p>Status: {html.escape(str(electron_panel.get('status', 'missing')))} · dependencyInstall={html.escape(str(electron_panel.get('dependencyInstallPerformed', 'n/a')))} · canRun={html.escape(str(electron_panel.get('canRunNow', 'n/a')))}</p><p>Approved desktop shell scaffold; dependencies installed and smoke-tested.</p></section>
<section class=\"panel\"><h2>Electron menu</h2><p>Status: {html.escape(str(electron_menu_panel.get('status', 'missing')))} · items={html.escape(str(electron_menu_panel.get('menuItemCount', 'n/a')))} · wired={html.escape(str(electron_menu_panel.get('wiredInMainProcess', 'n/a')))}</p><p>Native menu wiring for dashboard/status/pause/resume actions.</p></section>
<section class=\"panel\"><h2>Electron tray</h2><p>Status: {html.escape(str(electron_tray_panel.get('status', 'missing')))} · items={html.escape(str(electron_tray_panel.get('trayItemCount', 'n/a')))} · dynamicStates={html.escape(str(len(electron_tray_panel.get('dynamicStates', []) or [])))}</p><p>Tray contract with ok/paused/alert icons and pause/resume actions.</p></section>
<section class=\"panel\"><h2>Privacy gates</h2><p>Gateway persistence is enabled. Sensitive capabilities are Lee-approved; T3 dangerous physical actions remain blocked and actions are still logged/resource-gated.</p></section>
</main></body></html>"""


def main() -> None:
    status = build_status()
    JSON_OUT.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_doc = render(status)
    HTML_OUT.write_text(html_doc, encoding="utf-8")
    CANVAS_DOC.parent.mkdir(parents=True, exist_ok=True)
    CANVAS_DOC.write_text(html_doc, encoding="utf-8")
    print(json.dumps({"ok": True, "statusJson": str(JSON_OUT), "html": str(HTML_OUT), "embedRef": DOC_ID}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
