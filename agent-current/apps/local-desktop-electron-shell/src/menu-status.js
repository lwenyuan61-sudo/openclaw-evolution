import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHELL_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(SHELL_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const OUT = path.join(STATE, 'desktop_electron_menu_status.json');

const menuItems = [
  { id: 'reload-dashboard', label: 'Reload Dashboard', safeByDefault: true, mutatesState: false },
  { id: 'open-dashboard-file', label: 'Open Dashboard File', safeByDefault: true, mutatesState: false },
  { id: 'open-status-json', label: 'Open Status JSON', safeByDefault: true, mutatesState: false },
  { id: 'open-state-folder', label: 'Open State Folder', safeByDefault: true, mutatesState: false },
  { id: 'pause-all', label: 'Pause All', safeByDefault: true, mutatesState: true, mutationScope: 'state/app_control_state.json pauseAll=true only' },
  { id: 'resume-all', label: 'Resume All', safeByDefault: true, mutatesState: true, mutationScope: 'state/app_control_state.json pauseAll=false only' },
  { id: 'quit', label: 'Quit', safeByDefault: true, mutatesState: false },
];

const doc = {
  timestamp: new Date().toISOString(),
  status: 'ready',
  mode: 'electron-menu-contract',
  topLevelMenus: ['Local Evolution Agent'],
  menuItemCount: menuItems.length,
  menuItems,
  wiredInMainProcess: true,
  safety: {
    menuOnly: true,
    mutatesState: true,
    mutationScope: 'pause/resume menu items mutate only state/app_control_state.json pauseAll',
    persistentProcessStarted: false,
    externalNetworkWrites: false,
    microphone: false,
    camera: false,
    realPhysicalActuation: false,
  },
};

fs.mkdirSync(STATE, { recursive: true });
fs.writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({ ok: true, out: OUT, status: doc.status, menuItemCount: doc.menuItemCount }, null, 2));
