import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readJson, setPauseAll, writeJson } from './menu-actions.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHELL_ROOT = path.resolve(__dirname, '..');
const WORKSPACE = path.resolve(SHELL_ROOT, '..', '..');
const STATE = path.join(WORKSPACE, 'state');
const APP_CONTROL = path.join(STATE, 'app_control_state.json');
const OUT = path.join(STATE, 'desktop_electron_menu_action_test_status.json');

function main() {
  const started = new Date().toISOString();
  const before = readJson(APP_CONTROL, {});
  const originalPauseAll = Boolean(before.pauseAll);
  const pause = setPauseAll({ workspace: WORKSPACE, pauseAll: true, source: 'electron-menu-action-test' });
  const afterPause = readJson(APP_CONTROL, {});
  const resume = setPauseAll({ workspace: WORKSPACE, pauseAll: false, source: 'electron-menu-action-test' });
  const afterResume = readJson(APP_CONTROL, {});
  if (originalPauseAll !== false) {
    setPauseAll({ workspace: WORKSPACE, pauseAll: originalPauseAll, source: 'electron-menu-action-test-restore-original' });
  }
  const finalState = readJson(APP_CONTROL, {});
  const passed = afterPause.pauseAll === true && afterResume.pauseAll === false && finalState.pauseAll === originalPauseAll;
  const doc = {
    timestamp: new Date().toISOString(),
    started,
    status: passed ? 'passed' : 'failed',
    mode: 'electron-menu-pause-resume-action-test',
    originalPauseAll,
    afterPauseAll: afterPause.pauseAll,
    afterResumeAll: afterResume.pauseAll,
    finalPauseAll: finalState.pauseAll,
    auditPath: pause.auditPath,
    mutations: [pause.audit, resume.audit],
    safety: {
      reversible: true,
      mutationScope: 'state/app_control_state.json pauseAll only',
      persistentProcessStarted: false,
      externalNetworkWrites: false,
      microphone: false,
      camera: false,
      realPhysicalActuation: false,
    },
  };
  fs.mkdirSync(STATE, { recursive: true });
  writeJson(OUT, doc);
  console.log(JSON.stringify({ ok: passed, out: OUT, status: doc.status, finalPauseAll: doc.finalPauseAll }, null, 2));
}

main();
