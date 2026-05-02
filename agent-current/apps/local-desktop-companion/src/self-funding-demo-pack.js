import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_self_funding_demo_pack_status.json');
const PACK_JSON = path.join(STATE, 'self_funding_demo_pack.json');
const PACK_MD = path.join(STATE, 'self_funding_demo_pack.md');
const PACK_HTML = path.join(STATE, 'self_funding_demo_pack.html');
const AUDIT = path.join(STATE, 'desktop_wrapper_self_funding_demo_pack_audit.jsonl');

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
function sanitizeCard(card) {
  const summary = String(card?.summary ?? '')
    .replace(/[A-Z]:\\[^ ·\n]+/g, '[local-path]')
    .replace(/\b\d{8,}@[\w.-]+\b/g, '[account]')
    .replace(/\+\d{8,15}/g, '[phone]');
  return { id: card?.id ?? 'unknown', title: card?.title ?? card?.id ?? 'Untitled', level: card?.level ?? 'unknown', summary };
}
function markdown(pack) {
  const cards = pack.demoCards.map((card) => `- **${card.title}** (${card.level}): ${card.summary}`).join('\n');
  const assets = pack.assets.map((asset) => `- ${asset}`).join('\n');
  return `# ${pack.title}\n\nGenerated: ${pack.timestamp}\n\nPurpose: ${pack.purpose}\n\n## Demo story\n\n${pack.demoStory.map((x) => `- ${x}`).join('\n')}\n\n## Sanitized status cards\n\n${cards}\n\n## Local assets\n\n${assets}\n\n## Boundaries\n\n- Local draft only\n- No external posting/outreach\n- No client claims\n- No payments or paid APIs\n- No microphone/camera activation\n`;
}
function html(pack) {
  const cards = pack.demoCards.map((card) => `<li><strong>${esc(card.title)}</strong> <span>(${esc(card.level)})</span><br>${esc(card.summary)}</li>`).join('');
  const story = pack.demoStory.map((x) => `<li>${esc(x)}</li>`).join('');
  const assets = pack.assets.map((x) => `<li>${esc(x)}</li>`).join('');
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(pack.title)}</title><style>body{font-family:Inter,Segoe UI,Arial,sans-serif;max-width:920px;margin:32px auto;padding:0 20px;line-height:1.55;color:#1f2937}.badge{display:inline-block;border-radius:999px;background:#ecfeff;color:#155e75;padding:4px 10px;font-size:13px}section{border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin:16px 0}li{margin:8px 0}.guard{background:#f8fafc}</style></head><body><span class="badge">Sanitized local demo pack · not published</span><h1>${esc(pack.title)}</h1><p>${esc(pack.purpose)}</p><section><h2>Demo story</h2><ul>${story}</ul></section><section><h2>Status cards</h2><ul>${cards}</ul></section><section><h2>Assets</h2><ul>${assets}</ul></section><section class="guard"><h2>Boundaries</h2><p>Local draft only. No external posting, outreach, client claims, payments, paid APIs, microphone/camera activation, or physical actuation.</p></section></body></html>\n`;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const app = readJson('state/app_shell_status.json', { cards: [] });
  const offer = readJson('state/self_funding_automation_service_offer.json', {});
  const ledger = readJson('state/self_funding_value_ledger.json', {});
  const quota = readJson('state/codex_usage_governor_status.json', {});
  const wanted = new Set([
    'resource',
    'resource-action-ticket',
    'external-action-guard',
    'quiet-hours-action-gate',
    'self-funding-value-ledger',
    'self-funding-offer-draft',
    'service-health',
    'resident',
    'test-matrix',
  ]);
  const cards = (app.cards ?? []).filter((card) => wanted.has(card.id)).map(sanitizeCard).slice(0, 10);
  const pack = {
    timestamp,
    status: 'ready',
    title: 'Local Evolution Agent Local AI Automation Demo Pack',
    purpose: 'A sanitized local proof pack that explains the automation/resilience offer without leaking Lee private paths, accounts, phone numbers, raw media, or internal secrets.',
    offerTitle: offer.title ?? 'Local AI Automation & Resilience Pack',
    demoStory: [
      'Shows a local-first assistant control plane rather than a cloud-only chatbot.',
      'Demonstrates quota reserve discipline: keep 10% weekly quota for Lee while tracking value created.',
      'Demonstrates resource safety: VRAM/RAM/disk gate before sensitive or heavy work.',
      'Demonstrates external-action boundaries: no public posting, paid APIs, client outreach, or messages without approval.',
      'Demonstrates product value: dashboard, audit trail, safe queues, and runbook-friendly state files.',
    ],
    demoCards: cards,
    metrics: {
      valueLedgerEntries: ledger.entryCount ?? 0,
      estimatedHoursTracked: ledger.totalEstimatedHours ?? 0,
      weeklyQuotaLeftPercent: quota.weeklyLeftPercent ?? null,
      quotaReserveFloorPercent: quota.weeklyReserveFloorPercent ?? 10,
      appShellStatus: app.status ?? 'unknown',
    },
    assets: [
      'state/self_funding_automation_service_offer.md',
      'state/self_funding_automation_service_offer.html',
      'state/self_funding_value_ledger.md',
      'state/app_shell_dashboard.html',
      'state/self_funding_demo_pack.md',
      'state/self_funding_demo_pack.html',
    ],
    privacyReview: {
      rawAudioIncluded: false,
      rawImagesIncluded: false,
      phoneNumbersIncluded: false,
      accountEmailsIncluded: false,
      absolutePrivatePathsIncluded: false,
      publicPosting: false,
    },
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
  writeJson(PACK_JSON, pack);
  fs.writeFileSync(PACK_MD, markdown(pack), 'utf8');
  fs.writeFileSync(PACK_HTML, html(pack), 'utf8');
  const status = { ...pack, jsonPath: path.relative(WORKSPACE, PACK_JSON), markdownPath: path.relative(WORKSPACE, PACK_MD), htmlPath: path.relative(WORKSPACE, PACK_HTML), auditPath: path.relative(WORKSPACE, AUDIT) };
  writeJson(OUT, status);
  appendAudit({ timestamp, status: status.status, cardCount: cards.length, localDraftOnly: true });
  console.log(JSON.stringify({
    ok: true,
    out: OUT,
    status: status.status,
    cardCount: cards.length,
    assetCount: pack.assets.length,
    valueLedgerEntries: pack.metrics.valueLedgerEntries,
    weeklyQuotaLeftPercent: pack.metrics.weeklyQuotaLeftPercent,
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
