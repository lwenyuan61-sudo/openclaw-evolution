import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_audit_log_streaming_manifest_status.json');
const MANIFEST = path.join(STATE, 'audit_log_streaming_manifest.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_audit_log_streaming_manifest_audit.jsonl');
const MAX_FILES = 3;

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

function streamFingerprint(full) {
  const stat = fs.statSync(full);
  const hash = crypto.createHash('sha256');
  const fd = fs.openSync(full, 'r');
  const buffer = Buffer.alloc(1024 * 1024);
  let bytesReadTotal = 0;
  let newlineCount = 0;
  try {
    while (true) {
      const bytesRead = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (bytesRead === 0) break;
      bytesReadTotal += bytesRead;
      hash.update(buffer.subarray(0, bytesRead));
      for (let i = 0; i < bytesRead; i += 1) {
        if (buffer[i] === 0x0a) newlineCount += 1;
      }
    }
  } finally {
    fs.closeSync(fd);
  }
  return {
    bytes: stat.size,
    modified: stat.mtime.toISOString(),
    streamedBytes: bytesReadTotal,
    sha256: hash.digest('hex'),
    newlineCount,
    streamingOnly: true,
    storesRawContent: false,
  };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const tail = readJson('state/audit_log_tail_fingerprint_manifest.json', {});
  const candidates = (tail.fingerprints ?? []).slice(0, MAX_FILES);
  const entries = [];
  const blocked = [];
  for (const candidate of candidates) {
    if (!candidate?.rel) continue;
    const full = path.join(WORKSPACE, candidate.rel);
    try {
      entries.push({
        rel: candidate.rel,
        tailSha256: candidate.tailSha256 ?? null,
        ...streamFingerprint(full),
      });
    } catch (error) {
      blocked.push({ rel: candidate.rel, reason: `${error.name}: ${error.message}` });
    }
  }
  const manifest = {
    timestamp,
    mode: 'streaming-full-file-manifest-no-mutation',
    entries,
    blocked,
    restoreUse: 'Use sha256/newlineCount/bytes to verify future archive before any original log deletion is considered. This manifest does not authorize deletion.',
  };
  const doc = {
    timestamp,
    status: blocked.length ? 'blocked' : 'ready',
    mode: 'audit-log-streaming-manifest-no-mutation',
    resourceLevel: resource.resourcePressure?.level ?? 'unknown',
    sourceTailManifest: 'state\\audit_log_tail_fingerprint_manifest.json',
    manifestPath: path.relative(WORKSPACE, MANIFEST),
    entryCount: entries.length,
    totalStreamedBytes: entries.reduce((sum, item) => sum + item.streamedBytes, 0),
    entries,
    blocked,
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      streamingOnly: true,
      storesRawContent: false,
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
  appendAudit({ timestamp, status: doc.status, entryCount: entries.length, totalStreamedBytes: doc.totalStreamedBytes, blockedCount: blocked.length });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, manifest: MANIFEST, status: doc.status, entryCount: entries.length, totalStreamedBytes: doc.totalStreamedBytes, blockedCount: blocked.length, streamingOnly: true, storesRawContent: false, deletesFiles: false, truncatesFiles: false, compressesFilesNow: false, startsMicrophone: false, startsCamera: false, startsGpuWork: false, persistentProcessStarted: false }, null, 2));
}

main();
