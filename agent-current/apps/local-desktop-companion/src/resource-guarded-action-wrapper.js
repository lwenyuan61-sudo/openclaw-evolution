import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_guarded_action_wrapper_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_guarded_action_wrapper_audit.jsonl');
const NODE = process.execPath;
const VERIFIER = 'apps/local-desktop-companion/src/resource-action-clearance-verifier.js';

function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}

function argValue(name, fallback) {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1];
  return fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function commandPreview() {
  const idx = process.argv.indexOf('--');
  if (idx < 0) return [];
  return process.argv.slice(idx + 1);
}

function parseLastJson(text) {
  const trimmed = String(text ?? '').trim();
  if (!trimmed) return null;
  try { return JSON.parse(trimmed); } catch {}
  const start = trimmed.lastIndexOf('\n{');
  if (start >= 0) {
    try { return JSON.parse(trimmed.slice(start + 1)); } catch {}
  }
  return null;
}

function runVerifier(actionClass) {
  const started = Date.now();
  const result = childProcess.spawnSync(NODE, [VERIFIER, '--class', actionClass], {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30000,
  });
  return {
    status: result.status,
    signal: result.signal,
    durationMs: Date.now() - started,
    parsed: parseLastJson(result.stdout),
    stderrTail: (result.stderr ?? '').slice(-500),
  };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const actionClass = argValue('--class', 'read-only-probes');
  const intent = argValue('--intent', 'unspecified-local-action');
  const executeRequested = hasFlag('--execute');
  const command = commandPreview();
  const verification = runVerifier(actionClass);
  const verifierOk = verification.status === 0 && verification.parsed?.status === 'ready';
  const allowedByTicket = verifierOk && verification.parsed?.allowedNow === true;
  const blockedReasons = [];
  if (!verifierOk) blockedReasons.push('verifier-not-ready');
  if (!allowedByTicket) blockedReasons.push('ticket-denied-or-not-allowed');
  if (executeRequested) blockedReasons.push('execute-mode-disabled-for-wrapper-prototype');
  if (command.length === 0) blockedReasons.push('no-command-provided');
  const wouldExecute = executeRequested && allowedByTicket && command.length > 0 && !blockedReasons.includes('execute-mode-disabled-for-wrapper-prototype');
  const selfTestReadOnly = runVerifier('read-only-probes');
  const selfTestCamera = runVerifier('camera-capture');
  const selfTestPaidApi = runVerifier('paid-api');
  const readOnlyAllowed = selfTestReadOnly.parsed?.allowedNow === true;
  const cameraDenied = selfTestCamera.parsed?.allowedNow === false;
  const paidApiDenied = selfTestPaidApi.parsed?.allowedNow === false && selfTestPaidApi.parsed?.paidApiDenied === true;
  const doc = {
    timestamp,
    status: verifierOk && readOnlyAllowed && paidApiDenied ? 'ready' : 'blocked',
    mode: 'resource-guarded-action-wrapper-dry-run',
    requested: {
      intent,
      actionClass,
      executeRequested,
      commandPreview: command,
      allowedByTicket,
      wouldExecute,
      decision: wouldExecute ? 'would-execute-if-prototype-enabled' : 'dry-run-only-or-blocked',
      blockedReasons,
    },
    verifier: verification.parsed ?? null,
    selfTest: {
      readOnlyAllowed,
      cameraDenied,
      paidApiDenied,
      readOnlyVerifierStatus: selfTestReadOnly.parsed?.status ?? null,
      cameraVerifierStatus: selfTestCamera.parsed?.status ?? null,
      paidApiVerifierStatus: selfTestPaidApi.parsed?.status ?? null,
    },
    contract: {
      futureExecutionMustPassVerifier: true,
      currentWrapperDoesNotExecuteCommands: true,
      deniedSensitiveClassesRemainDenied: true,
      commandPreviewOnly: true,
      supportedClassesComeFromTicket: true,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      dryRunOnly: true,
      readOnlyExceptStatus: true,
      startsMicrophone: false,
      startsCamera: false,
      startsGpuWork: false,
      allocatesLargeMemory: false,
      writesLargeFiles: false,
      dependencyInstall: false,
      externalNetworkWrites: false,
      paidApi: false,
      persistentProcessStarted: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, intent, actionClass, allowedByTicket, executeRequested, wouldExecute, blockedReasons });
  console.log(JSON.stringify({ ok: doc.status === 'ready' && allowedByTicket && readOnlyAllowed && paidApiDenied, out: OUT, status: doc.status, actionClass, allowedByTicket, wouldExecute, readOnlyAllowed, cameraDenied, paidApiDenied, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
