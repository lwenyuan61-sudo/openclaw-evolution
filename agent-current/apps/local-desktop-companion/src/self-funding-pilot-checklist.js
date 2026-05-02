import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WORKSPACE = path.resolve(__dirname, '..', '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_self_funding_pilot_checklist_status.json');
const JSON_OUT = path.join(STATE, 'self_funding_pilot_checklist.json');
const MD_OUT = path.join(STATE, 'self_funding_pilot_checklist.md');
const AUDIT = path.join(STATE, 'desktop_wrapper_self_funding_pilot_checklist_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch { return fallback; }
}
function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}
function appendAudit(event) {
  fs.mkdirSync(path.dirname(AUDIT), { recursive: true });
  fs.appendFileSync(AUDIT, `${JSON.stringify(event)}\n`, 'utf8');
}
function markdown(doc) {
  return `# ${doc.title}\n\nGenerated: ${doc.timestamp}\n\nPurpose: ${doc.purpose}\n\n## Go / no-go gates\n\n${doc.goNoGoGates.map((x) => `- [ ] ${x}`).join('\n')}\n\n## Pilot tasks\n\n${doc.pilotTasks.map((x) => `- [ ] ${x}`).join('\n')}\n\n## Evidence to show Lee\n\n${doc.evidence.map((x) => `- ${x}`).join('\n')}\n\n## Hard boundaries\n\n${doc.boundaries.map((x) => `- ${x}`).join('\n')}\n`;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const roi = readJson('state/self_funding_roi_calculator.json', {});
  const runbook = readJson('state/self_funding_buyer_runbook.json', {});
  const sample = readJson('state/self_funding_sample_workflow_demo.json', {});
  const privacy = readJson('state/desktop_wrapper_self_funding_demo_privacy_verifier_status.json', {});
  const doc = {
    timestamp,
    status: 'ready',
    title: 'Self-Funding Pilot Checklist',
    purpose: 'A local-only checklist for deciding whether the standard-setup pilot is ready for Lee review, without outreach, publishing, payment, paid APIs, or real buyer data.',
    selectedPilot: runbook.selectedPilot ?? roi.bestScenarioId ?? 'standard-setup',
    priceHypothesisAud: runbook.selectedPilotPriceAud ?? 450,
    quotaTargetAud: roi.targetMonthlyQuotaBudgetAud ?? 100,
    readiness: {
      roiReady: roi.status === 'ready',
      runbookReady: runbook.status === 'ready',
      sampleWorkflowReady: sample.status === 'ready',
      privacyPassed: privacy.status === 'passed' && privacy.totalFindings === 0,
    },
    goNoGoGates: [
      'Lee approves any external outreach/posting/payment before it happens.',
      'Demo assets pass privacy verifier with zero findings.',
      'Pilot scope remains one local dashboard/status snapshot plus one dry-run automation workflow.',
      'Forbidden actions are explicit: no external send, delete, payment, mic/camera, paid API, persistent process, or physical control.',
      'Quota reserve remains at least 10% weekly for Lee direct use.',
    ],
    pilotTasks: [
      'Use generated Weekly Admin Digest sample as the first dry-run workflow.',
      'Prepare a 3-minute local walkthrough order: offer -> demo pack -> sample workflow -> privacy scan -> ROI.',
      'Collect Lee feedback on whether AUD $450 standard setup is plausible before any public-facing action.',
      'If approved later, create a sanitized outreach draft separately; do not send automatically.',
    ],
    evidence: [
      'ROI calculator selects standard-setup as best current self-funding route.',
      'Buyer runbook defines qualification and delivery steps.',
      'Sample workflow uses generated data only.',
      `Privacy verifier status: ${privacy.status ?? 'unknown'}, findings=${privacy.totalFindings ?? 'unknown'}.`,
    ],
    boundaries: [
      'Local checklist only; not sent to anyone.',
      'No public posting, outreach, client claims, payment, subscription change, or paid API without Lee approval.',
      'No real client data until Lee explicitly approves a safe intake path.',
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
  writeJson(JSON_OUT, doc);
  fs.writeFileSync(MD_OUT, markdown(doc), 'utf8');
  const status = { ...doc, jsonPath: path.relative(WORKSPACE, JSON_OUT), markdownPath: path.relative(WORKSPACE, MD_OUT), auditPath: path.relative(WORKSPACE, AUDIT) };
  writeJson(OUT, status);
  appendAudit({ timestamp, status: doc.status, selectedPilot: doc.selectedPilot, privacyPassed: doc.readiness.privacyPassed });
  console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, selectedPilot: doc.selectedPilot, gateCount: doc.goNoGoGates.length, taskCount: doc.pilotTasks.length, privacyPassed: doc.readiness.privacyPassed, localDraftOnly: true, startsMicrophone: false, startsCamera: false, startsGpuWork: false, dependencyInstall: false, externalNetworkWrites: false, sendsMessages: false, publicPosting: false, financialCommitment: false, paidApi: false, persistentProcessStarted: false }, null, 2));
}

main();
