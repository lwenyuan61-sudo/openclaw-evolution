import fs from 'node:fs';
import path from 'node:path';

export function readJson(file, fallback = {}) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch { return fallback; }
}

export function writeJson(file, doc) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(doc, null, 2)}\n`, 'utf8');
}

export function setPauseAll({ workspace, pauseAll, source = 'electron-menu' }) {
  const statePath = path.join(workspace, 'state', 'app_control_state.json');
  const auditPath = path.join(workspace, 'state', 'desktop_electron_menu_action_audit.jsonl');
  const current = readJson(statePath, {});
  const next = {
    ...current,
    timestamp: new Date().toISOString(),
    status: 'ready',
    pauseAll: Boolean(pauseAll),
    lastAction: pauseAll ? 'electron-menu-pause-all' : 'electron-menu-resume-all',
    lastChangedBy: source,
  };
  writeJson(statePath, next);
  const audit = {
    timestamp: next.timestamp,
    source,
    action: pauseAll ? 'pause-all' : 'resume-all',
    mutatesState: true,
    mutationScope: 'state/app_control_state.json pauseAll only',
    beforePauseAll: current.pauseAll ?? null,
    afterPauseAll: next.pauseAll,
  };
  fs.appendFileSync(auditPath, `${JSON.stringify(audit)}\n`, 'utf8');
  return { statePath, auditPath, audit, state: next };
}
