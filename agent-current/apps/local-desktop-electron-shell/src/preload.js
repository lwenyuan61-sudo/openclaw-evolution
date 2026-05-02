const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('local-evolution-agentShell', {
  mode: 'local-file-dashboard-shell',
  persistentProcessStartedByScaffold: false,
  approvalSource: 'Lee broad approval 2026-05-01 10:35 AEST',
});
