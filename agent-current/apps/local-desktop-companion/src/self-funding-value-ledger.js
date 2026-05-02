import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_self_funding_value_ledger_status.json');
const LEDGER = path.join(STATE, 'self_funding_value_ledger.json');
const LEDGER_MD = path.join(STATE, 'self_funding_value_ledger.md');
const AUDIT = path.join(STATE, 'desktop_wrapper_self_funding_value_ledger_audit.jsonl');
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
function tailLines(file, maxBytes = 384 * 1024) {
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
function parseEvents(limit = 120) {
  return tailLines(EXPERIMENT_LOG).slice(-limit).map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
}
function valueClass(event) {
  const text = `${event.id ?? ''} ${event.summary ?? ''}`.toLowerCase();
  if (text.includes('quota') || text.includes('self-funding') || text.includes('funding')) return 'quota-and-business-infrastructure';
  if (text.includes('resource') || text.includes('guard') || text.includes('ticket')) return 'risk-reduction';
  if (text.includes('organ') || text.includes('voice') || text.includes('camera')) return 'embodied-readiness';
  if (text.includes('app shell') || text.includes('electron') || text.includes('desktop')) return 'productization';
  return 'infrastructure';
}
function estimateMinutes(event) {
  const cls = valueClass(event);
  if (cls === 'quota-and-business-infrastructure') return 20;
  if (cls === 'risk-reduction') return 25;
  if (cls === 'embodied-readiness') return 30;
  if (cls === 'productization') return 30;
  return 15;
}
function markdown(doc) {
  const rows = doc.entries.map((entry) => `- ${entry.timestamp ?? 'n/a'} · ${entry.valueClass} · ${entry.estimatedMinutesSaved}m · ${entry.summary ?? entry.id}`).join('\n');
  return `# Self-Funding Value Ledger\n\nGenerated: ${doc.timestamp}\n\nPurpose: track concrete value created so quota upgrades can be justified or funded.\n\n## Quota\n\n- Weekly left: ${doc.quota.weeklyLeftPercent ?? 'unknown'}%\n- Reserve floor: ${doc.quota.weeklyReserveFloorPercent ?? 10}%\n- Speed band: ${doc.quota.selectedSpeedBand ?? 'unknown'}\n\n## Summary\n\n- Entries: ${doc.entryCount}\n- Estimated minutes saved/created: ${doc.totalEstimatedMinutes}\n- Estimated hours: ${doc.totalEstimatedHours}\n- External sends/posts/payments: none\n\n## Recent value entries\n\n${rows || '- No entries yet.'}\n`;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const quota = readJson('state/codex_usage_governor_status.json', {});
  const strategy = readJson('state/self_funding_quota_strategy.json', {});
  const events = parseEvents(120);
  const verified = events
    .filter((event) => ['verified', 'verified-warning'].includes(event.status) || event.type === 'verified-connector' || event.type === 'policy-connector')
    .slice(-12);
  const entries = verified.map((event) => {
    const cls = valueClass(event);
    return {
      id: event.id,
      timestamp: event.timestamp,
      type: event.type,
      status: event.status,
      valueClass: cls,
      estimatedMinutesSaved: estimateMinutes(event),
      summary: event.summary,
    };
  });
  const totalEstimatedMinutes = entries.reduce((sum, entry) => sum + entry.estimatedMinutesSaved, 0);
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'self-funding-value-ledger-read-only',
    goal: strategy.goal ?? 'fund higher quota through demonstrated value',
    quota: {
      weeklyLeftPercent: quota.weeklyLeftPercent ?? null,
      weeklyReserveFloorPercent: quota.weeklyReserveFloorPercent ?? 10,
      selectedSpeedBand: quota.selectedSpeedBand ?? 'unknown',
      weeklyResetIn: quota.weeklyResetIn ?? null,
    },
    entryCount: entries.length,
    totalEstimatedMinutes,
    totalEstimatedHours: Number((totalEstimatedMinutes / 60).toFixed(2)),
    entries,
    nextLocalOfferAsset: 'automation-service-pack-one-page-offer',
    externalActions: {
      sendsMessages: false,
      publicPosting: false,
      financialCommitment: false,
      paidApi: false,
    },
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
  writeJson(LEDGER, doc);
  fs.writeFileSync(LEDGER_MD, markdown(doc), 'utf8');
  writeJson(OUT, { ...doc, ledgerPath: path.relative(WORKSPACE, LEDGER), markdownPath: path.relative(WORKSPACE, LEDGER_MD), auditPath: path.relative(WORKSPACE, AUDIT) });
  appendAudit({ timestamp, status: doc.status, entryCount: doc.entryCount, totalEstimatedMinutes, quota: doc.quota });
  console.log(JSON.stringify({
    ok: true,
    out: OUT,
    status: doc.status,
    entryCount: doc.entryCount,
    totalEstimatedMinutes,
    totalEstimatedHours: doc.totalEstimatedHours,
    weeklyLeftPercent: doc.quota.weeklyLeftPercent,
    reserveFloor: doc.quota.weeklyReserveFloorPercent,
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
