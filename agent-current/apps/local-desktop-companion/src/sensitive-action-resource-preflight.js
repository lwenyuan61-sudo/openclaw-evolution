import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_sensitive_action_resource_preflight_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_sensitive_action_resource_preflight_audit.jsonl');
const MAX_PROFILE_AGE_SECONDS = 5 * 60;

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
  const profile = readJson('state/desktop_wrapper_resource_profile_sync_status.json', {});
  const response = readJson('state/desktop_wrapper_resource_pressure_response_status.json', {});
  const profileAge = ageSeconds(profile.timestamp);
  const resourceAge = ageSeconds(resource.timestamp);
  const fresh = profileAge !== null && profileAge <= MAX_PROFILE_AGE_SECONDS && resourceAge !== null && resourceAge <= MAX_PROFILE_AGE_SECONDS;
  const effectiveProfile = profile.effectiveProfile ?? response.profile ?? 'unknown';
  const pressureLevel = resource.resourcePressure?.level ?? 'unknown';
  const actions = [
    { id: 'camera-capture', class: 'organ', requiresFresh: true, requiresStable: true },
    { id: 'microphone-recording', class: 'organ', requiresFresh: true, requiresStable: true },
    { id: 'model-load', class: 'memory-heavy', requiresFresh: true, requiresStable: true },
    { id: 'dependency-install', class: 'environment-change', requiresFresh: true, requiresStable: false },
    { id: 'persistent-new-process', class: 'runtime-change', requiresFresh: true, requiresStable: false },
    { id: 'gpu-heavy', class: 'gpu-heavy', requiresFresh: true, requiresStable: true },
    { id: 'memory-heavy', class: 'memory-heavy', requiresFresh: true, requiresStable: true },
    { id: 'paid-api', class: 'external-cost', requiresFresh: true, requiresStable: false },
  ];
  const stableProfiles = new Set(['normal-local-first']);
  const watchProfiles = new Set(['normal-local-first-watch-memory', 'recovery-cooldown']);
  const decisions = actions.map((action) => {
    const reasons = [];
    if (!fresh) reasons.push('stale-resource-profile');
    if (pressureLevel !== 'ok') reasons.push(`resource-${pressureLevel}`);
    if (action.id === 'paid-api') reasons.push('paid-api-default-off');
    if (action.requiresStable && !stableProfiles.has(effectiveProfile)) reasons.push(`profile-not-stable:${effectiveProfile}`);
    if (!action.requiresStable && watchProfiles.has(effectiveProfile)) reasons.push(`fresh-check-required:${effectiveProfile}`);
    const allowedNow = reasons.length === 0;
    return {
      id: action.id,
      class: action.class,
      allowedNow,
      decision: allowedNow ? 'allowed-after-fresh-check' : 'blocked-until-gates-clear',
      reasons,
    };
  });
  const blockedCount = decisions.filter((item) => !item.allowedNow).length;
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'sensitive-action-resource-preflight-read-only',
    effectiveProfile,
    pressureLevel,
    freshness: {
      fresh,
      resourceAgeSeconds: resourceAge,
      profileAgeSeconds: profileAge,
      maxAgeSeconds: MAX_PROFILE_AGE_SECONDS,
    },
    current: {
      memoryPressure: resource.memory?.pressure ?? null,
      memoryUsedMiB: resource.memory?.usedMiB ?? null,
      memoryTotalMiB: resource.memory?.totalMiB ?? null,
      gpuVramUsedMiB: resource.gpus?.[0]?.memoryUsedMiB ?? null,
      workspaceDiskFreeMiB: (resource.disks ?? []).find((item) => item?.isWorkspaceDrive)?.freeMiB ?? null,
    },
    decisions,
    summary: {
      allowedNowCount: decisions.length - blockedCount,
      blockedCount,
      allSensitiveActionsRequireFreshProfile: true,
      paidApiDefaultOff: true,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      readOnly: true,
      mutatesControlState: false,
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
  appendAudit({ timestamp, status: doc.status, effectiveProfile, pressureLevel, fresh, allowedNowCount: doc.summary.allowedNowCount, blockedCount });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, effectiveProfile, pressureLevel, fresh, allowedNowCount: doc.summary.allowedNowCount, blockedCount, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
