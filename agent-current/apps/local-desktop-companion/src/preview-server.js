import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const DASHBOARD = path.join(STATE, 'app_shell_dashboard.html');
const STATUS = path.join(STATE, 'app_shell_status.json');
const MANIFEST = path.join(APP_ROOT, 'wrapper-manifest.json');
const CONTROL_PREVIEW = path.join(STATE, 'desktop_wrapper_control_preview_status.json');
const CONTROL_ENDPOINT_STATUS = path.join(STATE, 'desktop_wrapper_control_endpoint_status.json');
const CONTROL_ENDPOINT_AUDIT = path.join(STATE, 'desktop_wrapper_control_endpoint_audit.jsonl');
const APP_CONTROL_SCHEMA = path.join(STATE, 'app_control_schema.json');
const HOME_SUMMARY = path.join(STATE, 'desktop_wrapper_home_summary.json');
const HOME_DOC = path.join(APP_ROOT, 'HOME.md');
const HOME_ROUTES_STATUS = path.join(STATE, 'desktop_wrapper_home_routes_status.json');
const CLEARANCE_VERIFIER = path.join(APP_ROOT, 'src', 'resource-action-clearance-verifier.js');
const CLEARANCE_TICKET = path.join(APP_ROOT, 'src', 'resource-action-clearance-ticket.js');

const SAFE_PREVIEW_ACTIONS = new Set(['preview-pause-all', 'preview-resume-all', 'preview-control']);
const BLOCKED_EXECUTE_ACTIONS = new Set([
  'execute-pause-all',
  'execute-resume-all',
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

function exists(file) {
  try {
    return fs.existsSync(file);
  } catch {
    return false;
  }
}

function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function appendJsonl(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, `${JSON.stringify(doc)}\n`, 'utf8');
}

function parseJson(text) {
  const trimmed = String(text ?? '').trim();
  if (!trimmed) return null;
  try { return JSON.parse(trimmed); } catch {}
  const start = trimmed.lastIndexOf('\n{');
  if (start >= 0) {
    try { return JSON.parse(trimmed.slice(start + 1)); } catch {}
  }
  return null;
}

function runClearance(actionClass) {
  const started = Date.now();
  const result = childProcess.spawnSync(process.execPath, [CLEARANCE_VERIFIER, '--class', actionClass], {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 10000,
  });
  return {
    rc: result.status,
    durationMs: Date.now() - started,
    parsed: parseJson(result.stdout),
    stdoutTail: (result.stdout ?? '').slice(-1000),
    stderrTail: (result.stderr ?? '').slice(-1000),
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
  };
}

function refreshClearanceTicket() {
  const started = Date.now();
  const result = childProcess.spawnSync(process.execPath, [CLEARANCE_TICKET], {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30000,
  });
  return {
    rc: result.status,
    durationMs: Date.now() - started,
    parsed: parseJson(result.stdout),
    stderrTail: (result.stderr ?? '').slice(-500),
  };
}

function servePreflight(port = 18790) {
  const ticketRefresh = refreshClearanceTicket();
  const clearance = runClearance('persistent-new-process');
  const allowed = clearance.parsed?.allowedNow === true;
  return {
    timestamp: new Date().toISOString(),
    status: clearance.rc === 0 && clearance.parsed?.status === 'ready' ? 'ready' : 'blocked',
    mode: 'serve-preflight-resource-clearance',
    port,
    host: '127.0.0.1',
    allowedByTicket: allowed,
    wouldStartServer: allowed,
    persistentProcessStarted: false,
    ticketRefresh,
    clearance,
    safety: {
      dryRunOnly: true,
      externalNetworkWrites: false,
      persistentInstall: false,
      persistentProcessStarted: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
}

function controlEndpointSchema() {
  return {
    timestamp: new Date().toISOString(),
    status: 'ready',
    mode: 'local-preview-endpoint-only',
    hostBinding: '127.0.0.1 only when preview server is manually started',
    routes: {
      'GET /control-endpoint-schema.json': 'This schema.',
      'POST /api/control/preview': 'Preview pause/resume/control decisions without mutating app_control_state.json.',
      'GET /controls.json': 'Latest wrapper control preview status file.',
      'GET /home-summary.json': 'Compact companion home summary JSON for tray/dashboard landing UI.',
      'GET /home.md': 'Compact companion home markdown summary.',
    },
    acceptedPreviewActions: Array.from(SAFE_PREVIEW_ACTIONS),
    blockedExecuteActions: Array.from(BLOCKED_EXECUTE_ACTIONS),
    requestShapes: {
      previewPauseAll: { action: 'preview-pause-all' },
      previewResumeAll: { action: 'preview-resume-all' },
      previewControl: { action: 'preview-control', controlId: 'microphone-always-on' },
    },
    limits: {
      maxBodyBytes: 8192,
      jsonOnly: true,
      noStateMutation: true,
      noExternalNetworkWrites: true,
      noSensitiveActionExecution: true,
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

function statusDoc() {
  const dashboardExists = exists(DASHBOARD);
  const appStatusExists = exists(STATUS);
  const appStatus = readJson(STATUS, { status: 'missing' });
  const manifest = readJson(MANIFEST, { status: 'missing' });
  const controlPreview = readJson(CONTROL_PREVIEW, { status: 'missing' });
  const endpointStatus = readJson(CONTROL_ENDPOINT_STATUS, { status: 'missing' });
  return {
    timestamp: new Date().toISOString(),
    status: dashboardExists && appStatusExists && appStatus.status === 'ok' ? 'ready' : 'warn',
    mode: 'dependency-free-node-preview',
    workspace: WORKSPACE,
    appRoot: APP_ROOT,
    dashboard: { path: DASHBOARD, exists: dashboardExists },
    appShellStatus: {
      path: STATUS,
      exists: appStatusExists,
      status: appStatus.status,
      cardCount: Array.isArray(appStatus.cards) ? appStatus.cards.length : 0,
      timestamp: appStatus.timestamp ?? null,
    },
    manifest: {
      path: MANIFEST,
      status: manifest.status,
      currentMode: manifest.currentMode,
      permissions: manifest.permissions ?? {},
    },
    controlPreview: {
      path: CONTROL_PREVIEW,
      status: controlPreview.status,
      mode: controlPreview.mode,
      event: controlPreview.event,
      mutatesAppControlState: controlPreview.mutatesAppControlState ?? false,
    },
    controlEndpoint: {
      path: CONTROL_ENDPOINT_STATUS,
      status: endpointStatus.status,
      mode: endpointStatus.mode,
      lastAction: endpointStatus.action,
      mutatesAppControlState: endpointStatus.mutatesAppControlState ?? false,
    },
    routes: {
      '/': 'dashboard html',
      '/status.json': 'app shell status json',
      '/wrapper-status.json': 'wrapper readiness json',
      '/controls.json': 'wrapper control preview json',
      '/home-summary.json': 'compact companion home summary json',
      '/home.md': 'compact companion home markdown',
      '/control-endpoint-schema.json': 'control endpoint schema json',
      'POST /api/control/preview': 'preview-only control endpoint; no state mutation',
    },
    safety: {
      externalNetworkWrites: false,
      persistentInstall: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
}

function send(res, code, contentType, body) {
  res.writeHead(code, {
    'Content-Type': contentType,
    'Cache-Control': 'no-store',
    'X-Local Evolution Agent-Mode': 'local-read-only-preview',
  });
  res.end(body);
}

function readBody(req, limit = 8192) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      body += chunk;
      if (body.length > limit) reject(new Error('body-too-large'));
    });
    req.on('end', () => resolve(body));
    req.on('error', reject);
  });
}

function findControl(controlId) {
  const schema = readJson(APP_CONTROL_SCHEMA, { controls: [] });
  const controls = Array.isArray(schema.controls) ? schema.controls : [];
  return controls.find((control) => control && control.id === controlId) ?? null;
}

function previewControlRequest(input) {
  const action = String(input?.action ?? '');
  const base = {
    timestamp: new Date().toISOString(),
    mode: 'local-preview-endpoint-only',
    action,
    mutatesAppControlState: false,
    executesSensitiveAction: false,
    externalNetworkWrites: false,
    persistentInstall: false,
    microphone: false,
    camera: false,
    realPhysicalActuation: false,
  };
  if (BLOCKED_EXECUTE_ACTIONS.has(action)) {
    return { ...base, status: 'blocked', allowed: false, reason: 'execute-or-sensitive-action-not-allowed-on-preview-endpoint' };
  }
  if (!SAFE_PREVIEW_ACTIONS.has(action)) {
    return { ...base, status: 'blocked', allowed: false, reason: 'unknown-or-unsupported-preview-action' };
  }
  if (action === 'preview-pause-all') {
    return { ...base, status: 'previewed', allowed: true, previewPauseAll: true };
  }
  if (action === 'preview-resume-all') {
    return { ...base, status: 'previewed', allowed: true, previewPauseAll: false };
  }
  const controlId = String(input?.controlId ?? '');
  const control = findControl(controlId);
  if (!control) {
    return { ...base, status: 'blocked', allowed: false, controlId, reason: 'unknown-control-id' };
  }
  const requiresGate = Boolean(control.dryRunOnly || control.requiresConfirmation);
  return {
    ...base,
    status: requiresGate ? 'requires-gate' : 'previewed',
    allowed: !requiresGate,
    controlId,
    label: control.label,
    currentMode: control.currentMode,
    dryRunOnly: Boolean(control.dryRunOnly),
    requiresConfirmation: Boolean(control.requiresConfirmation),
    reason: requiresGate ? (control.reason ?? 'control requires confirmation or dry-run gate') : 'control can be represented as non-sensitive app-shell affordance',
  };
}

function recordEndpointResult(doc) {
  writeJson(CONTROL_ENDPOINT_STATUS, doc);
  appendJsonl(CONTROL_ENDPOINT_AUDIT, doc);
}

function homeRoutesSelfTest() {
  const homeSummary = readJson(HOME_SUMMARY, { status: 'missing' });
  const doc = {
    timestamp: new Date().toISOString(),
    status: exists(HOME_SUMMARY) && exists(HOME_DOC) && homeSummary.status === 'ok' ? 'passed' : 'failed',
    mode: 'home-routes-self-test',
    routes: {
      '/home-summary.json': { path: HOME_SUMMARY, exists: exists(HOME_SUMMARY), status: homeSummary.status ?? 'missing' },
      '/home.md': { path: HOME_DOC, exists: exists(HOME_DOC) },
    },
    cardCount: homeSummary.cardCount ?? null,
    resourcePressure: homeSummary.resourcePressure ?? 'unknown',
    safety: {
      mutatesRuntimeControlState: false,
      externalNetworkWrites: false,
      persistentInstall: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(HOME_ROUTES_STATUS, doc);
  return doc;
}

function serve(port = 18790) {
  const host = '127.0.0.1';
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', `http://${host}:${port}`);
    if (url.pathname === '/wrapper-status.json') {
      send(res, 200, 'application/json; charset=utf-8', JSON.stringify(statusDoc(), null, 2));
      return;
    }
    if (url.pathname === '/control-endpoint-schema.json') {
      const doc = controlEndpointSchema();
      recordEndpointResult({ ...doc, event: 'schema-served' });
      send(res, 200, 'application/json; charset=utf-8', JSON.stringify(doc, null, 2));
      return;
    }
    if (url.pathname === '/api/control/preview') {
      if (req.method !== 'POST') {
        send(res, 405, 'application/json; charset=utf-8', JSON.stringify({ status: 'blocked', reason: 'method-not-allowed', allowed: false }, null, 2));
        return;
      }
      try {
        const raw = await readBody(req);
        const input = raw ? JSON.parse(raw) : {};
        const result = previewControlRequest(input);
        recordEndpointResult(result);
        send(res, result.allowed || result.status === 'requires-gate' ? 200 : 400, 'application/json; charset=utf-8', JSON.stringify(result, null, 2));
      } catch (error) {
        const result = { timestamp: new Date().toISOString(), status: 'blocked', allowed: false, reason: `${error.name}: ${error.message}`, mutatesAppControlState: false, executesSensitiveAction: false };
        recordEndpointResult(result);
        send(res, 400, 'application/json; charset=utf-8', JSON.stringify(result, null, 2));
      }
      return;
    }
    if (url.pathname === '/controls.json') {
      if (!exists(CONTROL_PREVIEW)) {
        send(res, 404, 'application/json; charset=utf-8', JSON.stringify({ status: 'missing', path: CONTROL_PREVIEW }, null, 2));
        return;
      }
      send(res, 200, 'application/json; charset=utf-8', fs.readFileSync(CONTROL_PREVIEW, 'utf8'));
      return;
    }
    if (url.pathname === '/home-summary.json') {
      if (!exists(HOME_SUMMARY)) {
        send(res, 404, 'application/json; charset=utf-8', JSON.stringify({ status: 'missing', path: HOME_SUMMARY }, null, 2));
        return;
      }
      send(res, 200, 'application/json; charset=utf-8', fs.readFileSync(HOME_SUMMARY, 'utf8'));
      return;
    }
    if (url.pathname === '/home.md') {
      if (!exists(HOME_DOC)) {
        send(res, 404, 'text/plain; charset=utf-8', `Home summary missing: ${HOME_DOC}`);
        return;
      }
      send(res, 200, 'text/markdown; charset=utf-8', fs.readFileSync(HOME_DOC, 'utf8'));
      return;
    }
    if (url.pathname === '/status.json') {
      if (!exists(STATUS)) {
        send(res, 404, 'application/json; charset=utf-8', JSON.stringify({ status: 'missing', path: STATUS }, null, 2));
        return;
      }
      send(res, 200, 'application/json; charset=utf-8', fs.readFileSync(STATUS, 'utf8'));
      return;
    }
    if (url.pathname === '/' || url.pathname === '/index.html') {
      if (!exists(DASHBOARD)) {
        send(res, 404, 'text/plain; charset=utf-8', `Dashboard missing: ${DASHBOARD}`);
        return;
      }
      send(res, 200, 'text/html; charset=utf-8', fs.readFileSync(DASHBOARD, 'utf8'));
      return;
    }
    send(res, 404, 'text/plain; charset=utf-8', 'not found');
  });
  server.listen(port, host, () => {
    console.log(JSON.stringify({ ok: true, url: `http://${host}:${port}/`, wrapperStatus: `http://${host}:${port}/wrapper-status.json` }, null, 2));
  });
}

function argValue(flag, fallback) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
}

if (process.argv.includes('--status')) {
  console.log(JSON.stringify(statusDoc(), null, 2));
} else if (process.argv.includes('--endpoint-status')) {
  const doc = controlEndpointSchema();
  recordEndpointResult({ ...doc, event: 'endpoint-status-generated' });
  console.log(JSON.stringify(doc, null, 2));
} else if (process.argv.includes('--home-routes-self-test')) {
  console.log(JSON.stringify(homeRoutesSelfTest(), null, 2));
} else if (process.argv.includes('--endpoint-self-test')) {
  const schema = controlEndpointSchema();
  const mic = previewControlRequest({ action: 'preview-control', controlId: 'microphone-always-on' });
  const blocked = previewControlRequest({ action: 'execute-pause-all' });
  const result = {
    timestamp: new Date().toISOString(),
    status: schema.status === 'ready' && ['requires-gate', 'previewed'].includes(mic.status) && mic.mutatesAppControlState === false && blocked.status === 'blocked' ? 'passed' : 'failed',
    mode: 'endpoint-self-test',
    schemaStatus: schema.status,
    micPreview: mic,
    blockedExecute: blocked,
    mutatesAppControlState: false,
    executesSensitiveAction: false,
  };
  recordEndpointResult(result);
  console.log(JSON.stringify(result, null, 2));
} else if (process.argv.includes('--serve-preflight')) {
  const port = Number(argValue('--port', '18790')) || 18790;
  console.log(JSON.stringify(servePreflight(port), null, 2));
} else if (process.argv.includes('--serve')) {
  const port = Number(argValue('--port', '18790')) || 18790;
  const preflight = servePreflight(port);
  if (!preflight.allowedByTicket) {
    console.log(JSON.stringify({ ...preflight, status: 'blocked', wouldStartServer: false }, null, 2));
    process.exit(0);
  }
  serve(port);
} else {
  console.log(JSON.stringify({ ok: true, usage: ['--status', '--endpoint-status', '--endpoint-self-test', '--home-routes-self-test', '--serve-preflight --port 18790', '--serve --port 18790'], status: statusDoc() }, null, 2));
}
