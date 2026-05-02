import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_quiet_hours_progress_batcher_status.json');
const BATCH = path.join(STATE, 'quiet_hours_progress_batch.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_quiet_hours_progress_batcher_audit.jsonl');
const EXPERIMENT_LOG = path.join(WORKSPACE, 'autonomy', 'experiment-log.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}
function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}
function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}
function readTailLines(file, maxBytes = 256 * 1024) {
  try {
    const stat = fs.statSync(file);
    const start = Math.max(0, stat.size - maxBytes);
    const fd = fs.openSync(file, 'r');
    const buf = Buffer.alloc(stat.size - start);
    fs.readSync(fd, buf, 0, buf.length, start);
    fs.closeSync(fd);
    return buf.toString('utf8').split(/\r?\n/).filter(Boolean);
  } catch {
    return [];
  }
}
function parseTailEvents(limit = 40) {
  return readTailLines(EXPERIMENT_LOG).slice(-limit).map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const mode = readJson('core/session-mode.json', {});
  const self = readJson('core/self-state.json', {});
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json', {});
  const consistency = readJson('state/consistency_report.json', {});
  const app = readJson('state/app_shell_status.json', { cards: [] });
  const quietHours = mode.mode === 'quiet-hours';
  const events = parseTailEvents(60);
  const recentVerified = events
    .filter((event) => ['verified', 'verified-warning'].includes(event.status) || event.type === 'verified-connector')
    .slice(-8)
    .map((event) => ({ id: event.id, timestamp: event.timestamp, summary: event.summary, status: event.status, type: event.type }));
  const blockers = [];
  if (matrix.status && matrix.status !== 'passed') blockers.push({ source: 'test-matrix', status: matrix.status, failedIds: matrix.failedIds ?? [] });
  if (consistency.status && consistency.status !== 'ok') blockers.push({ source: 'consistency', status: consistency.status, errors: consistency.errors ?? [], warnings: consistency.warnings ?? [] });
  const warningCards = (app.cards ?? []).filter((card) => ['warn', 'warning', 'critical', 'needs-attention'].includes(card.level));
  const shouldReportNow = blockers.length > 0;
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'quiet-hours-progress-batcher-read-only',
    quietHours,
    shouldReportNow,
    reportReason: shouldReportNow ? 'blocker-or-regression' : 'batch-until-non-quiet-or-meaningful-blocker',
    batchCount: recentVerified.length,
    latestMeaningfulProgressAt: self.lastMeaningfulProgressAt ?? null,
    currentFocus: self.currentFocus ?? self.focus ?? null,
    recentVerified,
    blockers,
    warningCards: warningCards.map((card) => ({ id: card.id, level: card.level, summary: card.summary })).slice(0, 8),
    batchPath: path.relative(WORKSPACE, BATCH),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnly: true,
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
  writeJson(OUT, doc);
  writeJson(BATCH, {
    timestamp,
    quietHours,
    shouldReportNow,
    reportReason: doc.reportReason,
    recentVerified,
    blockers,
    holdPolicy: quietHours ? 'hold-routine-progress; surface-blockers-only' : 'normal-reporting-rules',
  });
  appendAudit({ timestamp, quietHours, shouldReportNow, batchCount: recentVerified.length, blockers: blockers.length });
  console.log(JSON.stringify({
    ok: true,
    out: OUT,
    status: doc.status,
    quietHours,
    shouldReportNow,
    reportReason: doc.reportReason,
    batchCount: doc.batchCount,
    blockers: blockers.length,
    startsMicrophone: false,
    startsCamera: false,
    startsGpuWork: false,
    dependencyInstall: false,
    externalNetworkWrites: false,
    paidApi: false,
    persistentProcessStarted: false,
  }, null, 2));
}

main();
