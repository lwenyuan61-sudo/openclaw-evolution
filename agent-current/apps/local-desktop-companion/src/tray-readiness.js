import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_tray_readiness_status.json');

const REQUIRED = [
  { id: 'app-shell', path: 'state/app_shell_status.json', check: (j) => j.status === 'ok' },
  { id: 'permission-controls', path: 'state/app_control_schema.json', check: (j) => j.status === 'ok' && Array.isArray(j.controls) && j.controls.length >= 8 },
  { id: 'pause-state', path: 'state/app_control_state.json', check: (j) => j.status === 'ready' && j.pauseAll === false },
  { id: 'service-health', path: 'state/service_health_status.json', check: (j) => j.status === 'ok' && j.gatewayConnectivityOk === true },
  { id: 'wrapper-status', path: 'state/desktop_app_wrapper_status.json', check: (j) => j.status === 'ready' },
  { id: 'control-preview', path: 'state/desktop_wrapper_control_preview_status.json', check: (j) => ['ready', 'previewed', 'requires-gate'].includes(j.status) && (j.safety?.executesSensitiveAction === false || j.executesSensitiveAction === false) },
  { id: 'control-endpoint', path: 'state/desktop_wrapper_control_endpoint_status.json', check: (j) => ['ready', 'passed'].includes(j.status) && j.mutatesAppControlState === false },
  { id: 'diagnostics', path: 'state/desktop_wrapper_diagnostics_status.json', check: (j) => j.status === 'ok' && j.privacy?.localOnly === true },
  { id: 'tray-contract', path: 'state/desktop_wrapper_tray_contract_status.json', check: (j) => j.status === 'ready-for-packaging-design' && j.safety?.dependencyInstall === false },
];

function readJson(rel) {
  const abs = path.join(WORKSPACE, rel);
  try {
    return { exists: true, json: JSON.parse(fs.readFileSync(abs, 'utf8')), abs };
  } catch (error) {
    return { exists: fs.existsSync(abs), json: null, abs, error: `${error.name}: ${error.message}` };
  }
}

function main() {
  const timestamp = new Date().toISOString();
  const gates = REQUIRED.map((gate) => {
    const got = readJson(gate.path);
    let passed = false;
    let reason = null;
    if (!got.exists) {
      reason = 'missing-file';
    } else if (!got.json) {
      reason = got.error ?? 'invalid-json';
    } else {
      try {
        passed = Boolean(gate.check(got.json));
        reason = passed ? 'ok' : 'predicate-failed';
      } catch (error) {
        reason = `${error.name}: ${error.message}`;
      }
    }
    return {
      id: gate.id,
      path: gate.path,
      passed,
      reason,
    };
  });
  const failed = gates.filter((gate) => !gate.passed);
  const plan = {
    timestamp,
    status: failed.length === 0 ? 'ready-for-native-scaffold-decision' : 'not-ready',
    mode: 'tray-readiness-diagnostics-no-install',
    passedCount: gates.length - failed.length,
    totalCount: gates.length,
    failedGateIds: failed.map((gate) => gate.id),
    gates,
    recommendedNext: failed.length === 0 ? 'Ask/decide whether to scaffold Tauri; do not install dependencies during quiet-hours without explicit action.' : 'Fix failed readiness gates before packaging.',
    safety: {
      dependencyInstall: false,
      persistentInstall: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(plan, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: failed.length === 0, out: OUT, status: plan.status, passedCount: plan.passedCount, totalCount: plan.totalCount, failedGateIds: plan.failedGateIds }, null, 2));
}

main();
