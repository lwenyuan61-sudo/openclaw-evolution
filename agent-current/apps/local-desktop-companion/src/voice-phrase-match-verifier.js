import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_voice_phrase_match_verifier_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_voice_phrase_match_verifier_audit.jsonl');

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

function normalize(text) {
  return String(text ?? '')
    .toLowerCase()
    .normalize('NFKC')
    .replace(/[\s\p{P}\p{S}]+/gu, '');
}

function phraseMatched(transcript, phrases) {
  const normalizedTranscript = normalize(transcript);
  const normalizedPhrases = phrases.map((phrase) => ({ phrase, normalized: normalize(phrase) })).filter((item) => item.normalized);
  const hit = normalizedPhrases.find((item) => normalizedTranscript.includes(item.normalized));
  return { matched: Boolean(hit), matchedPhrase: hit?.phrase ?? null, normalizedTranscript, normalizedPhrases };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const resource = readJson('core/resource-state.json', {});
  const boundary = readJson('state/desktop_wrapper_voice_spoken_wake_boundary_status.json', {});
  const retention = readJson('state/desktop_wrapper_voice_phrase_retention_verifier_status.json', {});
  const runner = readJson('state/desktop_wrapper_voice_spoken_wake_calibration_runner_status.json', {});
  const indicator = readJson('state/voice_listening_indicator.json', {});
  const existingResult = readJson('state/voice_spoken_wake_calibration_result.json', {});
  const phrases = boundary.calibrationContract?.recommendedWakeWords ?? ['the agent', 'hey local-evolution-agent'];
  const examples = [
    { id: 'zh-exact', transcript: 'the agent', expected: true },
    { id: 'zh-with-punctuation', transcript: 'the agent。', expected: true },
    { id: 'en-exact', transcript: 'hey local-evolution-agent', expected: true },
    { id: 'en-spaced-case', transcript: 'Hey, Local Evolution Agent!', expected: true },
    { id: 'negative', transcript: 'hello assistant', expected: false },
  ];
  const exampleResults = examples.map((example) => {
    const result = phraseMatched(example.transcript, phrases);
    return { ...example, matched: result.matched, matchedPhrase: result.matchedPhrase, passed: result.matched === example.expected };
  });
  const liveTranscript = existingResult.result?.transcript ?? existingResult.transcript ?? null;
  const liveMatch = liveTranscript ? phraseMatched(liveTranscript, phrases) : null;
  const indicatorIdle = indicator.state === 'idle' && indicator.recordingNow === false && indicator.alwaysOnMicEnabled === false;
  const gates = [
    { id: 'resource-ok', status: resource.resourcePressure?.level === 'ok' ? 'ready' : 'blocked', evidence: resource.resourcePressure?.level ?? 'unknown' },
    { id: 'spoken-boundary-ready', status: boundary.status === 'ready' ? 'ready' : 'blocked', evidence: boundary.status ?? 'missing' },
    { id: 'retention-verifier-ready', status: retention.status === 'ready' && (retention.blocked?.length ?? 0) === 0 ? 'ready' : 'blocked', evidence: { status: retention.status, blocked: retention.blocked ?? [] } },
    { id: 'runner-ready', status: ['ready', 'measured-needs-phrase-confirmation-backend'].includes(runner.status) ? 'ready' : 'blocked', evidence: runner.status ?? 'missing' },
    { id: 'indicator-idle', status: indicatorIdle ? 'ready' : 'blocked', evidence: { state: indicator.state, recordingNow: indicator.recordingNow, alwaysOnMicEnabled: indicator.alwaysOnMicEnabled } },
    { id: 'normalizer-self-test', status: exampleResults.every((item) => item.passed) ? 'ready' : 'blocked', evidence: exampleResults },
  ];
  const blocked = gates.filter((gate) => gate.status === 'blocked');
  const doc = {
    timestamp,
    status: blocked.length === 0 ? 'ready' : 'blocked',
    mode: 'voice-phrase-match-verifier-no-recording',
    phraseSet: phrases,
    normalizer: {
      method: 'NFKC + lowercase + strip whitespace/punctuation/symbols',
      examples: exampleResults,
    },
    liveResult: liveTranscript ? {
      transcriptPresent: true,
      transcriptStored: false,
      matched: liveMatch.matched,
      matchedPhrase: liveMatch.matchedPhrase,
      note: 'Verifier does not persist transcript text beyond this status summary; future runner should store only match/confidence/metrics unless Lee chooses otherwise.',
    } : {
      transcriptPresent: false,
      matched: null,
      note: 'No spoken wake calibration transcript/result exists yet; self-test validates matcher only.',
    },
    futureRunnerContract: {
      input: 'local CPU transcript or in-memory phrase confirmation result',
      outputAllowed: ['phraseMatched', 'matchedPhrase', 'confidence', 'candidateWakeCount', 'rms metrics', 'retention'],
      outputForbidden: ['raw audio bytes/path', 'full transcript by default', 'external upload', 'paid API result', 'persistent listener side effects'],
      mustRunAfter: ['voice-phrase-retention-verifier', 'indicator idle verification'],
    },
    gates,
    blocked: blocked.map((gate) => gate.id),
    auditPath: path.relative(WORKSPACE, AUDIT),
    safety: {
      verifierOnly: true,
      startsMicrophone: false,
      recordsAudio: false,
      readsRawAudio: false,
      storesRawAudio: false,
      transcriptGenerated: false,
      storesTranscriptByDefault: false,
      startsPersistentProcess: false,
      externalNetworkWrites: false,
      paidApi: false,
      gpuHeavy: false,
      realPhysicalActuation: false,
    },
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, blocked: doc.blocked, selfTestPassed: exampleResults.every((item) => item.passed), startsMicrophone: false, recordsAudio: false });
  console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, verifierOnly: true, startsMicrophone: false, recordsAudio: false, selfTestPassed: exampleResults.every((item) => item.passed), blocked: doc.blocked }, null, 2));
}

main();
