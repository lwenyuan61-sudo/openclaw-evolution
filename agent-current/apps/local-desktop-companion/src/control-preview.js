import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const CONTROL_SCHEMA = path.join(STATE, 'app_control_schema.json');
const CONTROL_STATE = path.join(STATE, 'app_control_state.json');
const OUT = path.join(STATE, 'desktop_wrapper_control_preview_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_control_preview_audit.jsonl');

const SENSITIVE_DIRECT_ACTIONS = new Set([
  'enable-always-on-mic',
  'enable-camera-continuous',
  'send-external-message',
  'real-physical-actuation',
  'paid-api-call',
  'gpu-heavy-local-model',
]);

function readJson(file, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function atomicWriteJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp-${process.pid}-${Date.now()}`;
  fs.writeFileSync(tmp, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  fs.renameSync(tmp, file);
}

function appendJsonl(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, `${JSON.stringify(doc)}\n`, 'utf8');
}

function argValue(flag, fallback = undefined) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
}

function getControls(schema) {
  return Array.isArray(schema.controls) ? schema.controls : [];
}

function findControl(schema, id) {
  return getControls(schema).find((control) => control && control.id === id) ?? null;
}

function buildStatus() {
  const schema = readJson(CONTROL_SCHEMA, { status: 'missing', controls: [] });
  const state = readJson(CONTROL_STATE, { status: 'missing' });
  const controls = getControls(schema);
  return {
    timestamp: new Date().toISOString(),
    status: ['ok', 'lee-approved-controls'].includes(schema.status) && ['ready', 'lee-approved'].includes(state.status) ? 'ready' : 'warn',
    mode: 'wrapper-control-preview-only',
    controlCount: controls.length,
    pauseAll: Boolean(state.pauseAll),
    enabledControls: Array.isArray(state.enabledControls) ? state.enabledControls : [],
    dryRunControls: Array.isArray(state.dryRunControls) ? state.dryRunControls : [],
    confirmationRequired: Array.isArray(state.confirmationRequired) ? state.confirmationRequired : [],
    safePreviewActions: {
      'preview-pause-all': 'Preview setting pauseAll=true; no state mutation by default.',
      'preview-resume-all': 'Preview setting pauseAll=false; no state mutation by default.',
      'preview-control': 'Preview one control by id and show whether it would be enabled, dry-run, or blocked.',
      'refresh-dashboard': 'Read-only dashboard/status refresh affordance for future UI.',
    },
    reversibleExecuteActions: {
      'execute-pause-all': 'Set app_control_state.pauseAll=true. Reversible with execute-resume-all; no sensitive organs are started.',
      'execute-resume-all': 'Set app_control_state.pauseAll=false. Reversible with execute-pause-all; does not bypass permission gates.',
    },
    blockedDirectActions: Array.isArray(schema.blockedDirectActions) ? schema.blockedDirectActions : Array.from(SENSITIVE_DIRECT_ACTIONS),
    paths: {
      schema: CONTROL_SCHEMA,
      state: CONTROL_STATE,
      out: OUT,
      audit: AUDIT,
    },
    safety: {
      mutatesAppControlState: false,
      executesSensitiveAction: false,
      externalNetworkWrites: false,
      persistentInstall: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
}

function previewPause(nextPauseAll) {
  const status = buildStatus();
  return {
    timestamp: new Date().toISOString(),
    event: nextPauseAll ? 'preview-pause-all' : 'preview-resume-all',
    status: 'previewed',
    allowed: true,
    mutatesAppControlState: false,
    currentPauseAll: status.pauseAll,
    previewPauseAll: nextPauseAll,
    affectedControlIds: status.enabledControls,
    note: 'Preview only. A future execute path must deliberately write app_control_state.json and should remain reversible.',
    safety: status.safety,
  };
}

function executePause(nextPauseAll) {
  const state = readJson(CONTROL_STATE, { status: 'missing' });
  if (state.status !== 'ready') {
    return {
      timestamp: new Date().toISOString(),
      event: nextPauseAll ? 'execute-pause-all' : 'execute-resume-all',
      status: 'blocked',
      allowed: false,
      reason: 'app-control-state-not-ready',
      mutatesAppControlState: false,
      executesSensitiveAction: false,
    };
  }
  const previousPauseAll = Boolean(state.pauseAll);
  const nextState = {
    ...state,
    timestamp: new Date().toISOString(),
    pauseAll: nextPauseAll,
    lastAction: nextPauseAll ? 'wrapper-execute-pause-all' : 'wrapper-execute-resume-all',
    lastChangedBy: 'apps/local-desktop-companion/src/control-preview.js',
  };
  atomicWriteJson(CONTROL_STATE, nextState);
  return {
    timestamp: new Date().toISOString(),
    event: nextPauseAll ? 'execute-pause-all' : 'execute-resume-all',
    status: 'executed',
    allowed: true,
    previousPauseAll,
    pauseAll: nextPauseAll,
    reversibleWith: nextPauseAll ? 'execute-resume-all' : 'execute-pause-all',
    mutatesAppControlState: true,
    executesSensitiveAction: false,
    externalNetworkWrites: false,
    persistentInstall: false,
    microphone: false,
    camera: false,
    realPhysicalActuation: false,
  };
}

function previewControl(controlId) {
  const schema = readJson(CONTROL_SCHEMA, { status: 'missing', controls: [] });
  const control = findControl(schema, controlId);
  if (!control) {
    return {
      timestamp: new Date().toISOString(),
      event: 'preview-control',
      status: 'blocked',
      allowed: false,
      reason: 'unknown-control-id',
      controlId,
      mutatesAppControlState: false,
      executesSensitiveAction: false,
    };
  }
  const directAction = `enable-${controlId}`;
  const blockedDirect = SENSITIVE_DIRECT_ACTIONS.has(directAction) || control.dryRunOnly || control.requiresConfirmation;
  return {
    timestamp: new Date().toISOString(),
    event: 'preview-control',
    status: blockedDirect ? 'requires-gate' : 'previewed',
    allowed: !blockedDirect,
    controlId,
    label: control.label,
    category: control.category,
    currentMode: control.currentMode,
    dryRunOnly: Boolean(control.dryRunOnly),
    requiresConfirmation: Boolean(control.requiresConfirmation),
    constraints: control.constraints ?? [],
    reason: blockedDirect ? (control.reason ?? 'control requires confirmation or dry-run gate') : 'would be safe to expose as read-only/app-shell control',
    mutatesAppControlState: false,
    executesSensitiveAction: false,
  };
}

function main() {
  let result;
  if (process.argv.includes('--status')) {
    result = buildStatus();
  } else if (process.argv.includes('--preview-pause-all')) {
    result = previewPause(true);
  } else if (process.argv.includes('--preview-resume-all')) {
    result = previewPause(false);
  } else if (process.argv.includes('--preview-control')) {
    result = previewControl(argValue('--control', ''));
  } else if (process.argv.includes('--execute-pause-all')) {
    result = executePause(true);
  } else if (process.argv.includes('--execute-resume-all')) {
    result = executePause(false);
  } else {
    result = {
      ok: true,
      usage: ['--status', '--preview-pause-all', '--preview-resume-all', '--preview-control --control <id>', '--execute-pause-all', '--execute-resume-all'],
      status: buildStatus(),
    };
  }
  writeJson(OUT, result);
  appendJsonl(AUDIT, result);
  console.log(JSON.stringify(result, null, 2));
}

main();
