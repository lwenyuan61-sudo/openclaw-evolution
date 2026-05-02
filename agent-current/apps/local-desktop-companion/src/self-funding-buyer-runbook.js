import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_self_funding_buyer_runbook_status.json');
const RUNBOOK_JSON = path.join(STATE, 'self_funding_buyer_runbook.json');
const RUNBOOK_MD = path.join(STATE, 'self_funding_buyer_runbook.md');
const RUNBOOK_HTML = path.join(STATE, 'self_funding_buyer_runbook.html');
const AUDIT = path.join(STATE, 'desktop_wrapper_self_funding_buyer_runbook_audit.jsonl');

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
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}
function markdown(doc) {
  const sections = doc.sections.map((section) => `## ${section.title}\n\n${section.items.map((item) => `- ${item}`).join('\n')}`).join('\n\n');
  return `# ${doc.title}\n\nGenerated: ${doc.timestamp}\n\nPurpose: ${doc.purpose}\n\n${sections}\n\n## Approval boundary\n\n${doc.approvalBoundary.join('\n')}\n`;
}
function html(doc) {
  const sections = doc.sections.map((section) => `<section><h2>${esc(section.title)}</h2><ul>${section.items.map((item) => `<li>${esc(item)}</li>`).join('')}</ul></section>`).join('');
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(doc.title)}</title><style>body{font-family:Inter,Segoe UI,Arial,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;line-height:1.55;color:#1f2937}.badge{display:inline-block;background:#ecfdf5;color:#166534;border-radius:999px;padding:4px 10px;font-size:13px}section{border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin:16px 0}.guard{background:#fff7ed}</style></head><body><span class="badge">Local buyer runbook · not sent</span><h1>${esc(doc.title)}</h1><p>${esc(doc.purpose)}</p>${sections}<section class="guard"><h2>Approval boundary</h2><ul>${doc.approvalBoundary.map((item) => `<li>${esc(item)}</li>`).join('')}</ul></section></body></html>\n`;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const roi = readJson('state/self_funding_roi_calculator.json', {});
  const privacy = readJson('state/desktop_wrapper_self_funding_demo_privacy_verifier_status.json', {});
  const demo = readJson('state/self_funding_demo_pack.json', {});
  const bestScenario = (roi.scenarios ?? []).find((item) => item.id === roi.bestScenarioId) ?? null;
  const doc = {
    timestamp,
    status: 'ready',
    title: 'Buyer Runbook · Local AI Automation & Resilience Pack',
    purpose: 'A private, Lee-reviewable runbook for qualifying a first pilot without outreach, publication, payment, or paid APIs.',
    selectedPilot: roi.bestScenarioId ?? 'standard-setup',
    selectedPilotPriceAud: bestScenario?.unitPriceAud ?? 450,
    quotaTargetAud: roi.targetMonthlyQuotaBudgetAud ?? 100,
    privacyStatus: privacy.status ?? 'unknown',
    demoPackTitle: demo.title ?? 'Local Evolution Agent Local AI Automation Demo Pack',
    sections: [
      {
        title: 'Ideal first buyer',
        items: [
          'Has repetitive document, research, workflow, or local admin tasks.',
          'Cares about privacy, audit logs, pause/resume, and avoiding uncontrolled external sends.',
          'Can benefit from a constrained local dashboard and one guarded automation workflow.',
          'Does not require live camera/microphone, paid API, or public deployment in the first pilot.',
        ],
      },
      {
        title: 'Pilot promise',
        items: [
          'Deliver one local dashboard/status snapshot and one small automation workflow.',
          'Include resource/quota guardrails, external-action guard, and a clear recovery/runbook note.',
          'Keep raw media, account identifiers, private paths, and client data out of demo assets by default.',
          `Use the ${roi.bestScenarioId ?? 'standard-setup'} scenario as the first pricing hypothesis; one successful pilot can cover about AUD $${roi.targetMonthlyQuotaBudgetAud ?? 100}/month quota budget.`,
        ],
      },
      {
        title: 'Qualification checklist',
        items: [
          'What task repeats weekly and wastes measurable time?',
          'What local files/apps are involved, and can sample data be sanitized?',
          'What action must never happen automatically: external send, delete, payment, mic/camera, physical control?',
          'What visible artifact proves success: report, dashboard, cleaned document, audit log, or runbook?',
        ],
      },
      {
        title: 'Delivery steps',
        items: [
          'Discovery: choose one workflow and define forbidden actions.',
          'Setup: adapt local dashboard/status cards and resource guard.',
          'Workflow: implement a dry-run-first automation with audit output.',
          'Verification: run privacy scan, smoke checks, and a handoff runbook.',
        ],
      },
      {
        title: 'Do-not-cross boundaries',
        items: [
          'No public posting or customer outreach without Lee approval.',
          'No paid APIs, subscriptions, financial commitment, or client claims without Lee approval.',
          'No real microphone/camera/physical-control action for a buyer pilot unless separately approved and visibly indicated.',
          'No raw private data in demo assets; use sanitized/generated examples first.',
        ],
      },
    ],
    approvalBoundary: [
      'This runbook is local-only and not sent to anyone.',
      'Lee approval is required before outreach, publishing, payments, subscriptions, or client-facing claims.',
      'The next safe local step is to create a sanitized sample workflow/demo dataset.',
    ],
    assets: [
      'state/self_funding_buyer_runbook.md',
      'state/self_funding_buyer_runbook.html',
      'state/self_funding_roi_calculator.md',
      'state/self_funding_demo_pack.md',
    ],
    safety: {
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
  writeJson(RUNBOOK_JSON, doc);
  fs.writeFileSync(RUNBOOK_MD, markdown(doc), 'utf8');
  fs.writeFileSync(RUNBOOK_HTML, html(doc), 'utf8');
  const status = { ...doc, jsonPath: path.relative(WORKSPACE, RUNBOOK_JSON), markdownPath: path.relative(WORKSPACE, RUNBOOK_MD), htmlPath: path.relative(WORKSPACE, RUNBOOK_HTML), auditPath: path.relative(WORKSPACE, AUDIT) };
  writeJson(OUT, status);
  appendAudit({ timestamp, status: doc.status, selectedPilot: doc.selectedPilot, localDraftOnly: true });
  console.log(JSON.stringify({
    ok: true,
    out: OUT,
    status: doc.status,
    selectedPilot: doc.selectedPilot,
    selectedPilotPriceAud: doc.selectedPilotPriceAud,
    sectionCount: doc.sections.length,
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
  }, null, 2));
}

main();
