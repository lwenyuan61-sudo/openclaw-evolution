import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_audit_log_tail_fingerprint_status.json');
const MANIFEST = path.join(STATE, 'audit_log_tail_fingerprint_manifest.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_audit_log_tail_fingerprint_audit.jsonl');
const TAIL_BYTES = 16 * 1024;

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function write(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content, 'utf8');
}

function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}

function tailFingerprint(full) {
  const stat = fs.statSync(full);
  const readBytes = Math.min(TAIL_BYTES, stat.size);
  const fd = fs.openSync(full, 'r');
  try {
    const buffer = Buffer.alloc(readBytes);
    fs.readSync(fd, buffer, 0, readBytes, stat.size - readBytes);
    const newlineCountInTail = buffer.toString('utf8').split(/\n/).length - 1;
    return {
      bytes: stat.size,
      modified: stat.mtime.toISOString(),
      tailReadBytes: readBytes,
      tailSha256: crypto.createHash('sha256').update(buffer).digest('hex'),
      newlineCountInTail,
      storesRawTail: false,
      lineCountMode: 'deferred-to-future-streaming-compaction-preflight',
    };
  } finally {
    fs.closeSync(fd);
  }
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const plan = readJson('state/desktop_wrapper_audit_log_compaction_plan_status.json', {});
  const resource = readJson('core/resource-state.json', {});
  const response = readJson('state/desktop_wrapper_resource_pressure_response_status.json', {});
  const candidates = (plan.largestCandidates ?? [])
    .filter((item) => item?.rel && /\.jsonl$/i.test(item.rel))
    .slice(0, 3);
  const fingerprints = [];
  const blocked = [];
  for (const candidate of candidates) {
    const full = path.join(WORKSPACE, candidate.rel);
    try {
      fingerprints.push({ rel: candidate.rel, ...tailFingerprint(full) });
    } catch (error) {
      blocked.push({ rel: candidate.rel, reason: `${error.name}: ${error.message}` });
    }
  }
  const manifest = {
    timestamp,
    mode: 'tail-fingerprint-no-raw-content',
    tailBytesPerFile: TAIL_BYTES,
    fingerprints,
    blocked,
    restoreUse: 'After future compression, compare original manifest bytes/modified/tailSha256 before deleting any original. This run does not authorize deletion.',
  };
  const doc = {
    timestamp,
    status: blocked.length ? 'blocked' : 'ready',
    mode: 'audit-log-tail-fingerprint-no-raw-content',
    resourceLevel: resource.resourcePressure?.level ?? 'unknown',
    profile: response.profile ?? 'unknown',
    sourcePlan: 'state\\desktop_wrapper_audit_log_compaction_plan_status.json',
    manifestPath: path.relative(WORKSPACE, MANIFEST),
    fingerprintCount: fingerprints.length,
    fingerprints,
    blocked,
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnlyExistingLogs: true,
      storesRawTailContent: false,
      tailBytesPerFile: TAIL_BYTES,
      fullFileRead: false,
      lineCountDeferred: true,
      deletesFiles: false,
      truncatesFiles: false,
      compressesFilesNow: false,
      movesFiles: false,
      externalNetworkWrites: false,
      paidApi: false,
      startsMicrophone: false,
      startsCamera: false,
      startsGpuWork: false,
      allocatesLargeMemory: false,
      dependencyInstall: false,
      persistentProcessStarted: false,
      realPhysicalActuation: false,
    },
  };
  write(MANIFEST, `${JSON.stringify(manifest, null, 2)}\n`);
  write(OUT, `${JSON.stringify(doc, null, 2)}\n`);
  appendAudit({ timestamp, status: doc.status, fingerprintCount: fingerprints.length, blockedCount: blocked.length, tailBytesPerFile: TAIL_BYTES });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, manifest: MANIFEST, status: doc.status, fingerprintCount: fingerprints.length, blockedCount: blocked.length, storesRawTailContent: false, fullFileRead: false, deletesFiles: false, truncatesFiles: false, compressesFilesNow: false, startsMicrophone: false, startsCamera: false, startsGpuWork: false, persistentProcessStarted: false }, null, 2));
}

main();
