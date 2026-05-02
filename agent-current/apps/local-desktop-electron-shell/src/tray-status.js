import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHELL_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(SHELL_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_electron_tray_status.json');

const trayItems = [
  { id: 'show-dashboard', label: 'Show Dashboard', safeByDefault: true, mutatesState: false },
  { id: 'reload-dashboard', label: 'Reload Dashboard', safeByDefault: true, mutatesState: false },
  { id: 'pause-all', label: 'Pause All', safeByDefault: true, mutatesState: true, mutationScope: 'state/app_control_state.json pauseAll=true only' },
  { id: 'resume-all', label: 'Resume All', safeByDefault: true, mutatesState: true, mutationScope: 'state/app_control_state.json pauseAll=false only' },
  { id: 'open-state-folder', label: 'Open State Folder', safeByDefault: true, mutatesState: false },
  { id: 'quit', label: 'Quit', safeByDefault: true, mutatesState: false },
];

const icons = ['assets/tray-ok.png', 'assets/tray-paused.png', 'assets/tray-alert.png'].map((rel) => ({ rel, exists: fs.existsSync(path.join(SHELL_ROOT, rel)) }));
const doc = {
  timestamp: new Date().toISOString(),
  status: icons.every((icon) => icon.exists) ? 'ready' : 'missing-icons',
  mode: 'electron-tray-contract',
  trayItemCount: trayItems.length,
  trayItems,
  icons,
  dynamicStates: ['ok', 'paused', 'resource-warning-or-critical'],
  wiredInMainProcess: true,
  safety: {
    trayOnly: true,
    persistentProcessStarted: false,
    externalNetworkWrites: false,
    microphone: false,
    camera: false,
    realPhysicalActuation: false,
    mutableActionsScoped: 'pause/resume only mutate state/app_control_state.json pauseAll',
  },
};
fs.mkdirSync(STATE, { recursive: true });
fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({ ok: doc.status === 'ready', out: OUT, status: doc.status, trayItemCount: doc.trayItemCount }, null, 2));
