import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WORKSPACE = path.resolve(__dirname, '..', '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_self_funding_sample_workflow_demo_status.json');
const JSON_OUT = path.join(STATE, 'self_funding_sample_workflow_demo.json');
const MD_OUT = path.join(STATE, 'self_funding_sample_workflow_demo.md');
const HTML_OUT = path.join(STATE, 'self_funding_sample_workflow_demo.html');
const AUDIT = path.join(STATE, 'desktop_wrapper_self_funding_sample_workflow_demo_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch { return fallback; }
}
function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}
function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}
function markdown(doc) {
  return `# ${doc.title}\n\nGenerated: ${doc.timestamp}\n\nPurpose: ${doc.purpose}\n\n## Sanitized input\n\n${doc.inputItems.map((x) => `- ${x}`).join('\n')}\n\n## Dry-run output\n\n${doc.dryRunOutput.map((x) => `- ${x}`).join('\n')}\n\n## Proof\n\n${doc.proof.map((x) => `- ${x}`).join('\n')}\n\n## Boundaries\n\n${doc.boundaries.map((x) => `- ${x}`).join('\n')}\n`;
}
function html(doc) {
  const list = (items) => `<ul>${items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`;
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(doc.title)}</title><style>body{font-family:Inter,Segoe UI,Arial,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;line-height:1.55;color:#1f2937}.badge{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:999px;padding:4px 10px;font-size:13px}section{border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin:16px 0}.guard{background:#fff7ed}</style></head><body><span class="badge">Generated sample data · local dry run</span><h1>${esc(doc.title)}</h1><p>${esc(doc.purpose)}</p><section><h2>Sanitized input</h2>${list(doc.inputItems)}</section><section><h2>Dry-run output</h2>${list(doc.dryRunOutput)}</section><section><h2>Proof</h2>${list(doc.proof)}</section><section class="guard"><h2>Boundaries</h2>${list(doc.boundaries)}</section></body></html>\n`;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const roi = readJson('state/self_funding_roi_calculator.json', {});
  const runbook = readJson('state/self_funding_buyer_runbook.json', {});
  const doc = {
    timestamp,
    status: 'ready',
    title: 'Sample Workflow Demo · Weekly Admin Digest',
    purpose: 'A generated, privacy-safe workflow example for the self-funding pilot: turn messy weekly notes into a concise action digest without touching real client data.',
    selectedPilot: runbook.selectedPilot ?? roi.bestScenarioId ?? 'standard-setup',
    inputItems: [
      'Generated note: invoice from Example Vendor due Friday; confirm amount before payment.',
      'Generated note: draft report needs final proofreading and two citation checks.',
      'Generated note: meeting follow-up has three unanswered action items.',
      'Generated note: local dashboard shows resources OK but memory should be watched.',
    ],
    dryRunOutput: [
      'Priority 1: verify invoice details; no payment action is taken automatically.',
      'Priority 2: proofread report and check citations; produce a change list only.',
      'Priority 3: summarize meeting follow-ups into owner-review checklist.',
      'Ops note: keep heavy automation disabled when memory pressure is elevated.',
    ],
    proof: [
      'Uses generated sample text only, not Lee private files or client data.',
      'Demonstrates dry-run-first automation with explicit forbidden actions.',
      'Maps directly to the buyer runbook qualification checklist.',
      `Supports the ${runbook.selectedPilot ?? 'standard-setup'} pilot hypothesis for quota self-funding.`,
    ],
    boundaries: [
      'No external send, public post, payment, paid API, or subscription change.',
      'No microphone, camera, GPU-heavy work, persistent process, or physical actuation.',
      'No real client data; all sample inputs are generated placeholders.',
      'Human approval remains required before using this with real buyer data.',
    ],
    assets: [
      'state/self_funding_sample_workflow_demo.md',
      'state/self_funding_sample_workflow_demo.html',
      'state/self_funding_buyer_runbook.md',
    ],
    safety: {
      generatedSampleOnly: true,
      localDraftOnly: true,
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
  };
  writeJson(JSON_OUT, doc);
  fs.writeFileSync(MD_OUT, markdown(doc), 'utf8');
  fs.writeFileSync(HTML_OUT, html(doc), 'utf8');
  const status = { ...doc, jsonPath: path.relative(WORKSPACE, JSON_OUT), markdownPath: path.relative(WORKSPACE, MD_OUT), htmlPath: path.relative(WORKSPACE, HTML_OUT), auditPath: path.relative(WORKSPACE, AUDIT) };
  writeJson(OUT, status);
  appendAudit({ timestamp, status: doc.status, selectedPilot: doc.selectedPilot, generatedSampleOnly: true });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, selectedPilot: doc.selectedPilot, inputCount: doc.inputItems.length, outputCount: doc.dryRunOutput.length, generatedSampleOnly: true, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, externalNetworkWrites: false, sendsMessages: false, publicPosting: false, financialCommitment: false, paidApi: false, persistentProcessStarted: false }, null, 2));
}

main();
