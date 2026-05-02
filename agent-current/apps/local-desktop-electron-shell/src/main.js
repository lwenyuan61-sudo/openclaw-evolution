import { app, BrowserWindow, shell, Menu, Tray } from 'electron';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setPauseAll } from './menu-actions.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WORKSPACE = path.resolve(__dirname, '..', '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const DASHBOARD = path.join(STATE, 'app_shell_dashboard.html');
const STATUS_JSON = path.join(STATE, 'app_shell_status.json');
const CONTROL_STATE = path.join(STATE, 'app_control_state.json');
const RESOURCE_STATE = path.join(WORKSPACE, 'core', 'resource-state.json');
const ICON_OK = path.join(__dirname, '..', 'assets', 'tray-ok.png');
const ICON_PAUSED = path.join(__dirname, '..', 'assets', 'tray-paused.png');
const ICON_ALERT = path.join(__dirname, '..', 'assets', 'tray-alert.png');
const SMOKE_OUT = process.env.LOCAL_AGENT_ELECTRON_SMOKE_OUT || null;
let tray = null;

const MENU_CONTRACT = [
  { id: 'reload-dashboard', label: 'Reload Dashboard', safeByDefault: true, mutatesState: false },
  { id: 'open-dashboard-file', label: 'Open Dashboard File', safeByDefault: true, mutatesState: false },
  { id: 'open-status-json', label: 'Open Status JSON', safeByDefault: true, mutatesState: false },
  { id: 'open-state-folder', label: 'Open State Folder', safeByDefault: true, mutatesState: false },
  { id: 'pause-all', label: 'Pause All', safeByDefault: true, mutatesState: true, mutationScope: 'state/app_control_state.json pauseAll=true only' },
  { id: 'resume-all', label: 'Resume All', safeByDefault: true, mutatesState: true, mutationScope: 'state/app_control_state.json pauseAll=false only' },
  { id: 'quit', label: 'Quit', safeByDefault: true, mutatesState: false },
];

const TRAY_CONTRACT = [
  { id: 'show-dashboard', label: 'Show Dashboard', safeByDefault: true, mutatesState: false },
  { id: 'reload-dashboard', label: 'Reload Dashboard', safeByDefault: true, mutatesState: false },
  { id: 'pause-all', label: 'Pause All', safeByDefault: true, mutatesState: true, mutationScope: 'state/app_control_state.json pauseAll=true only' },
  { id: 'resume-all', label: 'Resume All', safeByDefault: true, mutatesState: true, mutationScope: 'state/app_control_state.json pauseAll=false only' },
  { id: 'open-state-folder', label: 'Open State Folder', safeByDefault: true, mutatesState: false },
  { id: 'quit', label: 'Quit', safeByDefault: true, mutatesState: false },
];

function readJson(file, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch { return fallback; }
}

function trayIconForState() {
  const control = readJson(CONTROL_STATE, {});
  const resource = readJson(RESOURCE_STATE, {});
  if (control.pauseAll) return ICON_PAUSED;
  if (['warning', 'critical'].includes(resource.resourcePressure?.level)) return ICON_ALERT;
  return ICON_OK;
}

function writeSmokeStatus(status, extra = {}) {
  if (!SMOKE_OUT) return;
  const doc = {
    timestamp: new Date().toISOString(),
    status,
    dashboard: DASHBOARD,
    persistentProcessStarted: false,
    ...extra,
  };
  fs.mkdirSync(path.dirname(SMOKE_OUT), { recursive: true });
  fs.writeFileSync(SMOKE_OUT, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

function createLocal Evolution AgentMenu(win) {
  const template = [
    {
      label: 'Local Evolution Agent',
      submenu: [
        { label: 'Reload Dashboard', click: () => win.loadFile(DASHBOARD) },
        { label: 'Open Dashboard File', click: () => shell.openPath(DASHBOARD) },
        { label: 'Open Status JSON', click: () => shell.openPath(STATUS_JSON) },
        { label: 'Open State Folder', click: () => shell.openPath(STATE) },
        { type: 'separator' },
        { label: 'Pause All', click: () => setPauseAll({ workspace: WORKSPACE, pauseAll: true }) },
        { label: 'Resume All', click: () => setPauseAll({ workspace: WORKSPACE, pauseAll: false }) },
        { type: 'separator' },
        { label: 'Quit', role: 'quit' },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
  return template;
}

function createTray(win) {
  tray = new Tray(trayIconForState());
  tray.setToolTip('the agent Desktop Companion');
  const rebuild = () => {
    const control = readJson(CONTROL_STATE, {});
    const resource = readJson(RESOURCE_STATE, {});
    tray.setImage(trayIconForState());
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: `Local Evolution Agent · ${resource.resourcePressure?.level ?? 'unknown'}${control.pauseAll ? ' · paused' : ''}`, enabled: false },
      { type: 'separator' },
      { label: 'Show Dashboard', click: () => { win.show(); win.focus(); } },
      { label: 'Reload Dashboard', click: () => win.loadFile(DASHBOARD) },
      { type: 'separator' },
      { label: 'Pause All', click: () => { setPauseAll({ workspace: WORKSPACE, pauseAll: true, source: 'electron-tray' }); rebuild(); } },
      { label: 'Resume All', click: () => { setPauseAll({ workspace: WORKSPACE, pauseAll: false, source: 'electron-tray' }); rebuild(); } },
      { type: 'separator' },
      { label: 'Open State Folder', click: () => shell.openPath(STATE) },
      { label: 'Quit', role: 'quit' },
    ]));
  };
  tray.on('click', () => { win.isVisible() ? win.hide() : (win.show(), win.focus()); });
  rebuild();
  return { tray, itemCount: TRAY_CONTRACT.length, contract: TRAY_CONTRACT };
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1180,
    height: 820,
    title: 'the agent Desktop Companion',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  const menuTemplate = createLocal Evolution AgentMenu(win);
  const trayStatus = createTray(win);

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  win.webContents.once('did-finish-load', () => {
    writeSmokeStatus('loaded', {
      title: win.getTitle(),
      url: win.webContents.getURL(),
      fileExists: fs.existsSync(DASHBOARD),
      menuTopLevelCount: menuTemplate.length,
      menuItemCount: MENU_CONTRACT.length,
      menuItems: MENU_CONTRACT,
      trayItemCount: trayStatus.itemCount,
      trayItems: trayStatus.contract,
    });
    if (SMOKE_OUT && process.env.LOCAL_AGENT_ELECTRON_PERSISTENT_SMOKE !== '1') setTimeout(() => app.quit(), 300);
  });

  win.webContents.once('did-fail-load', (_event, errorCode, errorDescription, validatedURL) => {
    writeSmokeStatus('failed-load', { errorCode, errorDescription, validatedURL });
    if (SMOKE_OUT && process.env.LOCAL_AGENT_ELECTRON_PERSISTENT_SMOKE !== '1') setTimeout(() => app.quit(), 300);
  });

  win.loadFile(DASHBOARD);
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
