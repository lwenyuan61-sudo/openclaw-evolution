import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_multi_agent_handoff_rules_status.json');

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function role(mode, id) {
  return (mode.roles || []).find((item) => item.id === id) || { id, allowedActions: [], mustNot: [] };
}

function rule(id, when, delegateTo, requiredInputs, exitCriteria, gates = []) {
  return { id, when, delegateTo, requiredInputs, exitCriteria, gates };
}

function main() {
  const timestamp = new Date().toISOString();
  const mode = readJson('core/multi-agent-mode.json', { roles: [], principles: {}, spawnPolicy: {} });
  const coordination = readJson('state/multi_agent_coordination.json', {});
  const resource = readJson('core/resource-state.json', {});
  const queue = readJson('state/desktop_wrapper_next_connector_queue_status.json', {});
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json', {});

  const roles = ['architect', 'researcher', 'builder', 'auditor', 'resource-guardian'].map((id) => {
    const r = role(mode, id);
    return {
      id,
      active: (coordination.activeSpecialistSlots || []).includes(id),
      allowedActions: r.allowedActions || [],
      mustNot: r.mustNot || [],
      defaultRuntime: r.defaultRuntime,
    };
  });

  const rules = [
    rule(
      'architecture-before-broad-track-change',
      'Use when the next connector would change architecture, persistence model, app shell direction, or embodiment ladder.',
      ['architect'],
      ['current focus', 'resource state', 'existing app-shell/continuity state'],
      ['architect report with <=3 options', 'main persona selects one option'],
      ['no direct external speech', 'no unverified core behavior change']
    ),
    rule(
      'research-before-new-external-tech',
      'Use when a connector depends on unfamiliar libraries, platform APIs, wake-word stacks, packaging tech, or hardware APIs.',
      ['researcher'],
      ['local docs first', 'free/read-only web only if needed', 'resource guard'],
      ['bounded report', 'no paid API use', 'no install performed'],
      ['no external posting', 'no paid/GPU-heavy research without approval']
    ),
    rule(
      'builder-for-local-reversible-connector',
      'Use when a candidate is local-only, reversible, small, and has clear verification gates.',
      ['builder'],
      ['selected queue item', 'allowed files', 'test command', 'rollback note'],
      ['small patch', 'state artifact', 'verification output'],
      ['no destructive operation', 'no bypass of resource guard']
    ),
    rule(
      'auditor-after-builder-or-sensitive-surface',
      'Use after builder changes app controls, physical simulator, voice/body gates, persistence, packaging, or permissions.',
      ['auditor'],
      ['changed files', 'expected safety invariants', 'test artifacts'],
      ['pass/fail report', 'regression risks', 'required fixes if any'],
      ['do not expand scope', 'do not make external writes']
    ),
    rule(
      'resource-guardian-before-heavy-or-parallel-work',
      'Use before GPU/model work, dependency-heavy tests, multiple subagents, packaging, or long-running processes.',
      ['resource-guardian'],
      ['core/resource-state.json', 'estimated resource use'],
      ['allow/degrade/queue/offload decision'],
      ['block warning/critical GPU-heavy work']
    ),
    rule(
      'main-persona-for-user-facing-or-approval-boundary',
      'Use for all Lee-facing reporting, external sends, real-world actions, persistent installs, always-on mic, dependency installs, and final judgment.',
      ['main-persona'],
      ['specialist summaries', 'approval requirements', 'risk boundary'],
      ['visible decision or concise report only when useful'],
      ['do not let specialists speak for Lee', 'do not mark visible report sent until main persona sends it']
    ),
  ];

  const spawnChecklist = [
    'Read resource state first; if warning/critical, avoid GPU-heavy or parallel subagents.',
    'Prefer one-shot specialist runs with narrow prompts and report artifacts under state/.',
    'Set cleanup keep-for-audit for important runs; avoid polling loops.',
    'Give builder/auditor explicit safety invariants and minimal verification gates.',
    'Main persona must synthesize and decide; specialist output is advisory.',
  ];

  const selected = queue.selected?.id ?? null;
  const recommendation = selected === 'multi-agent-handoff-ruleset'
    ? 'ruleset-is-current-selected-connector'
    : 'ruleset-available-as-orchestration-guard';

  const violations = [];
  if (!mode.principles?.mainPersonaOwnsJudgment) violations.push('main-persona-ownership-not-set');
  if (resource.resourcePressure?.level !== 'ok') violations.push('resource-pressure-not-ok');

  const doc = {
    timestamp,
    status: violations.length === 0 ? 'ready' : 'needs-attention',
    mode: 'multi-agent-handoff-ruleset',
    selectedByQueue: selected === 'multi-agent-handoff-ruleset',
    recommendation,
    resourcePressure: resource.resourcePressure?.level ?? 'unknown',
    activeRoles: roles.filter((r) => r.active).length,
    roleCount: roles.length,
    roles,
    ruleCount: rules.length,
    rules,
    spawnChecklist,
    violations,
    handoffContract: {
      mainPersonaOwnsJudgment: true,
      specialistsAreAdvisory: true,
      reportsBeforeAction: true,
      resourceGuardRequired: true,
      noExternalWritesWithoutApproval: true,
      noSpecialistVisibleUserReport: true,
    },
    safety: {
      spawnedSubagentNow: false,
      selectorOnly: false,
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
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, ruleCount: doc.ruleCount, activeRoles: doc.activeRoles, selectedByQueue: doc.selectedByQueue }, null, 2));
}

main();
