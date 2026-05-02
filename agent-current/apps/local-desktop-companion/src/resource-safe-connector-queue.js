import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_safe_connector_queue_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_safe_connector_queue_audit.jsonl');

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

function ageSeconds(iso) {
  const parsed = Date.parse(iso ?? '');
  if (!Number.isFinite(parsed)) return null;
  return Math.max(0, Math.round((Date.now() - parsed) / 1000));
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const response = readJson('state/desktop_wrapper_resource_pressure_response_status.json', {});
  const serialized = readJson('state/desktop_wrapper_resource_gate_serialized_refresh_status.json', {});
  const profileSync = readJson('state/desktop_wrapper_resource_profile_sync_status.json', {});
  const trend = readJson('state/desktop_wrapper_resource_trend_gate_status.json', {});
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json', {});
  const app = readJson('state/app_shell_status.json', { cards: [] });
  const serializedFinal = serialized.final ?? {};
  const serializedFresh = serialized.status === 'ready' && ageSeconds(serialized.timestamp) !== null && ageSeconds(serialized.timestamp) <= 5 * 60;
  const profile = serializedFinal.effectiveProfile ?? profileSync.effectiveProfile ?? response.profile ?? 'unknown';
  const resourceLevel = serializedFinal.resourceLevel ?? resource.resourcePressure?.level ?? 'unknown';
  const suppressed = new Set(response.recommendations?.suppressed ?? []);
  const allowOnlyLight = ['low-memory-safe-mode', 'normal-local-first-watch-memory', 'recovery-cooldown'].includes(profile) || resourceLevel === 'warning';
  const candidates = [
    {
      id: 'resource-policy-state-summary',
      title: 'Resource policy state summary',
      kind: 'state-summary',
      baseScore: 13,
      allowedProfiles: ['normal-local-first', 'normal-local-first-watch-memory', 'low-memory-safe-mode', 'recovery-cooldown', 'protective-stop'],
      tags: ['read-only', 'small-local-cpu', 'no-organs', 'no-model-load'],
      value: 'keeps Lee-facing autonomy decisions explainable under pressure',
    },
    {
      id: 'safe-degrade-regression-maintenance',
      title: 'Safe-degrade regression maintenance',
      kind: 'test-policy',
      baseScore: 12,
      allowedProfiles: ['normal-local-first', 'normal-local-first-watch-memory', 'low-memory-safe-mode', 'recovery-cooldown'],
      tags: ['read-only', 'small-local-cpu', 'no-organs', 'no-model-load'],
      value: 'prevents resource-warning gates from becoming false regressions',
    },
    {
      id: 'app-shell-pressure-card-polish',
      title: 'App shell pressure-card polish',
      kind: 'app-shell',
      baseScore: 10,
      allowedProfiles: ['normal-local-first', 'normal-local-first-watch-memory', 'low-memory-safe-mode', 'recovery-cooldown'],
      tags: ['small-local-cpu', 'no-organs', 'no-model-load'],
      value: 'makes pressure modes visible without starting sensors or heavy tasks',
    },
    {
      id: 'audit-log-compaction-plan',
      title: 'Audit log compaction plan',
      kind: 'proposal-only',
      baseScore: 8,
      allowedProfiles: ['normal-local-first', 'normal-local-first-watch-memory', 'low-memory-safe-mode', 'recovery-cooldown', 'protective-stop'],
      tags: ['read-only', 'proposal-only', 'no-delete', 'no-organs', 'no-model-load'],
      value: 'prepares future disk/memory hygiene without deleting anything',
    },
    {
      id: 'camera-or-voice-calibration',
      title: 'Camera or voice calibration',
      kind: 'organ-start',
      baseScore: 20,
      allowedProfiles: ['normal-local-first'],
      tags: ['starts-organ', 'microphone-recording', 'camera-capture'],
      value: 'high product value, but suppressed while RAM is warning',
    },
    {
      id: 'dependency-install-or-model-load',
      title: 'Dependency install or model load',
      kind: 'heavy',
      baseScore: 18,
      allowedProfiles: ['normal-local-first'],
      tags: ['dependency-install', 'model-loads', 'memory-heavy'],
      value: 'deferred under low-memory safe mode',
    },
  ];
  const ranked = candidates.map((candidate) => {
    const blockedReasons = [];
    if (!candidate.allowedProfiles.includes(profile)) blockedReasons.push(`profile:${profile}`);
    for (const tag of candidate.tags) {
      if (suppressed.has(tag) || (tag === 'starts-organ' && (suppressed.has('camera-capture') || suppressed.has('microphone-recording')))) blockedReasons.push(`suppressed:${tag}`);
    }
    if (allowOnlyLight && !candidate.tags.includes('small-local-cpu') && !candidate.tags.includes('read-only')) blockedReasons.push('not-lightweight');
    const score = candidate.baseScore - blockedReasons.length * 100 + (candidate.tags.includes('read-only') ? 2 : 0) + (matrix.status === 'passed' ? 1 : 0);
    return { ...candidate, score, blockedReasons, selectable: blockedReasons.length === 0 };
  }).sort((a, b) => b.score - a.score);
  const selected = ranked.find((item) => item.selectable) ?? null;
  const doc = {
    timestamp,
    status: selected ? 'ready' : 'blocked',
    mode: 'resource-safe-connector-queue-read-only',
    profile,
    resourceLevel,
    current: {
      memoryPressure: resource.memory?.pressure ?? null,
      memoryUsedMiB: resource.memory?.usedMiB ?? null,
      memoryTotalMiB: resource.memory?.totalMiB ?? null,
      trendStatus: trend.status ?? null,
      memoryDirection: trend.trends?.memory?.direction ?? null,
      appWarningCards: (app.cards ?? []).filter((item) => ['warn', 'warning', 'critical'].includes(item.level)).length,
    },
    selected: selected ? {
      id: selected.id,
      title: selected.title,
      kind: selected.kind,
      tags: selected.tags,
      value: selected.value,
    } : null,
    ranked: ranked.map(({ id, title, kind, score, tags, selectable, blockedReasons }) => ({ id, title, kind, score, tags, selectable, blockedReasons })),
    canonicalPreflight: {
      source: 'resource-gate-serialized-refresh',
      fresh: serializedFresh,
      ageSeconds: ageSeconds(serialized.timestamp),
      status: serialized.status ?? 'unknown',
      consistencyRecommendation: serializedFinal.consistencyRecommendation ?? null,
      inconsistencies: serializedFinal.inconsistencies ?? [],
      requiresRerunOrder: serializedFinal.requiresRerunOrder ?? null,
    },
    policy: {
      onlySmallLocalCpuUnderWarning: true,
      usesSerializedResourcePreflight: true,
      forbidsWhileWarning: ['gpu-heavy', 'memory-heavy', 'camera-capture', 'microphone-recording', 'model-loads', 'dependency-install', 'persistent-new-processes', 'paid-api'],
      doesNotExecuteSelectedTask: true,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnly: true,
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
  appendAudit({ timestamp, status: doc.status, profile, selected: doc.selected?.id ?? null, resourceLevel, memoryPressure: doc.current.memoryPressure });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, profile, selected: doc.selected?.id ?? null, canonicalPreflightFresh: serializedFresh, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
