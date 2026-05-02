import fs from 'node:fs';
import path from 'node:path';
import childProcess from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_test_matrix_status.json');

const NODE = process.execPath;
function currentResourceLevel() {
  return readJson('core/resource-state.json', {})?.resourcePressure?.level ?? 'unknown';
}
function resourceWarningActive() {
  return currentResourceLevel() === 'warning';
}
function resourceSafeDegrade(j) {
  return resourceWarningActive() && ['blocked', 'needs-attention', 'warn'].includes(j?.status) && j?.startsMicrophone !== true && j?.recordsAudio !== true && j?.startsCamera !== true && j?.capturesFrame !== true;
}
const TESTS = [
  { id: 'syntax-preview-server', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/preview-server.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-control-preview', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/control-preview.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-diagnostics-export', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/diagnostics-export.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-tray-contract', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/tray-contract.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-tray-readiness', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/tray-readiness.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-packaging-preflight', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/packaging-preflight.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-fallback-plan', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/electron-fallback-plan.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-budget-gate', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-budget-gate.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-trend-gate', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-trend-gate.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-pressure-response', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-pressure-response.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-recovery-gate', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-recovery-gate.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-profile-sync', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-profile-sync.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-gate-consistency-audit', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-gate-consistency-audit.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-gate-serialized-refresh', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-gate-serialized-refresh.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-sensitive-action-resource-preflight', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/sensitive-action-resource-preflight.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-action-clearance-ticket', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-action-clearance-ticket.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-action-clearance-verifier', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-action-clearance-verifier.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-guarded-action-wrapper', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-guarded-action-wrapper.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-guard-integration-map', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-guard-integration-map.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-guard-enforcement-scorecard', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-guard-enforcement-scorecard.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-external-action-guard', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/external-action-guard.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-quiet-hours-action-gate', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/quiet-hours-action-gate.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-deferred-organ-calibration-queue', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/deferred-organ-calibration-queue.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-organ-calibration-resume-packet', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/organ-calibration-resume-packet.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-organ-calibration-resume-readiness-audit', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/organ-calibration-resume-readiness-audit.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-quiet-hours-progress-batcher', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/quiet-hours-progress-batcher.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-self-funding-value-ledger', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/self-funding-value-ledger.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-self-funding-offer-draft', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/self-funding-offer-draft.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-self-funding-demo-pack', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/self-funding-demo-pack.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-self-funding-demo-privacy-verifier', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/self-funding-demo-privacy-verifier.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-self-funding-roi-calculator', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/self-funding-roi-calculator.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-safe-connector-queue', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-safe-connector-queue.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-resource-policy-state-summary', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/resource-policy-state-summary.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-docs-consolidate', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/docs-consolidate.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-audit-viewer', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/audit-viewer.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-audit-log-compaction-plan', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/audit-log-compaction-plan.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-audit-log-tail-fingerprint', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/audit-log-tail-fingerprint.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-audit-log-streaming-manifest', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/audit-log-streaming-manifest.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-home-summary', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/home-summary.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-service-recovery-drill', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/service-recovery-drill.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-multi-agent-board', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/multi-agent-board.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-physical-scenario-matrix', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/physical-scenario-matrix.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-next-connector-queue', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/next-connector-queue.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-body-readiness', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-body-readiness-matrix.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-wake-boundary', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-wake-boundary.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-vad-measurement-dry-run', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-vad-measurement-dry-run.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-vad-measurement-runner', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-vad-measurement-runner.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-vad-baseline-evaluator', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-vad-baseline-evaluator.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-spoken-wake-boundary', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-spoken-wake-boundary.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-wake-engine-readiness', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-wake-engine-readiness.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-spoken-wake-calibration-runner', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-spoken-wake-calibration-runner.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-phrase-retention-verifier', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-phrase-retention-verifier.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-phrase-match-verifier', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-phrase-match-verifier.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-voice-wake-end-to-end-gate', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/voice-wake-end-to-end-gate.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-multi-agent-handoff-ruleset', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/multi-agent-handoff-ruleset.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-approval-gate-register', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/approval-gate-register.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-release-readiness-scorecard', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/release-readiness-scorecard.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-morning-progress-digest', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/morning-progress-digest.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-decision-boundary-packet', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/decision-boundary-packet.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-scaffold-status', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/electron-scaffold-status.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-body-indicator-status', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/body-indicator-status.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-body-control-contract', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/body-control-contract.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-camera-single-frame-dry-run', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/camera-single-frame-dry-run.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-camera-single-frame-capture', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/camera-single-frame-capture.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-camera-privacy-verifier', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/camera-privacy-verifier.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-camera-visual-analysis-boundary', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/camera-visual-analysis-boundary.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-camera-visual-semantic-extractor', kind: 'syntax', args: ['--check', 'apps/local-desktop-companion/src/camera-visual-semantic-extractor.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-main', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/main.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-preload', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/preload.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-smoke-test', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/smoke-test.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-menu-status', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/menu-status.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-menu-actions', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/menu-actions.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-menu-action-test', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/menu-action-test.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-tray-status', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/tray-status.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-persistent-smoke', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/persistent-smoke.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-autostart-readiness', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/autostart-readiness.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-autostart-control', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/autostart-control.js'], expect: (r) => r.status === 0 },
  { id: 'syntax-electron-shell-autostart-rollback-drill', kind: 'syntax', args: ['--check', 'apps/local-desktop-electron-shell/src/autostart-rollback-drill.js'], expect: (r) => r.status === 0 },
  { id: 'wrapper-status-ready', kind: 'status', args: ['apps/local-desktop-companion/src/preview-server.js', '--status'], expectJson: (j) => j.status === 'ready' },
  { id: 'wrapper-serve-preflight-ready', kind: 'status', args: ['apps/local-desktop-companion/src/preview-server.js', '--serve-preflight'], expectJson: (j) => j.status === 'ready' && j.persistentProcessStarted === false && j.safety?.persistentProcessStarted === false && j.clearance?.parsed?.requestedClass === 'persistent-new-process' },
  { id: 'endpoint-self-test-passed', kind: 'status', args: ['apps/local-desktop-companion/src/preview-server.js', '--endpoint-self-test'], expectJson: (j) => j.status === 'passed' && j.mutatesAppControlState === false },
  { id: 'home-routes-self-test-passed', kind: 'status', args: ['apps/local-desktop-companion/src/preview-server.js', '--home-routes-self-test'], expectJson: (j) => j.status === 'passed' && j.safety?.externalNetworkWrites === false },
  { id: 'controls-ready', kind: 'status', args: ['apps/local-desktop-companion/src/control-preview.js', '--status'], expectJson: (j) => j.status === 'ready' && j.safety?.executesSensitiveAction === false },
  { id: 'mic-preview-approved', kind: 'gate', args: ['apps/local-desktop-companion/src/control-preview.js', '--preview-control', '--control', 'microphone-always-on'], expectJson: (j) => ['previewed', 'requires-gate'].includes(j.status) && j.executesSensitiveAction === false },
  { id: 'diagnostics-ok', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/diagnostics-export.js'], expectJson: (j) => j.ok === true && j.summary?.status === 'ok' },
  { id: 'tray-readiness-pass', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/tray-readiness.js'], expectJson: (j) => j.ok === true && j.status === 'ready-for-native-scaffold-decision' },
  { id: 'packaging-preflight-no-install', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/packaging-preflight.js'], expectJson: (j) => j.ok === true && j.recommendation && j.tauriReady === false },
  { id: 'electron-plan-no-install', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/electron-fallback-plan.js'], expectJson: (j) => j.ok === true && j.packageInstallPerformedNow === false && j.scaffoldCreatedNow === false },
  { id: 'audit-viewer-ok', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/audit-viewer.js'], expectJson: (j) => j.ok === true && j.sensitiveCount === 0 },
  { id: 'audit-log-compaction-plan-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/audit-log-compaction-plan.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.proposalOnly === true && j.deletesFiles === false && j.truncatesFiles === false && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.persistentProcessStarted === false },
  { id: 'audit-log-tail-fingerprint-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/audit-log-tail-fingerprint.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.fingerprintCount >= 1 && j.storesRawTailContent === false && j.fullFileRead === false && j.deletesFiles === false && j.truncatesFiles === false && j.compressesFilesNow === false && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.persistentProcessStarted === false },
  { id: 'audit-log-streaming-manifest-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/audit-log-streaming-manifest.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.entryCount >= 1 && j.streamingOnly === true && j.storesRawContent === false && j.deletesFiles === false && j.truncatesFiles === false && j.compressesFilesNow === false && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.persistentProcessStarted === false },
  { id: 'home-summary-ok', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/home-summary.js'], expectJson: (j) => j.ok === true && ['ok', 'warning'].includes(j.resourcePressure) },
  { id: 'resource-budget-gate-ok', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-budget-gate.js'], expectJson: (j) => j.ok === true && ['ready', 'warning'].includes(j.status) && j.blocked.length === 0 && j.largeDiskWritesAllowed === true },
  { id: 'resource-trend-gate-ok', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-trend-gate.js'], expectJson: (j) => j.ok === true && ['ready', 'warning'].includes(j.status) && j.blocked.length === 0 },
  { id: 'resource-pressure-response-ok', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-pressure-response.js'], expectJson: (j) => j.ok === true && ['ready', 'warning'].includes(j.status) && j.blocked.length === 0 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.persistentProcessStarted === false },
  { id: 'resource-recovery-gate-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-recovery-gate.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && Boolean(j.recommendedProfile) && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-profile-sync-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-profile-sync.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && Boolean(j.effectiveProfile) && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-gate-consistency-audit-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-gate-consistency-audit.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-gate-serialized-refresh-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-gate-serialized-refresh.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.final?.inconsistencies?.length === 0 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'sensitive-action-resource-preflight-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/sensitive-action-resource-preflight.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.fresh === true && j.blockedCount >= 1 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-action-clearance-ticket-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-action-clearance-ticket.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.valid === true && j.allowedWorkClasses?.includes('read-only-probes') && j.deniedWorkClassCount >= 1 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-action-clearance-verifier-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-action-clearance-verifier.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.allowedNow === true && j.readOnlyAllowed === true && j.paidApiDenied === true && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-guarded-action-wrapper-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-guarded-action-wrapper.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.allowedByTicket === true && j.wouldExecute === false && j.readOnlyAllowed === true && j.paidApiDenied === true && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-guard-integration-map-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-guard-integration-map.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.integrationCount >= 6 && j.allowedCount === 1 && j.deniedCount >= 5 && j.mismatches?.length === 0 && j.sensitiveLeaks?.length === 0 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-guard-enforcement-scorecard-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-guard-enforcement-scorecard.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.score === 100 && j.hookedCount === j.totalCount && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'external-action-guard-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/external-action-guard.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.blockedExternalCount >= 3 && j.mismatches?.length === 0 && j.externalNetworkWrites === false && j.paidApi === false && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'quiet-hours-action-gate-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/quiet-hours-action-gate.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.quietHours === true && j.selected === 'guard-consolidation-read-only' && j.suppressedCount >= 3 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'deferred-organ-calibration-queue-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/deferred-organ-calibration-queue.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.selectedWhenAllowed === 'voice-spoken-wake-armed-calibration' && j.deferredCount >= 2 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'organ-calibration-resume-packet-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/organ-calibration-resume-packet.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.resumeWhen === 'after-quiet-hours-or-Lee-explicitly-active' && j.executableNow === false && j.selectedDeferredItem === 'voice-spoken-wake-armed-calibration' && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'organ-calibration-resume-readiness-audit-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/organ-calibration-resume-readiness-audit.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.quietHours === true && j.executableNow === false && j.failed?.length === 0 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'quiet-hours-progress-batcher-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/quiet-hours-progress-batcher.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.quietHours === true && j.shouldReportNow === false && j.batchCount >= 1 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'self-funding-value-ledger-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/self-funding-value-ledger.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.entryCount >= 1 && j.totalEstimatedMinutes >= 1 && j.reserveFloor === 10 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'self-funding-offer-draft-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/self-funding-offer-draft.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.pricingHypothesisCount >= 3 && j.proofPointCount >= 4 && j.sendsMessages === false && j.publicPosting === false && j.financialCommitment === false && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'self-funding-demo-pack-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/self-funding-demo-pack.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.cardCount >= 3 && j.assetCount >= 5 && j.localDraftOnly === true && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.sendsMessages === false && j.publicPosting === false && j.financialCommitment === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'self-funding-demo-privacy-verifier-passed', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/self-funding-demo-privacy-verifier.js'], expectJson: (j) => j.ok === true && j.status === 'passed' && j.filesScanned >= 6 && j.missingCount === 0 && j.totalFindings === 0 && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.sendsMessages === false && j.publicPosting === false && j.financialCommitment === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'self-funding-roi-calculator-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/self-funding-roi-calculator.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.scenarioCount >= 3 && j.targetMonthlyQuotaBudgetAud >= 1 && j.reserveFloor === 10 && j.sendsMessages === false && j.publicPosting === false && j.financialCommitment === false && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.externalNetworkWrites === false && j.paidApi === false && j.persistentProcessStarted === false },
  { id: 'resource-safe-connector-queue-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-safe-connector-queue.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && Boolean(j.selected) && j.canonicalPreflightFresh === true && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'resource-policy-state-summary-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/resource-policy-state-summary.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && Boolean(j.selectedConnector) && j.startsMicrophone === false && j.startsCamera === false && j.startsGpuWork === false && j.dependencyInstall === false && j.persistentProcessStarted === false },
  { id: 'service-recovery-drill-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/service-recovery-drill.js'], expectJson: (j) => (j.ok === true && j.status === 'ready') || (resourceWarningActive() && j.status === 'needs-attention' && (j.warningIds ?? []).includes('resource-pressure-ok-for-drill')) },
  { id: 'multi-agent-board-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/multi-agent-board.js'], expectJson: (j) => j.ok === true && j.activeRoles >= 5 },
  { id: 'physical-scenario-matrix-passed', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/physical-scenario-matrix.js'], expectJson: (j) => j.ok === true && j.passedCount === j.scenarioCount },
  { id: 'next-connector-queue-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/next-connector-queue.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && Boolean(j.selected) && j.selected !== 'voice-body-readiness-matrix') || (resourceWarningActive() && j.status === 'blocked' && j.resourcePressure === 'warning') },
  { id: 'voice-body-readiness-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-body-readiness-matrix.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.blockedIds.length === 0) || (resourceWarningActive() && j.status === 'needs-attention' && (j.blockedIds ?? []).includes('resource-fit')) },
  { id: 'voice-wake-boundary-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-wake-boundary.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.boundaryOnly === true && j.startsMicrophone === false && j.recordsAudio === false) || (resourceSafeDegrade(j) && j.boundaryOnly === true) },
  { id: 'voice-vad-measurement-dry-run-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-vad-measurement-dry-run.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.dryRunOnly === true && j.startsMicrophone === false && j.recordsAudio === false) || (resourceSafeDegrade(j) && j.dryRunOnly === true) },
  { id: 'voice-vad-measurement-runner-status-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-vad-measurement-runner.js'], expectJson: (j) => (j.ok === true && ['ready', 'measured-metrics-only'].includes(j.status) && j.startsMicrophone === false && j.storesRawAudio === false && j.indicatorRestored === true) || (resourceSafeDegrade(j) && j.storesRawAudio === false && j.indicatorRestored === true) },
  { id: 'voice-vad-baseline-evaluator-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-vad-baseline-evaluator.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.evaluatorOnly === true && j.startsMicrophone === false && j.recordsAudio === false) || (resourceSafeDegrade(j) && j.evaluatorOnly === true) },
  { id: 'voice-spoken-wake-boundary-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-spoken-wake-boundary.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.boundaryOnly === true && j.startsMicrophone === false && j.recordsAudio === false) || (resourceSafeDegrade(j) && j.boundaryOnly === true) },
  { id: 'voice-wake-engine-readiness-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-wake-engine-readiness.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.readinessOnly === true && j.startsMicrophone === false && j.recordsAudio === false && j.installPerformedNow === false) || (resourceSafeDegrade(j) && j.readinessOnly === true && j.installPerformedNow === false) },
  { id: 'voice-spoken-wake-calibration-runner-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-spoken-wake-calibration-runner.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.runnerReady === true && j.startsMicrophone === false && j.storesRawAudio === false && j.indicatorRestored === true) || (resourceSafeDegrade(j) && j.storesRawAudio === false && j.indicatorRestored === true) },
  { id: 'voice-phrase-retention-verifier-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-phrase-retention-verifier.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.verifierOnly === true && j.startsMicrophone === false && j.recordsAudio === false && j.rawLeftoverCount === 0) || (resourceSafeDegrade(j) && j.verifierOnly === true && j.rawLeftoverCount === 0) },
  { id: 'voice-phrase-match-verifier-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-phrase-match-verifier.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.verifierOnly === true && j.startsMicrophone === false && j.recordsAudio === false && j.selfTestPassed === true) || (resourceSafeDegrade(j) && j.verifierOnly === true && j.selfTestPassed === true) },
  { id: 'voice-wake-end-to-end-gate-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/voice-wake-end-to-end-gate.js'], expectJson: (j) => (j.ok === true && j.status === 'ready-for-armed-calibration' && j.gateOnly === true && j.startsMicrophone === false && j.recordsAudio === false && j.readyForArmedCalibration === true) || (resourceSafeDegrade(j) && j.gateOnly === true) },
  { id: 'multi-agent-handoff-rules-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/multi-agent-handoff-ruleset.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.ruleCount >= 6) || (resourceWarningActive() && j.status === 'needs-attention' && j.ruleCount >= 6) },
  { id: 'approval-gate-register-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/approval-gate-register.js'], expectJson: (j) => j.ok === true && j.gateCount >= 8 },
  { id: 'release-readiness-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/release-readiness-scorecard.js'], expectJson: (j) => j.ok === true && ['advanced-prototype', 'prototype'].includes(j.level) },
  { id: 'morning-progress-digest-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/morning-progress-digest.js'], expectJson: (j) => j.ok === true && ['advanced-prototype', 'prototype'].includes(j.level) },
  { id: 'decision-boundary-packet-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/decision-boundary-packet.js'], expectJson: (j) => j.ok === true && j.optionCount >= 5 },
  { id: 'electron-scaffold-status-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/electron-scaffold-status.js'], expectJson: (j) => j.ok === true && j.status === 'scaffold-ready' },
  { id: 'body-indicator-status-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/body-indicator-status.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.microphoneActive === false && j.cameraActive === false) || (resourceWarningActive() && j.status === 'warn' && j.microphoneActive === false && j.cameraActive === false) },
  { id: 'body-control-contract-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/body-control-contract.js', '--preview-start-microphone'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.previewOnly === true && j.activeNow === false) || (resourceSafeDegrade(j) && j.previewOnly === true && j.activeNow === false) },
  { id: 'camera-single-frame-dry-run-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/camera-single-frame-dry-run.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.dryRunOnly === true && j.startsCamera === false && j.capturesFrame === false) || (resourceSafeDegrade(j) && j.dryRunOnly === true) },
  { id: 'camera-single-frame-capture-status-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/camera-single-frame-capture.js'], expectJson: (j) => (j.ok === true && ['ready', 'captured-and-deleted'].includes(j.status) && j.rawImageDeleted === true && j.indicatorRestored === true) || (resourceSafeDegrade(j) && j.rawImageDeleted === true && j.indicatorRestored === true) },
  { id: 'camera-privacy-verifier-passed', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/camera-privacy-verifier.js'], expectJson: (j) => j.ok === true && j.status === 'passed' && j.rawLeftoverCount === 0 && j.verifierOnly === true },
  { id: 'camera-visual-analysis-boundary-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/camera-visual-analysis-boundary.js'], expectJson: (j) => (j.ok === true && j.status === 'ready' && j.boundaryOnly === true && j.analyzesImageNow === false) || (resourceSafeDegrade(j) && j.boundaryOnly === true && j.analyzesImageNow === false) },
  { id: 'camera-visual-semantic-extractor-status-ready', kind: 'diagnostic', args: ['apps/local-desktop-companion/src/camera-visual-semantic-extractor.js'], expectJson: (j) => (j.ok === true && ['ready', 'captured-analyzed-and-deleted'].includes(j.status) && j.rawImageDeleted === true && j.indicatorRestored === true) || (resourceSafeDegrade(j) && j.rawImageDeleted === true && j.indicatorRestored === true) },
  { id: 'electron-menu-status-ready', kind: 'diagnostic', args: ['apps/local-desktop-electron-shell/src/menu-status.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.menuItemCount >= 7 },
  { id: 'electron-menu-action-test-passed', kind: 'diagnostic', args: ['apps/local-desktop-electron-shell/src/menu-action-test.js'], expectJson: (j) => j.ok === true && j.status === 'passed' && j.finalPauseAll === false },
  { id: 'electron-tray-status-ready', kind: 'diagnostic', args: ['apps/local-desktop-electron-shell/src/tray-status.js'], expectJson: (j) => j.ok === true && j.status === 'ready' && j.trayItemCount >= 6 },
  { id: 'electron-launch-smoke-passed', kind: 'diagnostic', args: ['apps/local-desktop-electron-shell/src/smoke-test.js'], expectJson: (j) => j.ok === true && j.status === 'passed' },
  { id: 'electron-persistent-smoke-passed', kind: 'diagnostic', args: ['apps/local-desktop-electron-shell/src/persistent-smoke.js'], expectJson: (j) => j.ok === true && j.status === 'passed' },
  { id: 'electron-autostart-readiness-ready', kind: 'diagnostic', args: ['apps/local-desktop-electron-shell/src/autostart-readiness.js'], expectJson: (j) => j.ok === true && j.status === 'ready' },
  { id: 'electron-autostart-control-status-ok', kind: 'diagnostic', args: ['apps/local-desktop-electron-shell/src/autostart-control.js', '--status'], expectJson: (j) => j.ok === true && j.status === 'ok' },
];

function runNode(args) {
  const started = Date.now();
  const result = childProcess.spawnSync(NODE, args, {
    cwd: WORKSPACE,
    encoding: 'utf8',
    windowsHide: true,
    timeout: 30000,
  });
  return {
    status: result.status,
    signal: result.signal,
    durationMs: Date.now() - started,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
    error: result.error ? `${result.error.name}: ${result.error.message}` : null,
  };
}

function parseLastJson(text) {
  const trimmed = String(text ?? '').trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.lastIndexOf('\n{');
    if (start >= 0) {
      try { return JSON.parse(trimmed.slice(start + 1)); } catch {}
    }
    return null;
  }
}

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); } catch { return fallback; }
}

function main() {
  const timestamp = new Date().toISOString();
  const results = TESTS.map((test) => {
    const raw = runNode(test.args);
    const parsed = parseLastJson(raw.stdout);
    let passed = false;
    let reason = 'unknown';
    try {
      if (test.expect) {
        passed = Boolean(test.expect(raw));
      } else if (test.expectJson) {
        passed = Boolean(parsed && test.expectJson(parsed));
      }
      reason = passed ? 'ok' : 'predicate-failed';
    } catch (error) {
      passed = false;
      reason = `${error.name}: ${error.message}`;
    }
    return {
      id: test.id,
      kind: test.kind,
      passed,
      reason,
      status: raw.status,
      durationMs: raw.durationMs,
      error: raw.error,
      stdoutTail: raw.stdout.slice(-800),
      stderrTail: raw.stderr.slice(-800),
    };
  });
  const failed = results.filter((r) => !r.passed);
  const controlState = readJson('state/app_control_state.json', {});
  const doc = {
    timestamp,
    status: failed.length === 0 && controlState.pauseAll === false ? 'passed' : 'warn',
    mode: 'desktop-wrapper-local-test-matrix',
    passedCount: results.length - failed.length,
    totalCount: results.length,
    failedIds: failed.map((r) => r.id),
    finalPauseAll: controlState.pauseAll ?? null,
    results,
    safety: {
      dependencyInstall: false,
      scaffoldCreated: false,
      persistentInstall: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'passed', out: OUT, status: doc.status, passedCount: doc.passedCount, totalCount: doc.totalCount, failedIds: doc.failedIds }, null, 2));
}

main();
