import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_next_connector_queue_status.json');

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function exists(rel) {
  try { return fs.existsSync(path.join(WORKSPACE, rel)); } catch { return false; }
}

function card(app, id) {
  return (app.cards || []).find((item) => item.id === id) || null;
}

function warningCount(app) {
  return (app.cards || []).filter((item) => ['warn', 'warning', 'critical', 'error'].includes(item.level)).length;
}

function gateReason(candidate, facts) {
  const reasons = [];
  if (candidate.needsApproval && !facts.dependencyInstallApproved && !facts.alwaysOnMicApproved && !facts.realPhysicalApproved) reasons.push('approval-required');
  if (candidate.gpuHeavy && facts.resourcePressure !== 'ok') reasons.push('resource-pressure');
  if (candidate.externalWrite && !facts.externalSendApproved) reasons.push('external-write-gated');
  if (candidate.mic && !facts.alwaysOnMicApproved) reasons.push('always-on-mic-not-approved');
  if (candidate.realPhysical && !facts.realPhysicalApproved) reasons.push('real-physical-action-not-approved');
  if (candidate.dependencyInstall && !facts.dependencyInstallApproved) reasons.push('dependency-install-gated');
  return reasons;
}

function scoreCandidate(candidate, facts) {
  let score = candidate.baseScore;
  if (candidate.localOnly) score += 5;
  if (candidate.reversible) score += 4;
  if (candidate.verifiedPath) score += 3;
  if (candidate.userValue === 'high') score += 3;
  if (candidate.appShellValue) score += 2;
  if (candidate.resilienceValue) score += 2;
  if (candidate.embodimentValue) score += 2;
  if (candidate.multiAgentValue) score += 1;
  if (facts.warningCount > 0 && candidate.handlesWarnings) score += 2;
  if (facts.resourcePressure !== 'ok' && candidate.gpuHeavy) score -= 20;
  if (candidate.noise === 'low') score += 1;
  if (candidate.noise === 'high') score -= 4;
  const gates = gateReason(candidate, facts);
  if (gates.length) score -= 100;
  return { score, gates };
}

function main() {
  const timestamp = new Date().toISOString();
  const app = readJson('state/app_shell_status.json', { cards: [] });
  const resource = readJson('core/resource-state.json');
  const control = readJson('state/app_control_state.json');
  const upgrade = readJson('autonomy/upgrade-state.json');
  const continuity = readJson('autonomy/continuity-state.json');
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json');
  const physical = readJson('state/desktop_wrapper_physical_scenario_matrix_status.json');
  const board = readJson('state/desktop_wrapper_multi_agent_board_status.json');
  const packaging = readJson('state/desktop_wrapper_packaging_preflight_status.json');
  const voiceBody = readJson('state/desktop_wrapper_voice_body_readiness_status.json');
  const handoff = readJson('state/desktop_wrapper_multi_agent_handoff_rules_status.json');
  const approval = readJson('state/desktop_wrapper_approval_gate_register_status.json');
  const releaseReadiness = readJson('state/desktop_wrapper_release_readiness_status.json');
  const broad = readJson('state/lee_broad_approval_state.json', { scope: {} });
  const scope = broad.scope || {};

  const completionSignals = {
    'voice-body-readiness-matrix': voiceBody.status === 'ready' && voiceBody.readiness?.readyCount === voiceBody.readiness?.gateCount,
    'decision-queue-feedback-loop': true,
    'physical-simulator-coverage-next': physical.status === 'passed' && Number(physical.scenarioCount ?? 0) >= 11,
    'multi-agent-handoff-ruleset': handoff.status === 'ready' && Number(handoff.ruleCount ?? 0) >= 6,
    'approval-gate-register': approval.status === 'ready' && Number(approval.gateCount ?? 0) >= 8,
    'release-readiness-scorecard': releaseReadiness.status === 'ready' && releaseReadiness.overall?.level === 'advanced-prototype',
  };

  const facts = {
    resourcePressure: resource.resourcePressure?.level ?? 'unknown',
    pauseAll: Boolean(control.pauseAll),
    cardCount: Array.isArray(app.cards) ? app.cards.length : 0,
    warningCount: warningCount(app),
    alwaysOnMicApproved: scope.alwaysOnVoiceWake === true || scope.microphone === true,
    realPhysicalApproved: scope.realPhysicalControl === true,
    dependencyInstallApproved: scope.dependencyInstall === true || scope.scaffoldCreation === true,
    externalSendApproved: scope.externalSend === true,
    paidOrGpuHeavyApproved: scope.paidOrGpuHeavyWork === true,
    testMatrixPassed: matrix.status === 'passed',
    physicalMatrixPassed: physical.status === 'passed',
    multiAgentReady: board.status === 'ready',
    packagingRecommendation: packaging.recommendation ?? 'unknown',
    currentFocus: continuity.currentFocus ?? upgrade.currentFocus ?? null,
    completedConnectorCount: Object.values(completionSignals).filter(Boolean).length,
    completionAwareQueue: true,
    leeBroadApproval: broad.status ?? 'missing',
  };

  const candidates = [
    {
      id: 'voice-body-readiness-matrix',
      title: 'Voice/body readiness matrix without recording',
      baseScore: 12,
      localOnly: true,
      reversible: true,
      verifiedPath: true,
      appShellValue: true,
      userValue: 'high',
      handlesWarnings: true,
      noise: 'low',
      description: 'Summarize microphone, calibration, wake-listener, visible indicator, and approval gates without recording audio.',
    },
    {
      id: 'decision-queue-feedback-loop',
      title: 'Decision queue feedback loop',
      baseScore: 11,
      localOnly: true,
      reversible: true,
      verifiedPath: true,
      appShellValue: true,
      resilienceValue: true,
      userValue: 'high',
      noise: 'low',
      description: 'Use this queue as a stable selector for next wake connector decisions and reduce repetitive maintain loops.',
    },
    {
      id: 'physical-simulator-coverage-next',
      title: 'Physical simulator coverage expansion',
      baseScore: 9,
      localOnly: true,
      reversible: true,
      verifiedPath: facts.physicalMatrixPassed,
      embodimentValue: true,
      userValue: 'high',
      noise: 'low',
      description: 'Add more simulator-only scenario coverage such as kill-switch flag dry-run and visible-UI-required T2 expectations.',
    },
    {
      id: 'multi-agent-handoff-ruleset',
      title: 'Multi-agent handoff ruleset hardening',
      baseScore: 8,
      localOnly: true,
      reversible: true,
      verifiedPath: facts.multiAgentReady,
      multiAgentValue: true,
      userValue: 'medium',
      noise: 'low',
      description: 'Make explicit when main persona should spawn architect/builder/auditor instead of doing sequential local work.',
    },
    {
      id: 'approval-gate-register',
      title: 'Approval gate register',
      baseScore: 7,
      localOnly: true,
      reversible: true,
      verifiedPath: true,
      appShellValue: true,
      resilienceValue: true,
      userValue: 'high',
      noise: 'low',
      description: 'Summarize all approval-gated sensitive paths and exact unblock requirements without changing permissions.',
    },
    {
      id: 'release-readiness-scorecard',
      title: 'Desktop companion release readiness scorecard',
      baseScore: 10,
      localOnly: true,
      reversible: true,
      verifiedPath: facts.testMatrixPassed,
      appShellValue: true,
      resilienceValue: true,
      userValue: 'high',
      handlesWarnings: true,
      noise: 'low',
      description: 'Compute a compact maturity/readiness scorecard for app shell, controls, voice/body, physical simulator, service resilience, packaging, and approval gates.',
    },
    {
      id: 'morning-progress-digest',
      title: 'Morning progress digest snapshot',
      baseScore: 9,
      localOnly: true,
      reversible: true,
      verifiedPath: facts.testMatrixPassed,
      appShellValue: true,
      resilienceValue: true,
      userValue: 'high',
      noise: 'low',
      description: 'Create a compact local-only progress digest from verified connector state and remaining blockers; no external send by default.',
    },
    {
      id: 'electron-scaffold',
      title: 'Electron scaffold',
      baseScore: 14,
      localOnly: true,
      reversible: false,
      verifiedPath: false,
      appShellValue: true,
      dependencyInstall: true,
      needsApproval: true,
      userValue: 'high',
      noise: 'medium',
      description: 'Blocked until Lee explicitly approves dependency install/scaffold.',
    },
    {
      id: 'always-on-voice-wake',
      title: 'Always-on voice wake',
      baseScore: 15,
      localOnly: true,
      reversible: false,
      verifiedPath: false,
      mic: true,
      needsApproval: true,
      userValue: 'high',
      noise: 'high',
      description: 'Blocked until separate explicit always-on microphone approval and visible indicator.',
    },
    {
      id: 'real-device-actuation',
      title: 'Real physical device actuation',
      baseScore: 16,
      localOnly: false,
      reversible: false,
      verifiedPath: false,
      realPhysical: true,
      needsApproval: true,
      userValue: 'high',
      noise: 'high',
      description: 'Blocked until per-device allowlist, UI visibility, kill switch, and explicit approval.',
    },
  ];

  const ranked = candidates.map((candidate) => {
    const { score, gates } = scoreCandidate(candidate, facts);
    const completed = Boolean(completionSignals[candidate.id]);
    const completionPenalty = completed ? 50 : 0;
    return { ...candidate, score: score - completionPenalty, gated: gates.length > 0, gates, completed };
  }).sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));

  const actionable = ranked.filter((item) => !item.gated && !item.completed && facts.resourcePressure === 'ok' && !facts.pauseAll);
  const selected = actionable[0] ?? null;
  const doc = {
    timestamp,
    status: selected ? 'ready' : 'blocked',
    mode: 'next-connector-decision-queue',
    facts,
    selected: selected ? {
      id: selected.id,
      title: selected.title,
      score: selected.score,
      nextStep: selected.description,
    } : null,
    ranked: ranked.map((item) => ({ id: item.id, title: item.title, score: item.score, gated: item.gated, completed: item.completed, gates: item.gates, description: item.description })),
    completed: ranked.filter((item) => item.completed).map((item) => ({ id: item.id, title: item.title })),
    blockedImportant: ranked.filter((item) => item.gated).map((item) => ({ id: item.id, gates: item.gates })),
    safety: {
      selectorOnly: true,
      executedSelectedConnector: false,
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
    inputs: {
      appShellStatusExists: exists('state/app_shell_status.json'),
      testMatrixExists: exists('state/desktop_wrapper_test_matrix_status.json'),
      physicalMatrixExists: exists('state/desktop_wrapper_physical_scenario_matrix_status.json'),
      multiAgentBoardExists: exists('state/desktop_wrapper_multi_agent_board_status.json'),
      voiceBodyReadinessExists: exists('state/desktop_wrapper_voice_body_readiness_status.json'),
      handoffRulesExists: exists('state/desktop_wrapper_multi_agent_handoff_rules_status.json'),
      approvalGateRegisterExists: exists('state/desktop_wrapper_approval_gate_register_status.json'),
      releaseReadinessExists: exists('state/desktop_wrapper_release_readiness_status.json'),
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, selected: doc.selected?.id ?? null, rankedCount: doc.ranked.length, resourcePressure: facts.resourcePressure }, null, 2));
}

main();
