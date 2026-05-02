import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_policy_state_summary_status.json');
const MD = path.join(STATE, 'resource_policy_state_summary.md');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_policy_state_summary_audit.jsonl');

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

function fmtMiB(value) {
  return typeof value === 'number' ? `${value} MiB` : 'n/a';
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const budget = readJson('state/desktop_wrapper_resource_budget_gate_status.json', {});
  const trend = readJson('state/desktop_wrapper_resource_trend_gate_status.json', {});
  const response = readJson('state/desktop_wrapper_resource_pressure_response_status.json', {});
  const queue = readJson('state/desktop_wrapper_resource_safe_connector_queue_status.json', {});
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json', {});
  const profile = queue.profile ?? response.profile ?? 'unknown';
  const selected = queue.selected?.id ?? null;
  const allowed = response.recommendations?.allowed ?? [];
  const suppressed = response.recommendations?.suppressed ?? [];
  const resourceLevel = resource.resourcePressure?.level ?? 'unknown';
  const memoryPressure = resource.memory?.pressure ?? null;
  const warnings = [...new Set([...(budget.warnings ?? []), ...(trend.warnings ?? []), ...(response.warnings ?? [])])];
  const blocked = [...new Set([...(budget.blocked ?? []), ...(trend.blocked ?? []), ...(response.blocked ?? [])])];
  const md = `# Resource Policy State Summary\n\nGenerated: ${timestamp}\n\n## Current resource state\n\n- Resource level: ${resourceLevel}\n- Profile: ${profile}\n- VRAM: ${fmtMiB(resource.gpus?.[0]?.memoryUsedMiB)} / ${fmtMiB(resource.gpus?.[0]?.memoryTotalMiB)}\n- RAM: ${fmtMiB(resource.memory?.usedMiB)} / ${fmtMiB(resource.memory?.totalMiB)} · pressure ${memoryPressure ?? 'n/a'}\n- Workspace disk free: ${fmtMiB((resource.disks ?? []).find((item) => item?.isWorkspaceDrive)?.freeMiB)}\n- Memory trend: ${trend.trends?.memory?.direction ?? 'n/a'} · delta ${trend.trends?.memory?.delta ?? 'n/a'}\n\n## Active autonomy policy\n\nAllowed while this profile is active:\n${allowed.map((item) => `- ${item}`).join('\n') || '- n/a'}\n\nSuppressed while this profile is active:\n${suppressed.map((item) => `- ${item}`).join('\n') || '- n/a'}\n\n## Selected safe connector class\n\n- Selected: ${selected ?? 'none'}\n- Reason: stay useful under RAM warning by choosing read-only / small-local-CPU / no-organ / no-model-load work.\n\n## Gates\n\n- Budget gate: ${budget.status ?? 'missing'}\n- Trend gate: ${trend.status ?? 'missing'}\n- Pressure response: ${response.status ?? 'missing'}\n- Safe connector queue: ${queue.status ?? 'missing'}\n- Test matrix: ${matrix.status ?? 'missing'} ${matrix.passedCount ?? '?'} / ${matrix.totalCount ?? '?'}\n- Warnings: ${warnings.length ? warnings.join(', ') : 'none'}\n- Blocked: ${blocked.length ? blocked.join(', ') : 'none'}\n\n## Safety\n\nThis summary is read-only. It does not start microphone/camera/GPU work, does not allocate large memory, does not install dependencies, does not start persistent processes, and does not call paid APIs.\n`;
  const doc = {
    timestamp,
    status: blocked.length ? 'blocked' : 'ready',
    mode: 'resource-policy-state-summary-read-only',
    resourceLevel,
    profile,
    current: {
      memoryPressure,
      memoryUsedMiB: resource.memory?.usedMiB ?? null,
      memoryTotalMiB: resource.memory?.totalMiB ?? null,
      gpuVramUsedMiB: resource.gpus?.[0]?.memoryUsedMiB ?? null,
      gpuVramTotalMiB: resource.gpus?.[0]?.memoryTotalMiB ?? null,
      workspaceDiskFreeMiB: (resource.disks ?? []).find((item) => item?.isWorkspaceDrive)?.freeMiB ?? null,
      memoryTrend: trend.trends?.memory?.direction ?? null,
      memoryTrendDelta: trend.trends?.memory?.delta ?? null,
    },
    allowed,
    suppressed,
    selectedConnector: selected,
    canonicalPreflight: queue.canonicalPreflight ?? null,
    warnings,
    blocked,
    markdownPath: path.relative(WORKSPACE, MD),
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
  write(MD, md);
  write(OUT, `${JSON.stringify(doc, null, 2)}\n`);
  appendAudit({ timestamp, status: doc.status, profile, resourceLevel, memoryPressure, selectedConnector: selected, warnings, blocked });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, markdown: MD, status: doc.status, profile, resourceLevel, selectedConnector: selected, warnings: warnings.length, blocked: blocked.length, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
