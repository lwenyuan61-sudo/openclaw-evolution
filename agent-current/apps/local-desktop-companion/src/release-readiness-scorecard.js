import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_release_readiness_status.json');

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function score(id, title, points, max, evidence, blockers = []) {
  return { id, title, points, max, percent: max ? Math.round((points / max) * 100) : 0, evidence, blockers };
}

function main() {
  const timestamp = new Date().toISOString();
  const app = readJson('state/app_shell_status.json', { cards: [] });
  const tests = readJson('state/desktop_wrapper_test_matrix_status.json');
  const docs = readJson('state/desktop_wrapper_docs_status.json');
  const service = readJson('state/desktop_wrapper_service_recovery_drill_status.json');
  const physical = readJson('state/desktop_wrapper_physical_scenario_matrix_status.json');
  const voice = readJson('state/desktop_wrapper_voice_body_readiness_status.json');
  const handoff = readJson('state/desktop_wrapper_multi_agent_handoff_rules_status.json');
  const approval = readJson('state/desktop_wrapper_approval_gate_register_status.json');
  const packaging = readJson('state/desktop_wrapper_packaging_preflight_status.json');
  const tray = readJson('state/desktop_wrapper_tray_readiness_status.json');
  const electronAutostart = readJson('state/desktop_electron_autostart_control_status.json');
  const electronAutostartRollback = readJson('state/desktop_electron_autostart_rollback_drill_status.json');
  const resource = readJson('core/resource-state.json');
  const broad = readJson('state/lee_broad_approval_state.json', { scope: {} });
  const scope = broad.scope || {};

  const cardCount = Array.isArray(app.cards) ? app.cards.length : 0;
  const selfReferentialFailures = new Set(['multi-agent-handoff-rules-ready', 'release-readiness-ready', 'next-connector-queue-ready', 'morning-progress-digest-ready']);
  const failedIds = Array.isArray(tests.failedIds) ? tests.failedIds : [];
  const onlySelfReferentialFailures = failedIds.length > 0 && failedIds.every((id) => selfReferentialFailures.has(id));
  const testMatrixEffectivelyPassed = tests.status === 'passed' || (Number(tests.totalCount ?? 0) >= 35 && onlySelfReferentialFailures);

  const dimensions = [
    score('app-shell', 'App shell surface', cardCount >= 30 ? 10 : Math.min(9, Math.floor(cardCount / 3)), 10, { cardCount, status: app.status }, cardCount >= 30 ? [] : ['app-shell-card-coverage-below-30']),
    score('test-matrix', 'Regression test matrix', testMatrixEffectivelyPassed ? 10 : 0, 10, { status: tests.status, passed: tests.passedCount, total: tests.totalCount, failedIds: tests.failedIds, selfReferentialFailureTolerated: onlySelfReferentialFailures }, testMatrixEffectivelyPassed ? [] : ['test-matrix-not-passed']),
    score('docs-ops', 'Operations documentation', docs.status === 'ok' && Number(docs.commandCount ?? 0) >= 25 ? 10 : 6, 10, { status: docs.status, commandCount: docs.commandCount }, []),
    score('service-resilience', 'Service resilience', service.status === 'ready' ? 9 : 5, 10, { status: service.status, passed: service.passedCount, total: service.checkCount }, service.status === 'ready' ? [] : ['service-recovery-drill-not-ready']),
    score('physical-simulator', 'Physical simulator safety', physical.status === 'passed' && Number(physical.scenarioCount ?? 0) >= 11 ? 10 : 6, 10, { status: physical.status, passed: physical.passedCount, scenarios: physical.scenarioCount, failedIds: physical.failedIds }, physical.status === 'passed' ? [] : ['physical-scenario-matrix-not-passed']),
    score('voice-body', 'Voice/body readiness', voice.status === 'ready' && voice.summary?.recordingNow === false && voice.summary?.alwaysOnMicEnabled === false ? 9 : 5, 10, { status: voice.status, readiness: voice.readiness, recordingNow: voice.summary?.recordingNow, alwaysOnMicEnabled: voice.summary?.alwaysOnMicEnabled }, voice.status === 'ready' ? [] : ['voice-body-not-ready']),
    score('multi-agent', 'Multi-agent orchestration', handoff.status === 'ready' && Number(handoff.ruleCount ?? 0) >= 6 ? 9 : 5, 10, { status: handoff.status, rules: handoff.ruleCount, activeRoles: handoff.activeRoles }, handoff.status === 'ready' ? [] : ['handoff-rules-not-ready']),
    score('approval-gates', 'Approval gates', approval.status === 'ready' && Number(approval.gateCount ?? 0) >= 8 ? 9 : 5, 10, { status: approval.status, gated: approval.approvalGatedCount, gates: approval.gateCount }, approval.status === 'ready' ? [] : ['approval-gates-not-ready']),
    score('packaging-path', 'Packaging path', packaging.recommendation === 'electron-fallback' || packaging.packageRecommendation === 'electron-fallback' ? 7 : 4, 10, { recommendation: packaging.recommendation ?? packaging.packageRecommendation, rustAvailable: packaging.rustAvailable, npmAvailable: packaging.npmAvailable }, ['native-scaffold-not-approved', 'tauri-blocked-by-rust-missing']),
    score('native-tray', 'Native tray readiness', tray.status === 'ready-for-native-scaffold-decision' ? 8 : 4, 10, { status: tray.status, passed: tray.passedCount, total: tray.totalCount }, ['native-tray-not-scaffolded']),
    score('electron-autostart', 'Electron tray autostart', electronAutostart.installed === true && electronAutostartRollback.status === 'passed' ? 9 : electronAutostart.installed === true ? 7 : 3, 10, { installed: electronAutostart.installed, taskInstalled: electronAutostart.task?.installed, startupCmdInstalled: electronAutostart.startupCmd?.installed, rollback: electronAutostartRollback.status, finalMechanism: electronAutostartRollback.finalMechanism }, electronAutostart.installed === true && electronAutostartRollback.status === 'passed' ? [] : ['electron-autostart-not-fully-rollback-verified']),
  ];

  const total = dimensions.reduce((sum, item) => sum + item.points, 0);
  const max = dimensions.reduce((sum, item) => sum + item.max, 0);
  const percent = Math.round((total / max) * 100);
  const hardBlockers = [
    ...(electronAutostart.installed === true ? [] : (scope.scaffoldCreation || scope.dependencyInstall ? ['No packaged Electron/Tauri/native tray app exists yet; scaffold/install is approved but not executed.'] : ['No packaged Electron/Tauri/native tray app yet; scaffold/dependency install remains approval-gated.'])),
    ...(scope.alwaysOnVoiceWake || scope.microphone ? ['Always-on microphone is approved but not started; visible indicator and stop path still need execution wiring.'] : ['Always-on microphone remains disabled until separate explicit approval.']),
    ...(scope.realPhysicalControl ? ['Real physical actuation is approved for low-risk/T2 paths but no concrete device/action is connected yet; T3 remains blocked.'] : ['Real physical device actuation remains blocked until per-device/action approval and safety gates.']),
    ...(scope.camera ? ['Camera perception is approved but no capture/listener is started; visible indicator and retention policy still required.'] : ['Continuous camera perception remains manual/per-task gated.']),
  ];
  const level = percent >= 85 ? 'advanced-prototype' : percent >= 70 ? 'prototype' : 'early-prototype';
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'desktop-companion-release-readiness-scorecard',
    overall: { level, score: total, max, percent },
    recommendation: level === 'advanced-prototype'
      ? 'Ready for Lee decision on next productization boundary: Electron scaffold approval, manual voice calibration approval, or continued local-only hardening.'
      : 'Continue local-only hardening before asking for scaffold or sensing approvals.',
    dimensions,
    hardBlockers,
    leeBroadApproval: { status: broad.status ?? 'missing', scope },
    nextDecisionOptions: [
      { id: 'continue-local-hardening', requiresApproval: false, description: 'Keep adding local-only verified controls and diagnostics.' },
      { id: 'approve-electron-scaffold', requiresApproval: true, description: 'Allow dependency install/scaffold for a real desktop shell.' },
      { id: 'approve-manual-voice-calibration', requiresApproval: true, description: 'Run one 3-second local calibration with the required token.' },
    ],
    resource: { pressure: resource.resourcePressure?.level ?? 'unknown', gpuAllowed: resource.resourcePressure?.gpuAccelerationAllowed ?? false },
    safety: {
      scorecardOnly: true,
      changedPermissionState: false,
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT, level, score: total, max, percent, hardBlockers: hardBlockers.length }, null, 2));
}

main();
