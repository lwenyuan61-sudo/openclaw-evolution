import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT_JSON = path.join(STATE, 'desktop_wrapper_decision_boundary_packet_status.json');
const OUT_MD = path.join(APP_ROOT, 'DECISION_PACKET.md');

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function option(id, title, recommendation, requiresApproval, why, exactApproval, expectedNext, rollback, risks = []) {
  return { id, title, recommendation, requiresApproval, why, exactApproval, expectedNext, rollback, risks };
}

function main() {
  const timestamp = new Date().toISOString();
  const release = readJson('state/desktop_wrapper_release_readiness_status.json');
  const gates = readJson('state/desktop_wrapper_approval_gate_register_status.json');
  const packaging = readJson('state/desktop_wrapper_packaging_preflight_status.json');
  const voice = readJson('state/desktop_wrapper_voice_body_readiness_status.json');
  const digest = readJson('state/desktop_wrapper_morning_progress_digest_status.json');
  const tests = readJson('state/desktop_wrapper_test_matrix_status.json');
  const resource = readJson('core/resource-state.json');

  const options = [
    option(
      'continue-local-hardening',
      'Continue local-only hardening',
      'recommended-default',
      false,
      'Keeps improving safety, diagnostics, UX contracts, and simulator coverage without crossing privacy/install/physical boundaries.',
      null,
      'Run the next local connector selected by the queue; keep all approval-gated paths blocked.',
      'No rollback needed beyond normal git/file review; generated state files can be regenerated.',
      ['Lower productization speed than approving a real packaged shell.']
    ),
    option(
      'approve-electron-scaffold',
      'Approve Electron scaffold/dependency install',
      'best-productization-leap-if-Lee-wants-real-app-now',
      true,
      'Release readiness is advanced-prototype; Electron fallback is recommended because Node/npm are present and Rust/Cargo are unavailable.',
      'Lee approves Electron scaffold and dependency install for local-evolution-agent desktop companion.',
      'Create scaffold under a separate app directory, install bounded dependencies, keep no persistent process unless separately approved, then run regression gates.',
      'Delete scaffold directory / package lock changes if needed; no Gateway rollback required.',
      ['Dependency install modifies local project state.', 'May need follow-up packaging/debug time.', 'Still does not approve always-on mic or real physical devices.']
    ),
    option(
      'approve-manual-voice-calibration',
      'Approve one 3-second local manual voice calibration',
      'best-voice-step-without-always-on-listening',
      true,
      'Voice/body readiness is ready and manual calibration runner already blocks recording unless the explicit token is provided.',
      'LEE_APPROVED_3_SECOND_LOCAL_CALIBRATION',
      'Run one local 3-second capture, show listening indicator, compute metadata/transcription locally if available, delete raw audio by default, write ledger.',
      'No persistent state except metadata ledger; raw audio is deleted by default.',
      ['Momentary microphone access.', 'Transcript/energy metadata may reflect private speech, though no external upload is performed.']
    ),
    option(
      'approve-always-on-voice-wake-later',
      'Approve always-on voice wake later',
      'not-recommended-yet-without-visible-native-shell',
      true,
      'Always-on mic remains intentionally blocked until there is a stronger visible UI indicator/toggle and stop path.',
      'Lee separately approves always-on microphone listener with visible indicator and stop control.',
      'Enable only after indicator, stop/pause path, retention policy, and audit are verified.',
      'Disable listener and clear app control flag; no external upload allowed.',
      ['Continuous privacy-sensitive sensing.', 'CPU/background process reliability work needed.']
    ),
    option(
      'approve-real-device-actuation-later',
      'Approve real physical device action later',
      'not-recommended-until-specific-device-is-known',
      true,
      'Simulator coverage is strong, but real-device actions need a concrete device, target operation, visible UI state, and post-action verification.',
      'Lee approves a specific device + action + risk tier for real actuation.',
      'Add per-device allowlist entry, dry-run first, require kill switch and post-action verification.',
      'Remove allowlist entry and keep simulator-only policy.',
      ['Real-world effects; device-specific failure modes.', 'Dangerous/irreversible T3 actions remain blocked.']
    ),
  ];

  const doc = {
    timestamp,
    status: 'ready',
    mode: 'decision-boundary-packet-local-only',
    release: release.overall ?? {},
    digest: { status: digest.status, headline: digest.headline },
    regression: { status: tests.status, passed: tests.passedCount, total: tests.totalCount, failedIds: tests.failedIds ?? [] },
    resource: { pressure: resource.resourcePressure?.level ?? 'unknown', gpuUsedMiB: resource.gpus?.[0]?.memoryUsedMiB ?? null, gpuFreeMiB: resource.gpus?.[0]?.memoryFreeMiB ?? null },
    approvalGateCount: gates.gateCount ?? 0,
    approvalGatedCount: gates.approvalGatedCount ?? 0,
    packagingRecommendation: packaging.recommendation ?? packaging.packageRecommendation ?? 'unknown',
    voiceReadiness: { status: voice.status, recordingNow: voice.summary?.recordingNow ?? false, alwaysOnMicEnabled: voice.summary?.alwaysOnMicEnabled ?? false },
    options,
    defaultRecommendation: 'continue-local-hardening unless Lee explicitly wants to cross a productization/privacy boundary now',
    safety: {
      packetOnly: true,
      externalSendPerformed: false,
      approvalGrantedByThisPacket: false,
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
    '# Local Evolution Agent Desktop Companion · Decision Boundary Packet',
    '',
    `Generated: ${timestamp}`,
    '',
    `Readiness: ${doc.release.level ?? 'unknown'} (${doc.release.score ?? 0}/${doc.release.max ?? 0}, ${doc.release.percent ?? 0}%)`,
    `Regression: ${doc.regression.status} (${doc.regression.passed}/${doc.regression.total})`,
    `Resource: ${doc.resource.pressure}; GPU used/free MiB ${doc.resource.gpuUsedMiB}/${doc.resource.gpuFreeMiB}`,
    `Approval gates: ${doc.approvalGatedCount}/${doc.approvalGateCount}`,
    '',
    '## Default recommendation',
    `- ${doc.defaultRecommendation}`,
    '',
    '## Options',
    ...options.flatMap((item) => [
      `### ${item.id}`,
      `- Title: ${item.title}`,
      `- Recommendation: ${item.recommendation}`,
      `- Requires approval: ${item.requiresApproval}`,
      `- Why: ${item.why}`,
      `- Exact approval text/token: ${item.exactApproval ?? 'none'}`,
      `- Expected next: ${item.expectedNext}`,
      `- Rollback: ${item.rollback}`,
      `- Risks: ${item.risks.length ? item.risks.join('; ') : 'none'}`,
      '',
    ]),
    '## Safety',
    '- Packet only. No external send, approval grant, permission change, install, scaffold, persistent process, mic/camera access, or real physical actuation.',
    '',
  ].join('\n');

  fs.writeFileSync(OUT_JSON, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  fs.writeFileSync(OUT_MD, md, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT_JSON, packet: OUT_MD, optionCount: options.length, defaultRecommendation: doc.defaultRecommendation, releaseLevel: doc.release.level ?? null }, null, 2));
}

main();
