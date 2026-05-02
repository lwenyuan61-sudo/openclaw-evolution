import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT_JSON = path.join(STATE, 'desktop_wrapper_home_summary.json');
const OUT_MD = path.join(APP_ROOT, 'HOME.md');

function readJson(rel, fallback = {}) {
  const abs = path.join(WORKSPACE, rel);
  try {
    return JSON.parse(fs.readFileSync(abs, 'utf8'));
  } catch {
    return fallback;
  }
}

function card(app, id) {
  return (app.cards || []).find((item) => item.id === id) || {};
}

function levelRank(level) {
  if (level === 'error' || level === 'critical') return 3;
  if (level === 'warn' || level === 'warning') return 2;
  if (level === 'unknown' || !level) return 1;
  return 0;
}

function main() {
  const timestamp = new Date().toISOString();
  const app = readJson('state/app_shell_status.json', { cards: [] });
  const resource = readJson('core/resource-state.json');
  const control = readJson('state/app_control_state.json');
  const audit = readJson('state/desktop_wrapper_audit_view_status.json');
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json');
  const docs = readJson('state/desktop_wrapper_docs_status.json');
  const packaging = readJson('state/desktop_wrapper_packaging_preflight_status.json');
  const service = readJson('state/service_health_status.json');

  const cards = app.cards || [];
  const highest = [...cards].sort((a, b) => levelRank(b.level) - levelRank(a.level))[0] || {};
  const warnings = cards.filter((item) => levelRank(item.level) >= 2).map((item) => ({ id: item.id, title: item.title, level: item.level, summary: item.summary }));
  const ready = [
    card(app, 'resident'),
    card(app, 'resource'),
    card(app, 'service-health'),
    card(app, 'test-matrix'),
    card(app, 'audit-view'),
  ].filter((item) => item.id).map((item) => ({ id: item.id, level: item.level, summary: item.summary }));

  const summary = {
    timestamp,
    status: 'ok',
    mode: 'companion-home-summary',
    headline: 'Local Evolution Agent Desktop Companion is running as a local-first autonomous desktop-agent prototype.',
    cardCount: cards.length,
    highestAttention: highest.id ? { id: highest.id, title: highest.title, level: highest.level, summary: highest.summary } : null,
    warnings,
    ready,
    resourcePressure: resource.resourcePressure?.level ?? 'unknown',
    gpuSummary: (resource.gpus || []).map((gpu) => ({ name: gpu.name, usedMiB: gpu.memoryUsedMiB, totalMiB: gpu.memoryTotalMiB, pressure: gpu.memoryPressure })),
    pauseAll: Boolean(control.pauseAll),
    audit: { events: audit.eventCount ?? 0, blocked: audit.blockedCount ?? 0, sensitive: audit.sensitiveCount ?? 0 },
    testMatrix: { status: matrix.status ?? 'unknown', passed: matrix.passedCount ?? 0, total: matrix.totalCount ?? 0 },
    operationsDocs: { status: docs.status ?? 'unknown', commandCount: docs.commandCount ?? 0 },
    packaging: { recommendation: packaging.recommendation ?? packaging.packageRecommendation ?? 'unknown', rustAvailable: packaging.rustAvailable ?? false, npmAvailable: packaging.npmAvailable ?? true },
    serviceHealth: { status: service.status ?? 'unknown', gatewayRunning: service.gateway?.running ?? service.gatewayRunning ?? null, watchdogTaskPresent: service.watchdog?.taskPresent ?? service.watchdogTaskPresent ?? null },
    nextUsefulActions: [
      'Keep current local-only wake loop and resource guard active.',
      'Use HOME.md as the future tray/dashboard landing summary.',
      'Only scaffold Electron/Tauri after explicit Lee approval for dependency install/scaffold.',
    ],
    safety: {
      externalNetworkWrites: false,
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentProcessStarted: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };

  const md = [
    '# Local Evolution Agent Desktop Companion · Home',
    '',
    `Generated: ${timestamp}`,
    '',
    `Status: ${summary.status}`,
    `Cards: ${summary.cardCount}`,
    `Resource pressure: ${summary.resourcePressure}`,
    `Pause all: ${summary.pauseAll}`,
    '',
    '## Highest attention',
    summary.highestAttention ? `- ${summary.highestAttention.title} (${summary.highestAttention.level}): ${summary.highestAttention.summary}` : '- none',
    '',
    '## Ready signals',
    ...summary.ready.map((item) => `- ${item.id} (${item.level}): ${item.summary}`),
    '',
    '## Warnings / gated items',
    ...(summary.warnings.length ? summary.warnings.map((item) => `- ${item.title} (${item.level}): ${item.summary}`) : ['- none']),
    '',
    '## Audit / testing',
    `- Audit events: ${summary.audit.events}; blocked=${summary.audit.blocked}; sensitive=${summary.audit.sensitive}`,
    `- Test matrix: ${summary.testMatrix.status} (${summary.testMatrix.passed}/${summary.testMatrix.total})`,
    `- Operations docs: ${summary.operationsDocs.status}; commands=${summary.operationsDocs.commandCount}`,
    '',
    '## Packaging',
    `- Recommendation: ${summary.packaging.recommendation}`,
    `- Rust available: ${summary.packaging.rustAvailable}`,
    '',
    '## Safety',
    '- No dependency install, scaffold, persistent process, external write, microphone, camera, or real physical actuation was performed by this summary.',
    '',
  ].join('\n');

  fs.writeFileSync(OUT_JSON, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
  fs.writeFileSync(OUT_MD, md, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT_JSON, home: OUT_MD, cardCount: summary.cardCount, warnings: summary.warnings.length, resourcePressure: summary.resourcePressure }, null, 2));
}

main();
