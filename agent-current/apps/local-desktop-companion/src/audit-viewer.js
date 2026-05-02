import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_audit_view_status.json');

const SOURCES = [
  { id: 'wrapper-control-preview', path: 'state/desktop_wrapper_control_preview_audit.jsonl' },
  { id: 'service-control', path: 'state/service_control_audit_log.jsonl' },
  { id: 'voice-calibration', path: 'state/voice_calibration_ledger.jsonl' },
  { id: 'physical-simulator', path: 'state/physical_actuation_simulator_log.jsonl' },
  { id: 'control-endpoint', path: 'state/desktop_wrapper_control_endpoint_audit.jsonl' },
];

function parseJsonl(rel) {
  const abs = path.join(WORKSPACE, rel);
  if (!fs.existsSync(abs)) return { exists: false, events: [] };
  const text = fs.readFileSync(abs, 'utf8');
  const events = [];
  for (const [idx, line] of text.split(/\r?\n/).entries()) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const obj = JSON.parse(trimmed);
      events.push({ line: idx + 1, ...obj });
    } catch (error) {
      events.push({ line: idx + 1, status: 'parse-error', error: `${error.name}: ${error.message}` });
    }
  }
  return { exists: true, events };
}

function classify(event) {
  const sensitive = Boolean(
    event.executesSensitiveAction ||
    event.realPhysicalActuation ||
    event.realDeviceCalled ||
    event.microphone ||
    event.camera ||
    event.alwaysOnMicEnabled ||
    event.externalUpload ||
    event.externalNetworkWrites
  );
  const mutation = Boolean(
    event.mutatesAppControlState ||
    event.executedSystemChange ||
    event.recordingStarted ||
    event.rawAudioCreated ||
    event.pauseAll !== undefined ||
    event.rawAudioKept
  );
  const blocked = event.status === 'blocked' || event.allowed === false || String(event.reason ?? '').includes('blocked');
  return { sensitive, mutation, blocked };
}

function main() {
  const timestamp = new Date().toISOString();
  const sourceSummaries = [];
  const merged = [];
  for (const source of SOURCES) {
    const parsed = parseJsonl(source.path);
    const events = parsed.events.map((event) => ({ source: source.id, ...event, classification: classify(event) }));
    merged.push(...events);
    sourceSummaries.push({
      id: source.id,
      path: source.path,
      exists: parsed.exists,
      eventCount: events.length,
      blockedCount: events.filter((e) => e.classification.blocked).length,
      mutationCount: events.filter((e) => e.classification.mutation).length,
      sensitiveCount: events.filter((e) => e.classification.sensitive).length,
    });
  }
  merged.sort((a, b) => String(a.timestamp ?? '').localeCompare(String(b.timestamp ?? '')));
  const recent = merged.slice(-25);
  const sensitiveCount = merged.filter((e) => e.classification.sensitive).length;
  const mutationCount = merged.filter((e) => e.classification.mutation).length;
  const blockedCount = merged.filter((e) => e.classification.blocked).length;
  const doc = {
    timestamp,
    status: 'ok',
    mode: 'local-audit-viewer',
    sourceCount: SOURCES.length,
    eventCount: merged.length,
    blockedCount,
    mutationCount,
    sensitiveCount,
    sourceSummaries,
    recent,
    interpretation: {
      sensitiveCountMeaning: 'Events classified as potentially sensitive; inspect before enabling real actions.',
      mutationCountMeaning: 'Includes reversible pause/resume previews/executions or local ledger/status writes; not external writes by itself.',
      blockedCountMeaning: 'Expected for gated capabilities such as always-on mic, rollback execution, or endpoint execute attempts.',
    },
    safety: {
      externalNetworkWrites: false,
      persistentInstall: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
      mutatesRuntimeControlState: false,
    },
  };
  fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT, eventCount: doc.eventCount, blockedCount, mutationCount, sensitiveCount }, null, 2));
}

main();
