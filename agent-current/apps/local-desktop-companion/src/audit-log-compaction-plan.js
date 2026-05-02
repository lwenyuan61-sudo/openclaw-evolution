import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_audit_log_compaction_plan_status.json');
const PLAN_MD = path.join(STATE, 'audit_log_compaction_plan.md');
const AUDIT = path.join(STATE, 'desktop_wrapper_audit_log_compaction_plan_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function walk(dir, predicate, out = []) {
  let entries = [];
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!['node_modules', '.git'].includes(entry.name)) walk(full, predicate, out);
    } else if (predicate(full)) {
      try {
        const stat = fs.statSync(full);
        out.push({ full, rel: path.relative(WORKSPACE, full), bytes: stat.size, modified: stat.mtime.toISOString() });
      } catch {}
    }
  }
  return out;
}

function write(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content, 'utf8');
}

function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}

function mib(bytes) { return Number((bytes / 1024 / 1024).toFixed(3)); }

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const response = readJson('state/desktop_wrapper_resource_pressure_response_status.json', {});
  const queue = readJson('state/desktop_wrapper_resource_safe_connector_queue_status.json', {});
  const files = walk(STATE, (file) => /(_audit|audit_|_log|log\.|\.jsonl$)/i.test(path.basename(file))).sort((a, b) => b.bytes - a.bytes);
  const totalBytes = files.reduce((sum, item) => sum + item.bytes, 0);
  const largest = files.slice(0, 12);
  const recommendations = [
    {
      id: 'tail-snapshot-before-compaction',
      action: 'Before any future compaction, write a tail snapshot and line count for each JSONL/audit log.',
      reversible: true,
      executesNow: false,
    },
    {
      id: 'compress-not-delete',
      action: 'Prefer gzip/zip archive to deletion; keep original until checksum and restore path are verified.',
      reversible: true,
      executesNow: false,
    },
    {
      id: 'size-thresholds',
      action: 'Only compact logs above 20 MiB or when workspace disk enters warning; current run is proposal-only.',
      reversible: true,
      executesNow: false,
    },
    {
      id: 'manifest-required',
      action: 'Write manifest with original path, bytes, sha256, archive path, line count, createdAt, and restore command.',
      reversible: true,
      executesNow: false,
    },
  ];
  const markdown = `# Audit Log Compaction Plan\n\nGenerated: ${timestamp}\n\n## Resource context\n\n- Resource level: ${resource.resourcePressure?.level ?? 'unknown'}\n- Profile: ${response.profile ?? 'unknown'}\n- RAM pressure: ${resource.memory?.pressure ?? 'n/a'}\n- Workspace disk free: ${(resource.disks ?? []).find((item) => item?.isWorkspaceDrive)?.freeMiB ?? 'n/a'} MiB\n- Safe queue selected: ${queue.selected?.id ?? 'none'}\n\n## Current audit/log footprint\n\n- Candidate files: ${files.length}\n- Total candidate size: ${mib(totalBytes)} MiB\n\nLargest candidates:\n${largest.map((item) => `- ${item.rel} · ${mib(item.bytes)} MiB`).join('\n') || '- none'}\n\n## Future reversible compaction rules\n\n${recommendations.map((item) => `- ${item.id}: ${item.action}`).join('\n')}\n\n## Safety\n\nThis run is proposal-only. It does not delete, truncate, compress, move, upload, or mutate existing logs.\n`;
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'audit-log-compaction-plan-proposal-only',
    resourceLevel: resource.resourcePressure?.level ?? 'unknown',
    profile: response.profile ?? 'unknown',
    candidateCount: files.length,
    totalCandidateBytes: totalBytes,
    totalCandidateMiB: mib(totalBytes),
    largestCandidates: largest,
    recommendations,
    markdownPath: path.relative(WORKSPACE, PLAN_MD),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      proposalOnly: true,
      readOnlyExistingLogs: true,
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
  write(PLAN_MD, markdown);
  write(OUT, `${JSON.stringify(doc, null, 2)}\n`);
  appendAudit({ timestamp, status: doc.status, candidateCount: files.length, totalCandidateBytes: totalBytes, profile: doc.profile });
  console.log(JSON.stringify({ ok: true, out: OUT, markdown: PLAN_MD, status: doc.status, candidateCount: files.length, totalCandidateMiB: doc.totalCandidateMiB, proposalOnly: true, deletesFiles: false, truncatesFiles: false, startsMicrophone: false, startsCamera: false, startsGpuWork: false, persistentProcessStarted: false }, null, 2));
}

main();
