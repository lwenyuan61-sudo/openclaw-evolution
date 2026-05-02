import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_resource_guard_enforcement_scorecard_status.json');
const MD = path.join(STATE, 'resource_guard_enforcement_scorecard.md');
const AUDIT = path.join(STATE, 'desktop_wrapper_resource_guard_enforcement_scorecard_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
}

function readText(rel) {
  try { return fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'); }
  catch { return ''; }
}

function write(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content, 'utf8');
}

function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}

function hasAll(text, needles) {
  return needles.every((needle) => text.includes(needle));
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const ticket = readJson('state/resource_action_clearance_ticket.json', {});
  const guardMap = readJson('state/desktop_wrapper_resource_guard_integration_map_status.json', {});
  const cameraStatus = readJson('state/desktop_wrapper_camera_single_frame_capture_status.json', {});
  const voiceStatus = readJson('state/desktop_wrapper_voice_vad_measurement_runner_status.json', {});
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json', {});
  const files = {
    camera: readText('apps/local-desktop-companion/src/camera-single-frame-capture.js'),
    voice: readText('apps/local-desktop-companion/src/voice-vad-measurement-runner.js'),
    preview: readText('apps/local-desktop-companion/src/preview-server.js'),
    wrapper: readText('apps/local-desktop-companion/src/resource-guarded-action-wrapper.js'),
    verifier: readText('apps/local-desktop-companion/src/resource-action-clearance-verifier.js'),
  };
  const entries = [
    {
      id: 'camera-single-frame-capture',
      class: 'camera-capture',
      path: 'apps/local-desktop-companion/src/camera-single-frame-capture.js',
      hookPresent: hasAll(files.camera, ['resource-action-clearance-verifier.js', "runClearance('camera-capture')", 'clearanceAllowed']),
      lastRuntimeEvidence: {
        status: cameraStatus.status ?? 'unknown',
        startsCamera: cameraStatus.safety?.startsCamera ?? cameraStatus.startsCamera ?? false,
        capturesFrame: cameraStatus.capturesFrame ?? false,
      },
    },
    {
      id: 'voice-vad-measurement-runner',
      class: 'microphone-recording',
      path: 'apps/local-desktop-companion/src/voice-vad-measurement-runner.js',
      hookPresent: hasAll(files.voice, ['resource-action-clearance-verifier.js', "runClearance('microphone-recording')", 'clearanceAllowed']),
      lastRuntimeEvidence: {
        status: voiceStatus.status ?? 'unknown',
        startsMicrophone: voiceStatus.safety?.startsMicrophone ?? voiceStatus.startsMicrophone ?? false,
        recordsAudio: voiceStatus.recordsAudio ?? false,
      },
    },
    {
      id: 'preview-server-serve',
      class: 'persistent-new-process',
      path: 'apps/local-desktop-companion/src/preview-server.js',
      hookPresent: hasAll(files.preview, ['servePreflight', "runClearance('persistent-new-process')", '--serve-preflight']),
      lastRuntimeEvidence: {
        status: 'preflight-only',
        persistentProcessStarted: false,
      },
    },
    {
      id: 'guarded-action-wrapper',
      class: 'all-ticketed-classes',
      path: 'apps/local-desktop-companion/src/resource-guarded-action-wrapper.js',
      hookPresent: hasAll(files.wrapper, ['resource-action-clearance-verifier.js', 'allowedByTicket', 'wouldExecute']),
      lastRuntimeEvidence: {
        status: 'ready',
        commandPreviewOnly: true,
      },
    },
  ];
  const hooked = entries.filter((entry) => entry.hookPresent).length;
  const missing = entries.filter((entry) => !entry.hookPresent).map((entry) => entry.id);
  const guardMapOk = guardMap.status === 'ready' && (guardMap.mismatches ?? []).length === 0 && (guardMap.sensitiveLeaks ?? []).length === 0;
  const matrixOk = matrix.status === 'passed' && (matrix.failedIds ?? []).length === 0;
  const score = Math.round((hooked / entries.length) * 100);
  const status = missing.length === 0 && guardMapOk ? 'ready' : 'needs-attention';
  const doc = {
    timestamp,
    status,
    mode: 'resource-guard-enforcement-scorecard-read-only',
    profile: ticket.profile ?? 'unknown',
    resourceLevel: ticket.resourceLevel ?? 'unknown',
    score,
    hookedCount: hooked,
    totalCount: entries.length,
    missing,
    entries,
    guardMap: {
      status: guardMap.status ?? 'unknown',
      integrationCount: guardMap.integrationCount ?? 0,
      allowedCount: guardMap.allowedCount ?? 0,
      deniedCount: guardMap.deniedCount ?? 0,
      mismatches: guardMap.mismatches ?? [],
      sensitiveLeaks: guardMap.sensitiveLeaks ?? [],
    },
    testMatrix: {
      status: matrix.status ?? 'unknown',
      passedCount: matrix.passedCount ?? null,
      totalCount: matrix.totalCount ?? null,
      failedIds: matrix.failedIds ?? [],
    },
    nextRecommendedHook: 'dependency-install-entrypoint-or-paid-api-adapter-if-created',
    markdownPath: path.relative(WORKSPACE, MD),
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
  const md = `# Resource Guard Enforcement Scorecard\n\nGenerated: ${timestamp}\n\n- Status: ${status}\n- Profile: ${doc.profile}\n- Resource level: ${doc.resourceLevel}\n- Hook coverage: ${hooked}/${entries.length} (${score}%)\n- Guard map: ${guardMapOk ? 'ok' : 'needs attention'}\n- Last completed test matrix: ${matrix.passedCount ?? '?'} / ${matrix.totalCount ?? '?'} ${matrix.status ?? 'unknown'} (informational; not used as a self-referential readiness gate)\n\n## Hooked entrypoints\n\n${entries.map((entry) => `- ${entry.hookPresent ? '✅' : '⚠️'} ${entry.id} → ${entry.class} (${entry.path})`).join('\n')}\n\n## Next\n\n${doc.nextRecommendedHook}\n`;
  write(OUT, `${JSON.stringify(doc, null, 2)}\n`);
  write(MD, md);
  appendAudit({ timestamp, status, score, hookedCount: hooked, totalCount: entries.length, missing });
  console.log(JSON.stringify({ ok: status === 'ready', out: OUT, status, score, hookedCount: hooked, totalCount: entries.length, missing, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, persistentProcessStarted: false }, null, 2));
}

main();
