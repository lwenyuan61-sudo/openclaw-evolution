import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT_JSON = path.join(STATE, 'desktop_wrapper_morning_progress_digest_status.json');
const OUT_MD = path.join(APP_ROOT, 'MORNING_DIGEST.md');

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function tailJsonl(rel, count = 12) {
  try {
    const lines = fs.readFileSync(path.join(WORKSPACE, rel), 'utf8').split(/\r?\n/).filter(Boolean);
    return lines.slice(-count).map((line) => {
      try { return JSON.parse(line); } catch { return { parseError: true, raw: line.slice(0, 300) }; }
    });
  } catch {
    return [];
  }
}

function asList(items, mapper) {
  if (!items || !items.length) return ['- none'];
  return items.map(mapper);
}

function main() {
  const timestamp = new Date().toISOString();
  const release = readJson('state/desktop_wrapper_release_readiness_status.json');
  const queue = readJson('state/desktop_wrapper_next_connector_queue_status.json');
  const app = readJson('state/app_shell_status.json', { cards: [] });
  const tests = readJson('state/desktop_wrapper_test_matrix_status.json');
  const gates = readJson('state/desktop_wrapper_approval_gate_register_status.json');
  const resource = readJson('core/resource-state.json');
  const docs = readJson('state/desktop_wrapper_docs_status.json');
  const recent = tailJsonl('autonomy/experiment-log.jsonl', 16)
    .filter((event) => event.type === 'verified-connector' || event.status === 'verified')
    .slice(-10)
    .map((event) => ({ id: event.id ?? null, timestamp: event.timestamp ?? null, summary: event.summary ?? null, verification: event.verification ?? null }));

  const cards = Array.isArray(app.cards) ? app.cards : [];
  const warningCards = cards.filter((card) => ['warn', 'warning', 'error', 'critical'].includes(card.level));
  const releaseOverall = release.overall || {};
  const nextDecisionOptions = release.nextDecisionOptions || [];
  const hardBlockers = release.hardBlockers || [];
  const selectedNext = queue.selected || null;
  const completed = queue.completed || [];
  const blockedImportant = queue.blockedImportant || [];

  const doc = {
    timestamp,
    status: 'ready',
    mode: 'morning-progress-digest-local-only',
    headline: `Desktop companion is ${releaseOverall.level ?? 'unknown'} (${releaseOverall.percent ?? 0}%).`,
    release: releaseOverall,
    appShell: { cardCount: cards.length, warningCount: warningCards.length, status: app.status ?? 'unknown' },
    regression: { status: tests.status ?? 'unknown', passed: tests.passedCount ?? 0, total: tests.totalCount ?? 0, failedIds: tests.failedIds ?? [] },
    docs: { status: docs.status ?? 'unknown', commandCount: docs.commandCount ?? 0 },
    resource: { pressure: resource.resourcePressure?.level ?? 'unknown', gpuFreeMiB: resource.gpus?.[0]?.memoryFreeMiB ?? null, gpuUsedMiB: resource.gpus?.[0]?.memoryUsedMiB ?? null },
    queue: { selected: selectedNext, completedCount: completed.length, completed, blockedImportant },
    approvalGates: { gateCount: gates.gateCount ?? 0, approvalGatedCount: gates.approvalGatedCount ?? 0 },
    hardBlockers,
    nextDecisionOptions,
    recentVerifiedConnectors: recent,
    safety: {
      digestOnly: true,
      externalSendPerformed: false,
      changedPermissionState: false,
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentProcessStarted: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };

  const md = [
    '# Local Evolution Agent Desktop Companion · Morning Progress Digest',
    '',
    `Generated: ${timestamp}`,
    '',
    `Headline: ${doc.headline}`,
    '',
    '## Current verified state',
    `- Release readiness: ${releaseOverall.level ?? 'unknown'} (${releaseOverall.score ?? 0}/${releaseOverall.max ?? 0}, ${releaseOverall.percent ?? 0}%)`,
    `- App shell cards: ${doc.appShell.cardCount}; warning cards: ${doc.appShell.warningCount}`,
    `- Test matrix: ${doc.regression.status} (${doc.regression.passed}/${doc.regression.total})`,
    `- Operations docs commands: ${doc.docs.commandCount}`,
    `- Resource pressure: ${doc.resource.pressure}; GPU used/free MiB: ${doc.resource.gpuUsedMiB}/${doc.resource.gpuFreeMiB}`,
    '',
    '## Completed safe connector sequence',
    ...asList(completed, (item) => `- ${item.id}: ${item.title}`),
    '',
    '## Current next queue item',
    selectedNext ? `- ${selectedNext.id}: ${selectedNext.nextStep}` : '- none selected',
    '',
    '## Hard blockers / approval boundaries',
    ...asList(hardBlockers, (item) => `- ${item}`),
    '',
    '## Next decision options',
    ...asList(nextDecisionOptions, (item) => `- ${item.id}${item.requiresApproval ? ' (requires approval)' : ''}: ${item.description}`),
    '',
    '## Recent verified connector evidence',
    ...asList(recent, (item) => `- ${item.id}: ${item.summary ?? 'verified'}`),
    '',
    '## Safety',
    '- Digest only. No external send, permission change, install, scaffold, persistent process, mic/camera access, or real physical actuation.',
    '',
  ].join('\n');

  fs.writeFileSync(OUT_JSON, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  fs.writeFileSync(OUT_MD, md, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT_JSON, digest: OUT_MD, level: releaseOverall.level ?? null, percent: releaseOverall.percent ?? null, completedCount: completed.length, hardBlockers: hardBlockers.length }, null, 2));
}

main();
