import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_self_funding_offer_draft_status.json');
const OFFER_JSON = path.join(STATE, 'self_funding_automation_service_offer.json');
const OFFER_MD = path.join(STATE, 'self_funding_automation_service_offer.md');
const OFFER_HTML = path.join(STATE, 'self_funding_automation_service_offer.html');
const AUDIT = path.join(STATE, 'desktop_wrapper_self_funding_offer_draft_audit.jsonl');

function readJson(rel, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(path.join(WORKSPACE, rel), 'utf8')); }
  catch (error) { return { ...fallback, _error: `${error.name}: ${error.message}` }; }
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
function markdown(offer) {
  return `# ${offer.title}\n\n${offer.subtitle}\n\n## Who this helps\n\n${offer.audience.map((x) => `- ${x}`).join('\n')}\n\n## Package\n\n${offer.package.map((x) => `- **${x.name}:** ${x.description}`).join('\n')}\n\n## Proof points from current demo\n\n${offer.proofPoints.map((x) => `- ${x}`).join('\n')}\n\n## Starter scope\n\n${offer.starterScope.map((x) => `- ${x}`).join('\n')}\n\n## Pricing hypotheses, not offers yet\n\n${offer.pricingHypotheses.map((x) => `- ${x}`).join('\n')}\n\n## Approval boundary\n\nThis is a local draft only. No external posting, outreach, client claim, payment, or paid API action happens without Lee's explicit approval.\n`;
}
function html(offer) {
  const list = (items) => `<ul>${items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`;
  const pkg = `<ul>${offer.package.map((x) => `<li><strong>${esc(x.name)}:</strong> ${esc(x.description)}</li>`).join('')}</ul>`;
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(offer.title)}</title><style>body{font-family:Inter,Segoe UI,Arial,sans-serif;max-width:880px;margin:32px auto;padding:0 20px;line-height:1.55;color:#202124}section{border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin:16px 0;background:#fff}.badge{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:999px;padding:4px 10px;font-size:13px}.guard{background:#fff7ed;border-color:#fed7aa}</style></head><body><span class="badge">Local draft · not published</span><h1>${esc(offer.title)}</h1><p>${esc(offer.subtitle)}</p><section><h2>Who this helps</h2>${list(offer.audience)}</section><section><h2>Package</h2>${pkg}</section><section><h2>Proof points</h2>${list(offer.proofPoints)}</section><section><h2>Starter scope</h2>${list(offer.starterScope)}</section><section><h2>Pricing hypotheses</h2>${list(offer.pricingHypotheses)}</section><section class="guard"><h2>Approval boundary</h2><p>No external posting, outreach, client claim, payment, or paid API action happens without Lee's explicit approval.</p></section></body></html>\n`;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const ledger = readJson('state/self_funding_value_ledger.json', {});
  const quota = readJson('state/codex_usage_governor_status.json', {});
  const matrix = readJson('state/desktop_wrapper_test_matrix_status.json', {});
  const offer = {
    timestamp,
    status: 'draft-ready',
    title: 'Local AI Automation & Resilience Pack',
    subtitle: 'A small, auditable local-first setup for people who want AI help without losing control of privacy, resources, or recovery paths.',
    audience: [
      'Solo operators or students who need repeatable document/research/workflow automation.',
      'Small teams who want a local dashboard for AI assistant health, quotas, resources, and audit logs.',
      'Developers who need guarded automation around sensitive actions such as camera, microphone, persistent processes, and external sends.',
    ],
    package: [
      { name: 'Local control plane', description: 'Desktop dashboard, pause/resume, service health, watchdog, and status cards.' },
      { name: 'Resource and quota guard', description: 'VRAM/RAM/disk checks plus quota reserve policy before heavy work.' },
      { name: 'Safe automation wrappers', description: 'Dry-run first, audit logs, clearance tickets, and explicit external-action guards.' },
      { name: 'Workflow demo', description: 'One concrete automation such as document cleanup, research digest, or local app health report.' },
    ],
    proofPoints: [
      `Current regression matrix: ${matrix.passedCount ?? '?'} / ${matrix.totalCount ?? '?'} passed.`,
      `Current value ledger: ${ledger.entryCount ?? 0} entries, ${ledger.totalEstimatedHours ?? 0} estimated hours tracked.`,
      `Quota policy: keep ${quota.weeklyReserveFloorPercent ?? 10}% weekly quota reserved for Lee; current week left ${quota.weeklyLeftPercent ?? 'unknown'}%.`,
      'No public posting, external outreach, payments, paid APIs, microphone/camera activation, or physical actuation in this draft.',
    ],
    starterScope: [
      '30-minute discovery and local readiness check.',
      'Install or adapt a local dashboard/status snapshot.',
      'Define 1-2 guarded automation workflows.',
      'Deliver a short runbook: how to pause, verify, restore, and audit.',
    ],
    pricingHypotheses: [
      'Tiny setup: AUD $99-199 for a constrained local demo.',
      'Standard setup: AUD $300-600 for dashboard + one workflow + runbook.',
      'Monthly maintenance: AUD $30-100 if there is ongoing monitoring/support value.',
    ],
    approvalBoundary: {
      localDraftOnly: true,
      externalPostingRequiresLeeApproval: true,
      outreachRequiresLeeApproval: true,
      paymentOrSubscriptionRequiresLeeApproval: true,
      paidApiRequiresLeeApproval: true,
    },
  };
  writeJson(OFFER_JSON, offer);
  fs.writeFileSync(OFFER_MD, markdown(offer), 'utf8');
  fs.writeFileSync(OFFER_HTML, html(offer), 'utf8');
  const status = {
    timestamp,
    status: 'ready',
    mode: 'self-funding-offer-draft-local-only',
    offerTitle: offer.title,
    markdownPath: path.relative(WORKSPACE, OFFER_MD),
    htmlPath: path.relative(WORKSPACE, OFFER_HTML),
    jsonPath: path.relative(WORKSPACE, OFFER_JSON),
    pricingHypothesisCount: offer.pricingHypotheses.length,
    proofPointCount: offer.proofPoints.length,
    externalActions: {
      sendsMessages: false,
      publicPosting: false,
      financialCommitment: false,
      paidApi: false,
    },
    safety: {
      readOnly: false,
      localDraftOnly: true,
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
  writeJson(OUT, { ...status, auditPath: path.relative(WORKSPACE, AUDIT) });
  appendAudit({ timestamp, status: status.status, offerTitle: offer.title, localDraftOnly: true });
  console.log(JSON.stringify({
    ok: true,
    out: OUT,
    status: status.status,
    offerTitle: status.offerTitle,
    pricingHypothesisCount: status.pricingHypothesisCount,
    proofPointCount: status.proofPointCount,
    sendsMessages: false,
    publicPosting: false,
    financialCommitment: false,
    startsMicrophone: false,
    startsCamera: false,
    startsGpuWork: false,
    dependencyInstall: false,
    externalNetworkWrites: false,
    paidApi: false,
    persistentProcessStarted: false,
  }, null, 2));
}

main();
