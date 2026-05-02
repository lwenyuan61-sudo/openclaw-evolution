import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_external_action_guard_status.json');
const MANIFEST = path.join(STATE, 'external_action_guard_manifest.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_external_action_guard_audit.jsonl');
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
    durationMs: Date.now() - started,
    parsed: parseLastJson(result.stdout),
    stderrTail: (result.stderr ?? '').slice(-500),
  };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const guarded = [
    {
      id: 'paid-api-call',
      actionClass: 'paid-api',
      commandPreview: ['provider-api-call'],
      expectedAllowed: false,
      reason: 'paid APIs remain default denied even under normal-local-first',
    },
    {
      id: 'external-network-write',
      actionClass: 'external-network-write',
      commandPreview: ['POST', 'https://example.invalid/webhook'],
      expectedAllowed: false,
      reason: 'external writes require explicit non-resource authorization and are not a ticketed class',
    },
    {
      id: 'public-message-send',
      actionClass: 'external-network-write',
      commandPreview: ['message.send', 'public-or-cross-channel-target'],
      expectedAllowed: false,
      reason: 'Lee-facing/internal reports use current chat only; public/cross-channel sends require explicit user intent',
    },
    {
      id: 'read-only-local-summary',
      actionClass: 'read-only-probes',
      commandPreview: ['node', 'apps/local-desktop-companion/src/resource-policy-state-summary.js'],
      expectedAllowed: true,
      reason: 'local read-only work is allowed by a fresh resource ticket',
    },
  ];
  const decisions = guarded.map((item) => {
    const verification = runVerifier(item.actionClass);
    const allowedByTicket = verification.parsed?.allowedNow === true;
    const mismatch = allowedByTicket !== item.expectedAllowed;
    return {
      ...item,
      allowedByTicket,
      decision: allowedByTicket ? 'allowed-by-ticket' : 'blocked-by-external-action-guard',
      mismatch,
      wouldExecute: false,
      verifierStatus: verification.parsed?.status ?? 'unknown',
      verifierReasons: verification.parsed?.requested?.reasons ?? [],
      startsMicrophone: false,
      startsCamera: false,
      startsGpuWork: false,
      dependencyInstall: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      paidApi: false,
    };
  });
  const mismatches = decisions.filter((item) => item.mismatch).map((item) => item.id);
  const blockedExternalCount = decisions.filter((item) => !item.allowedByTicket && ['paid-api', 'external-network-write'].includes(item.actionClass)).length;
  const doc = {
    timestamp,
    status: mismatches.length === 0 ? 'ready' : 'needs-attention',
    mode: 'external-action-guard-dry-run',
    manifestPath: path.relative(WORKSPACE, MANIFEST),
    decisionCount: decisions.length,
    allowedCount: decisions.filter((item) => item.allowedByTicket).length,
    blockedExternalCount,
    mismatches,
    decisions,
    contract: {
      dryRunOnly: true,
      doesNotSendMessages: true,
      doesNotCallPaidApis: true,
      externalWritesRequireExplicitAuthorizationOutsideResourceTicket: true,
      readOnlyLocalWorkCanPassWithFreshTicket: true,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      dryRunOnly: true,
      startsMicrophone: false,
      startsCamera: false,
      startsGpuWork: false,
      dependencyInstall: false,
      externalNetworkWrites: false,
      paidApi: false,
      persistentProcessStarted: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(MANIFEST, { timestamp, guarded, contract: doc.contract });
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, decisionCount: decisions.length, allowedCount: doc.allowedCount, blockedExternalCount, mismatches });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, decisionCount: doc.decisionCount, allowedCount: doc.allowedCount, blockedExternalCount, mismatches, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, externalNetworkWrites: false, paidApi: false, persistentProcessStarted: false }, null, 2));
}

main();
