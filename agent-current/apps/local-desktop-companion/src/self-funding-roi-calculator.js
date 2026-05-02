import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_self_funding_roi_calculator_status.json');
const ROI_JSON = path.join(STATE, 'self_funding_roi_calculator.json');
const ROI_MD = path.join(STATE, 'self_funding_roi_calculator.md');
const AUDIT = path.join(STATE, 'desktop_wrapper_self_funding_roi_calculator_audit.jsonl');

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
function money(value) {
  return `AUD $${Number(value).toFixed(0)}`;
}
function markdown(doc) {
  const rows = doc.scenarios.map((s) => `- **${s.id}:** ${s.unitsNeeded} unit(s) at ${money(s.unitPriceAud)} covers ${money(s.targetMonthlyQuotaBudgetAud)} monthly target; estimated margin ${money(s.estimatedGrossMarginAud)}.`).join('\n');
  return `# Self-Funding ROI Calculator\n\nGenerated: ${doc.timestamp}\n\n## Quota state\n\n- Week left: ${doc.quota.weeklyLeftPercent ?? 'unknown'}%\n- Reserve floor: ${doc.quota.weeklyReserveFloorPercent ?? 10}%\n- Speed band: ${doc.quota.selectedSpeedBand ?? 'unknown'}\n\n## Value ledger\n\n- Entries: ${doc.value.entryCount}\n- Estimated hours tracked: ${doc.value.estimatedHoursTracked}\n\n## Scenarios\n\n${rows}\n\n## Recommendation\n\n${doc.recommendation}\n\n## Boundary\n\nLocal calculation only. No external messages, posts, client claims, payments, paid APIs, or subscription changes without Lee approval.\n`;
}

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  const timestamp = new Date().toISOString();
  const ledger = readJson('state/self_funding_value_ledger.json', {});
  const quota = readJson('state/codex_usage_governor_status.json', {});
  const offer = readJson('state/self_funding_automation_service_offer.json', {});
  const targetMonthlyQuotaBudgetAud = 100;
  const scenarios = [
    { id: 'tiny-setup', unitPriceAud: 149, estimatedDeliveryHours: 2.5 },
    { id: 'standard-setup', unitPriceAud: 450, estimatedDeliveryHours: 6 },
    { id: 'maintenance-retainer', unitPriceAud: 60, estimatedDeliveryHours: 1.2 },
  ].map((scenario) => ({
    ...scenario,
    targetMonthlyQuotaBudgetAud,
    unitsNeeded: Math.ceil(targetMonthlyQuotaBudgetAud / scenario.unitPriceAud),
    estimatedGrossMarginAud: Math.max(0, scenario.unitPriceAud - targetMonthlyQuotaBudgetAud / Math.ceil(targetMonthlyQuotaBudgetAud / scenario.unitPriceAud)),
    hourlyEquivalentAud: Number((scenario.unitPriceAud / scenario.estimatedDeliveryHours).toFixed(2)),
  }));
  const best = scenarios.slice().sort((a, b) => b.hourlyEquivalentAud - a.hourlyEquivalentAud)[0];
  const doc = {
    timestamp,
    status: 'ready',
    mode: 'self-funding-roi-calculator-local-only',
    offerTitle: offer.title ?? 'Local AI Automation & Resilience Pack',
    quota: {
      weeklyLeftPercent: quota.weeklyLeftPercent ?? null,
      weeklyReserveFloorPercent: quota.weeklyReserveFloorPercent ?? 10,
      selectedSpeedBand: quota.selectedSpeedBand ?? 'unknown',
      weeklyResetIn: quota.weeklyResetIn ?? null,
    },
    value: {
      entryCount: ledger.entryCount ?? 0,
      estimatedHoursTracked: ledger.totalEstimatedHours ?? 0,
    },
    targetMonthlyQuotaBudgetAud,
    scenarios,
    bestScenarioId: best?.id ?? null,
    recommendation: best ? `Prepare a Lee-reviewed ${best.id} pilot first; one sale can cover the current ${money(targetMonthlyQuotaBudgetAud)} monthly quota target without public outreach yet.` : 'Need more ledger data before selecting a pilot.',
    nextLocalAsset: 'buyer-runbook-and-pilot-checklist',
    externalActions: {
      sendsMessages: false,
      publicPosting: false,
      clientClaims: false,
      financialCommitment: false,
      paidApi: false,
      subscriptionChange: false,
    },
    safety: {
      localCalculationOnly: true,
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
  writeJson(ROI_JSON, doc);
  fs.writeFileSync(ROI_MD, markdown(doc), 'utf8');
  writeJson(OUT, { ...doc, jsonPath: path.relative(WORKSPACE, ROI_JSON), markdownPath: path.relative(WORKSPACE, ROI_MD), auditPath: path.relative(WORKSPACE, AUDIT) });
  appendAudit({ timestamp, status: doc.status, bestScenarioId: doc.bestScenarioId, targetMonthlyQuotaBudgetAud });
  console.log(JSON.stringify({
    ok: true,
    out: OUT,
    status: doc.status,
    targetMonthlyQuotaBudgetAud,
    scenarioCount: scenarios.length,
    bestScenarioId: doc.bestScenarioId,
    reserveFloor: doc.quota.weeklyReserveFloorPercent,
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
