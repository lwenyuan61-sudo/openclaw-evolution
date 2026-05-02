import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_self_funding_demo_privacy_verifier_status.json');
const AUDIT = path.join(STATE, 'desktop_wrapper_self_funding_demo_privacy_verifier_audit.jsonl');

const FILES = [
  'state/self_funding_demo_pack.md',
  'state/self_funding_demo_pack.html',
  'state/self_funding_demo_pack.json',
  'state/self_funding_automation_service_offer.md',
  'state/self_funding_automation_service_offer.html',
  'state/self_funding_automation_service_offer.json',
  'state/self_funding_sample_workflow_demo.md',
  'state/self_funding_sample_workflow_demo.html',
  'state/self_funding_sample_workflow_demo.json',
];

function readText(rel) {
  try { return fs.readFileSync(path.join(WORKSPACE, rel), 'utf8'); }
  catch { return ''; }
}
function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}
function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}
function unique(values) {
  return [...new Set(values)].sort();
}
function find(pattern, text) {
  return [...text.matchAll(pattern)].map((m) => m[0]);
}
function redactSamples(samples) {
  return unique(samples).slice(0, 8).map((s) => {
    if (s.includes('@')) return '[email-like]';
    if (s.startsWith('+')) return '[phone-like]';
    return s.replace(/Users\\[^\\\s<>"]+/gi, 'Users\\[user]');
  });
}

function scan(rel) {
  const text = readText(rel);
  const findings = {
    phoneLike: find(/\+\d[\d\s().-]{7,}\d/g, text),
    emailLike: find(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, text),
    privateWindowsUserPath: find(/[A-Z]:\\Users\\[^\s<>"]+/gi, text),
    rawMediaPath: find(/[^\s<>"]+\.(?:wav|mp3|m4a|flac|webm|png|jpe?g|gif|webp)\b/gi, text).filter((item) => !item.includes('app_shell_dashboard.html')),
    tokenLike: find(/\b(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})\b/g, text),
  };
  const counts = Object.fromEntries(Object.entries(findings).map(([key, value]) => [key, value.length]));
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  return { rel, bytes: Buffer.byteLength(text, 'utf8'), counts, total, samples: Object.fromEntries(Object.entries(findings).map(([key, value]) => [key, redactSamples(value)])) };
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const scans = FILES.map(scan);
  const totalFindings = scans.reduce((sum, item) => sum + item.total, 0);
  const missing = FILES.filter((rel) => !fs.existsSync(path.join(WORKSPACE, rel)));
  const doc = {
    timestamp,
    status: totalFindings === 0 && missing.length === 0 ? 'passed' : 'needs-attention',
    mode: 'self-funding-demo-privacy-verifier-read-only',
    filesScanned: FILES.length,
    missing,
    totalFindings,
    scans,
    policy: {
      blocksPhoneNumbers: true,
      blocksAccountEmails: true,
      blocksPrivateWindowsUserPaths: true,
      blocksRawMediaPaths: true,
      blocksCommonTokenPatterns: true,
      allowsLocalDraftText: true,
      allowsDriveFreeSpaceSummary: true,
    },
    safety: {
      readOnly: true,
      startsMicrophone: false,
      startsCamera: false,
      startsGpuWork: false,
      dependencyInstall: false,
      externalNetworkWrites: false,
      sendsMessages: false,
      publicPosting: false,
      financialCommitment: false,
      paidApi: false,
      persistentProcessStarted: false,
      realPhysicalActuation: false,
    },
    auditPath: path.relative(WORKSPACE, AUDIT),
  };
  writeJson(OUT, doc);
  appendAudit({ timestamp, status: doc.status, filesScanned: doc.filesScanned, totalFindings, missing: missing.length });
  console.log(JSON.stringify({
    ok: doc.status === 'passed',
    out: OUT,
    status: doc.status,
    filesScanned: doc.filesScanned,
    missingCount: missing.length,
    totalFindings,
    startsMicrophone: false,
    startsCamera: false,
    startsGpuWork: false,
    dependencyInstall: false,
    externalNetworkWrites: false,
    sendsMessages: false,
    publicPosting: false,
    financialCommitment: false,
    paidApi: false,
    persistentProcessStarted: false,
  }, null, 2));
}

main();
