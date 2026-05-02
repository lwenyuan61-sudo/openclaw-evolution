import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_service_recovery_drill_status.json');

function readJson(rel, fallback = {}) {
  try {
    return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'));
  } catch (error) {
    return { ...fallback, _error: `${error.name}: ${error.message}` };
  }
}

function taskById(health, id) {
  return (health.tasks || []).find((task) => task.id === id) || null;
}

function main() {
  const timestamp = new Date().toISOString();
  const health = readJson('state/service_health_status.json', { status: 'missing', tasks: [] });
  const schema = readJson('state/service_control_schema.json', { safeActions: {}, blockedDirectActions: {} });
  const resource = readJson('core/resource-state.json', {});
  const gateway = taskById(health, 'openclaw-gateway');
  const watchdog = taskById(health, 'openclaw-gateway-watchdog');

  const checks = [
    {
      id: 'gateway-task-registered',
      status: gateway?.registered === true ? 'pass' : 'warn',
      evidence: { registered: gateway?.registered ?? null, queryOk: gateway?.queryOk ?? null },
    },
    {
      id: 'watchdog-task-registered',
      status: watchdog?.registered === true ? 'pass' : 'warn',
      evidence: { registered: watchdog?.registered ?? null, queryOk: watchdog?.queryOk ?? null },
    },
    {
      id: 'gateway-loopback-connectivity',
      status: health.gatewayConnectivityOk === true ? 'pass' : 'warn',
      evidence: { gatewayConnectivityOk: health.gatewayConnectivityOk ?? null },
    },
    {
      id: 'watchdog-last-status',
      status: health.watchdogLastStatusOk === true ? 'pass' : 'warn',
      evidence: { watchdogLastStatusOk: health.watchdogLastStatusOk ?? null, watchdogAction: health.watchdogStatus?.action ?? null },
    },
    {
      id: 'missing-required-tasks',
      status: Array.isArray(health.missingRequiredTasks) && health.missingRequiredTasks.length === 0 ? 'pass' : 'warn',
      evidence: { missingRequiredTasks: health.missingRequiredTasks ?? [] },
    },
    {
      id: 'safe-control-schema-present',
      status: Object.keys(schema.safeActions || {}).length >= 3 ? 'pass' : 'warn',
      evidence: { safeActions: Object.keys(schema.safeActions || {}), blockedDirectActions: Object.keys(schema.blockedDirectActions || {}) },
    },
    {
      id: 'resource-pressure-ok-for-drill',
      status: resource.resourcePressure?.level === 'ok' ? 'pass' : 'warn',
      evidence: { resourcePressure: resource.resourcePressure?.level ?? 'unknown' },
    },
  ];

  const blockedActions = Object.entries(schema.blockedDirectActions || {}).map(([id, reason]) => ({
    id,
    expectedStatus: 'blocked-unless-explicit-confirmation',
    reason,
  }));

  const playbook = {
    normalRefresh: [
      'Run core/scripts/service_health_snapshot.py to refresh local service health.',
      'If gateway loopback is reachable and watchdog status is ok, take no restart action.',
    ],
    safeModePreview: schema.safeModePreview || null,
    rollbackPreview: schema.rollbackCommandsPreview || [],
    escalationRules: [
      'Do not execute rollback/safe-mode/restart from preview drill.',
      'If both gateway and watchdog are missing, ask Lee before destructive rollback or reinstall steps.',
      'If only loopback is closed, watchdog may start gateway.cmd according to its existing local policy.',
    ],
  };

  const failedOrWarn = checks.filter((check) => check.status !== 'pass');
  const doc = {
    timestamp,
    status: failedOrWarn.length === 0 ? 'ready' : 'needs-attention',
    mode: 'service-recovery-dry-run-drill',
    healthStatus: health.status ?? 'unknown',
    checkCount: checks.length,
    passedCount: checks.length - failedOrWarn.length,
    warningIds: failedOrWarn.map((check) => check.id),
    checks,
    blockedActions,
    playbook,
    safety: {
      drillOnly: true,
      executedSystemChange: false,
      dependencyInstall: false,
      persistentInstall: false,
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };

  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, passedCount: doc.passedCount, checkCount: doc.checkCount, warningIds: doc.warningIds }, null, 2));
}

main();
