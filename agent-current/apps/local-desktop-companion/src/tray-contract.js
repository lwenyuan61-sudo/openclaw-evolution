import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(APP_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_wrapper_tray_contract_status.json');
const PLAN = path.join(STATE, 'native_tray_packaging_plan.json');

const CONTRACT = {
  timestamp: new Date().toISOString(),
  status: 'ready-for-packaging-design',
  mode: 'native-tray-contract-no-install',
  purpose: 'Define the first native tray surface before installing any tray app or adding new dependencies.',
  trayItems: [
    {
      id: 'open-dashboard',
      label: 'Open Local Evolution Agent Dashboard',
      action: 'open local dashboard or wrapper URL',
      safeByDefault: true,
      mutatesState: false,
    },
    {
      id: 'show-status',
      label: 'Show Status',
      action: 'read state/app_shell_status.json and wrapper status',
      safeByDefault: true,
      mutatesState: false,
    },
    {
      id: 'pause-all',
      label: 'Pause All',
      action: 'execute wrapper pause-all control; reversible',
      safeByDefault: true,
      mutatesState: true,
      mutationScope: 'state/app_control_state.json pauseAll=true only',
    },
    {
      id: 'resume-all',
      label: 'Resume All',
      action: 'execute wrapper resume-all control; reversible',
      safeByDefault: true,
      mutatesState: true,
      mutationScope: 'state/app_control_state.json pauseAll=false only',
    },
    {
      id: 'diagnostics-export',
      label: 'Export Diagnostics',
      action: 'run local redacted diagnostics export',
      safeByDefault: true,
      mutatesState: true,
      mutationScope: 'state/diagnostics_export/latest.json and diagnostics summary only',
    },
    {
      id: 'voice-calibration-preview',
      label: 'Voice Calibration Preview',
      action: 'preview manual voice calibration; no recording',
      safeByDefault: true,
      mutatesState: true,
      mutationScope: 'voice calibration ledger/indicator preview only',
    },
    {
      id: 'voice-calibration-record',
      label: 'Record 3s Calibration',
      action: 'blocked until explicit token / user click flow',
      safeByDefault: false,
      requiresConfirmation: true,
      startsMicrophone: true,
    },
    {
      id: 'real-physical-action',
      label: 'Real Physical Action',
      action: 'blocked; simulator/allowlist only until per-device approvals',
      safeByDefault: false,
      requiresConfirmation: true,
      startsPhysicalActuation: true,
    }
  ],
  packagingCandidates: [
    {
      id: 'tauri',
      recommendation: 'best-next-native-shell',
      why: 'Small footprint and good fit for local UI + Rust sidecar later; requires dependency install and project scaffold later.',
      currentAction: 'plan only; no install',
    },
    {
      id: 'electron',
      recommendation: 'fallback-fastest-web-wrapper',
      why: 'Fast to wrap existing dashboard, heavier runtime footprint.',
      currentAction: 'plan only; no install',
    },
    {
      id: 'native-windows-tray',
      recommendation: 'minimal-utility-option',
      why: 'Could expose tray/status without full app shell, but richer UI is harder.',
      currentAction: 'plan only; no install',
    }
  ],
  verificationGates: [
    'No dependency install during planning step',
    'No persistent tray process started',
    'Pause/resume remain reversible and scoped to app_control_state.pauseAll',
    'Voice recording remains confirmation-gated',
    'Real physical actuation remains simulator/allowlist-gated',
    'Diagnostics export stays local and redacted'
  ],
  safety: {
    externalNetworkWrites: false,
    persistentInstall: false,
    dependencyInstall: false,
    microphone: false,
    camera: false,
    realPhysicalActuation: false,
  }
};

function main() {
  fs.mkdirSync(STATE, { recursive: true });
  fs.writeFileSync(OUT, `${JSON.stringify(CONTRACT, null, 2)}\n`, 'utf8');
  fs.writeFileSync(PLAN, `${JSON.stringify(CONTRACT, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ ok: true, out: OUT, plan: PLAN, trayItemCount: CONTRACT.trayItems.length, status: CONTRACT.status }, null, 2));
}

main();
