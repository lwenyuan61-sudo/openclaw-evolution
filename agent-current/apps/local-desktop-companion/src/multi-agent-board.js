import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_multi_agent_board_status.json');

const REPORTS = [
  { id: 'architect-sprint', role: 'architect', path: 'state/multi_agent_architect_sprint_report.json' },
  { id: 'auditor-sprint', role: 'auditor', path: 'state/multi_agent_auditor_sprint_report.json' },
  { id: 'sprint-synthesis', role: 'main-persona', path: 'state/multi_agent_sprint_synthesis.json' },
  { id: 'self-evolution-next-connector', role: 'main-persona', path: 'state/self_evolution_next_connector_report.json' },
  { id: 'autonomous-dinner-sprint', role: 'builder/auditor', path: 'state/autonomous_dinner_sprint_report.json' },
];

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function exists(rel) {
  try { return fs.existsSync(path.join(WORKSPACE, rel)); } catch { return false; }
}

function fileMtime(rel) {
  try { return fs.statSync(path.join(WORKSPACE, rel)).mtime.toISOString(); } catch { return null; }
}

function tailJsonl(rel, count = 6) {
  try {
    const text = fs.readFileSync(path.join(WORKSPACE, rel), 'utf8');
    return text.split(/\r?\n/).filter(Boolean).slice(-count).map((line) => {
      try { return JSON.parse(line); } catch { return { parseError: true, raw: line.slice(0, 240) }; }
    });
  } catch {
    return [];
  }
}

function roleStatus(mode, coordination, role) {
  const active = Array.isArray(coordination.activeSpecialistSlots) && coordination.activeSpecialistSlots.includes(role.id);
  const allowed = Array.isArray(role.allowedActions) ? role.allowedActions : [];
  const mustNot = Array.isArray(role.mustNot) ? role.mustNot : [];
  return {
    id: role.id,
    name: role.name,
    active,
    defaultRuntime: role.defaultRuntime,
    job: role.job,
    allowedActions: allowed,
    blockedActions: mustNot,
  };
}

function main() {
  const timestamp = new Date().toISOString();
  const mode = readJson('core/multi-agent-mode.json', { enabled: false, roles: [] });
  const coordination = readJson('state/multi_agent_coordination.json', { enabled: false });
  const resource = readJson('core/resource-state.json', {});
  const experiments = tailJsonl('autonomy/experiment-log.jsonl');

  const roles = (mode.roles || []).map((role) => roleStatus(mode, coordination, role));
  const reportSummaries = REPORTS.map((report) => {
    const doc = readJson(report.path, { status: 'missing' });
    return {
      id: report.id,
      role: report.role,
      path: report.path,
      exists: exists(report.path),
      mtime: fileMtime(report.path),
      status: doc.status ?? (exists(report.path) ? 'present' : 'missing'),
      decision: doc.decision ?? doc.summary ?? doc.recommendation ?? null,
      selectedNextConnector: doc.selectedNextConnector?.id ?? doc.nextConnector?.id ?? null,
    };
  });

  const pending = [];
  const synthesis = readJson('state/multi_agent_sprint_synthesis.json', {});
  if (synthesis.selectedNextConnector?.id) {
    pending.push({ id: synthesis.selectedNextConnector.id, source: 'sprint-synthesis', status: 'implemented-or-in-progress', nextStep: synthesis.selectedNextConnector.nextImplementationStep ?? null });
  }
  pending.push({ id: 'compact-task-board-continuation', source: 'current-main-loop', status: 'created', nextStep: 'Use board to decide when to spawn architect/builder/auditor instead of blind sequential work.' });

  const doc = {
    timestamp,
    status: mode.enabled && coordination.enabled ? 'ready' : 'warn',
    mode: 'multi-agent-task-board-summary',
    coordinationMode: coordination.mode ?? 'unknown',
    currentRule: coordination.currentRule ?? mode.workflow?.[0] ?? 'main persona decides',
    resourcePressure: resource.resourcePressure?.level ?? 'unknown',
    mainPersonaOwnsJudgment: Boolean(mode.principles?.mainPersonaOwnsJudgment),
    roleCount: roles.length,
    activeRoleCount: roles.filter((role) => role.active).length,
    roles,
    reports: reportSummaries,
    recentExperimentTail: experiments.map((event) => ({ id: event.id ?? null, timestamp: event.timestamp ?? null, status: event.status ?? null, type: event.type ?? null, summary: event.summary ?? null })).slice(-6),
    board: {
      currentFocus: mode.currentFocus ?? coordination.nextUse ?? null,
      nextUse: coordination.nextUse ?? null,
      pending,
      spawnPolicy: mode.spawnPolicy ?? {},
      handoffRule: 'Main persona chooses; specialists propose/build/audit; resource guard checked first; no external writes without approval.',
    },
    safety: {
      spawnedSubagentNow: false,
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };

  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, roles: doc.roleCount, activeRoles: doc.activeRoleCount, reports: doc.reports.filter((r) => r.exists).length, resourcePressure: doc.resourcePressure }, null, 2));
}

main();
