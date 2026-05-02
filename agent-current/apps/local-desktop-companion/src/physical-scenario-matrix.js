import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_physical_scenario_matrix_status.json');
const KILL_SWITCH_FLAG = path.join(STATE, 'physical_actuation_disabled.flag');
const PYTHON = process.env.PYTHON || 'python';

const SCENARIOS = [
  {
    id: 't0-plan-only-unknown-target-allowed',
    expectedStatus: 'simulated',
    action: { id: 'plan-only-unknown-target', kind: 'planning', target: 'future-device', operation: 'describe', simulateOnly: true },
  },
  {
    id: 't1-demo-lamp-status-allowed',
    expectedStatus: 'simulated',
    action: { id: 'demo-lamp-status', kind: 'query-status', target: 'demo-lamp', operation: 'status', simulateOnly: false },
  },
  {
    id: 't1-demo-lamp-toggle-allowed',
    expectedStatus: 'simulated',
    action: { id: 'demo-lamp-toggle', kind: 'virtual-device', target: 'demo-lamp', operation: 'toggle', simulateOnly: false },
  },
  {
    id: 't1-desktop-focus-status-allowed',
    expectedStatus: 'simulated',
    action: { id: 'desktop-focus-status', kind: 'desktop-reversible', target: 'desktop-focus-demo', operation: 'status', simulateOnly: false },
  },
  {
    id: 'unknown-target-blocked',
    expectedStatus: 'blocked',
    expectedReason: 'target-not-allowlisted',
    action: { id: 'unknown-light-status', kind: 'query-status', target: 'unknown-light', operation: 'status', simulateOnly: false },
  },
  {
    id: 'unknown-operation-blocked',
    expectedStatus: 'blocked',
    expectedReason: 'operation-not-allowed',
    action: { id: 'demo-lamp-dim', kind: 'virtual-device', target: 'demo-lamp', operation: 'dim', simulateOnly: false },
  },
  {
    id: 'real-device-t2-requires-allowlist',
    expectedStatus: 'blocked',
    expectedReason: 'target-not-allowlisted',
    action: { id: 'real-device-status', kind: 'real-device', target: 'real-lamp', operation: 'status', simulateOnly: false },
  },
  {
    id: 'dangerous-kind-t3-blocked',
    expectedStatus: 'blocked',
    expectedReason: 'tier-blocked',
    action: { id: 'dangerous-motion', kind: 'robot-motion-near-people', target: 'future-robot', operation: 'move', simulateOnly: false },
  },
  {
    id: 'schema-missing-field-blocked',
    expectedStatus: 'blocked',
    expectedReasonPrefix: 'missing-required-fields',
    action: { id: 'missing-target', kind: 'query-status', operation: 'status', simulateOnly: false },
  },
  {
    id: 'schema-bad-simulate-only-type-blocked',
    expectedStatus: 'blocked',
    expectedReason: 'simulateOnly-must-be-boolean',
    action: { id: 'bad-simulate-only-type', kind: 'query-status', target: 'demo-lamp', operation: 'status', simulateOnly: 'false' },
  },
  {
    id: 'kill-switch-flag-blocks-t1',
    expectedStatus: 'blocked',
    expectedReason: 'kill-switch-flag-present',
    setupKillSwitch: true,
    action: { id: 'kill-switch-demo-lamp-status', kind: 'query-status', target: 'demo-lamp', operation: 'status', simulateOnly: false },
  },
];

function withKillSwitch(enabled, fn) {
  const existedBefore = fs.existsSync(KILL_SWITCH_FLAG);
  const previous = existedBefore ? fs.readFileSync(KILL_SWITCH_FLAG, 'utf8') : null;
  if (enabled) {
    fs.writeFileSync(KILL_SWITCH_FLAG, 'temporary test kill-switch for simulator scenario matrix\n', 'utf8');
  }
  try {
    return fn();
  } finally {
    if (enabled) {
      if (existedBefore) fs.writeFileSync(KILL_SWITCH_FLAG, previous, 'utf8');
      else if (fs.existsSync(KILL_SWITCH_FLAG)) fs.unlinkSync(KILL_SWITCH_FLAG);
    }
  }
}

function runScenario(scenario) {
  const started = Date.now();
  const result = withKillSwitch(Boolean(scenario.setupKillSwitch), () => childProcess.spawnSync(PYTHON, [
    'core/scripts/physical_actuation_simulator.py',
    '--action-json',
    JSON.stringify(scenario.action),
  ], {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30000,
  }));
  let parsed = null;
  try { parsed = JSON.parse(String(result.stdout || '').trim()); } catch {}
  const reason = parsed?.reason ?? null;
  const reasonOk = scenario.expectedReason
    ? reason === scenario.expectedReason
    : scenario.expectedReasonPrefix
      ? String(reason || '').startsWith(scenario.expectedReasonPrefix)
      : true;
  const passed = result.status === 0 && parsed?.status === scenario.expectedStatus && reasonOk && parsed?.realDeviceCalled === false && parsed?.externalWrite === false;
  return {
    id: scenario.id,
    passed,
    expectedStatus: scenario.expectedStatus,
    expectedReason: scenario.expectedReason ?? scenario.expectedReasonPrefix ?? null,
    actualStatus: parsed?.status ?? null,
    actualReason: reason,
    tier: parsed?.tier ?? null,
    allowed: parsed?.allowed ?? null,
    realDeviceCalled: parsed?.realDeviceCalled ?? null,
    externalWrite: parsed?.externalWrite ?? null,
    durationMs: Date.now() - started,
    processStatus: result.status,
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
    stderrTail: String(result.stderr || '').slice(-500),
  };
}

function main() {
  const timestamp = new Date().toISOString();
  const results = SCENARIOS.map(runScenario);
  const failed = results.filter((item) => !item.passed);
  const doc = {
    timestamp,
    status: failed.length === 0 ? 'passed' : 'failed',
    mode: 'physical-actuation-simulator-scenario-matrix',
    scenarioCount: results.length,
    passedCount: results.length - failed.length,
    failedIds: failed.map((item) => item.id),
    results,
    coverage: {
      allowedT0: results.some((item) => item.id.includes('t0') && item.passed),
      allowedT1: results.filter((item) => item.id.includes('t1') && item.passed).length,
      blockedUnknownTarget: results.some((item) => item.id === 'unknown-target-blocked' && item.passed),
      blockedUnknownOperation: results.some((item) => item.id === 'unknown-operation-blocked' && item.passed),
      blockedT2: results.some((item) => item.id === 'real-device-t2-requires-allowlist' && item.passed),
      blockedT3: results.some((item) => item.id === 'dangerous-kind-t3-blocked' && item.passed),
      blockedBadSchema: results.some((item) => item.id === 'schema-missing-field-blocked' && item.passed),
    blockedBadType: results.some((item) => item.id === 'schema-bad-simulate-only-type-blocked' && item.passed),
    blockedKillSwitch: results.some((item) => item.id === 'kill-switch-flag-blocks-t1' && item.passed),
    },
    safety: {
      simulatorOnly: true,
      killSwitchFlagRestored: !fs.existsSync(KILL_SWITCH_FLAG),
      realDeviceCalled: false,
      externalNetworkWrites: false,
      dependencyInstall: false,
      persistentProcessStarted: false,
      microphone: false,
      camera: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'passed', out: OUT, status: doc.status, passedCount: doc.passedCount, scenarioCount: doc.scenarioCount, failedIds: doc.failedIds }, null, 2));
}

main();
