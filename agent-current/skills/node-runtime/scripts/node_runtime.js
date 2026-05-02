#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const child_process = require('child_process');

function nowIso(){ return new Date().toISOString(); }
function ensureDir(p){ fs.mkdirSync(p, {recursive:true}); }
function writeJson(p, data){ if(!p) return; ensureDir(path.dirname(p)); fs.writeFileSync(p, JSON.stringify(data,null,2)+'\n', 'utf8'); }
function parseArgs(argv){
  const args = { _: [] };
  for(let i=0;i<argv.length;i++){
    const a=argv[i];
    if(a.startsWith('--')){ const k=a.slice(2); args[k]=argv[i+1] && !argv[i+1].startsWith('--') ? argv[++i] : true; }
    else args._.push(a);
  }
  return args;
}
function run(cmd, argv, timeout, cwd){
  const start = Date.now();
  try{
    const r = child_process.spawnSync(cmd, argv, {cwd: cwd || process.cwd(), encoding:'utf8', timeout: timeout*1000, windowsHide:true});
    return {ok:r.status===0, returncode:r.status, durationMs:Date.now()-start, stdout:r.stdout||'', stderr:r.stderr||'', signal:r.signal||null};
  }catch(e){ return {ok:false, returncode:null, durationMs:Date.now()-start, stdout:'', stderr:String(e)}; }
}
function probe(args){
  const modules = ['fs','path','crypto','child_process','os','http','https'];
  const payload = {
    timestamp: nowIso(),
    nodeExecutable: process.execPath,
    version: process.version,
    platform: process.platform,
    arch: process.arch,
    cwd: process.cwd(),
    heapLimitNote: 'For memory-heavy jobs, prefer NODE_OPTIONS=--max-old-space-size=8192 or smaller scoped processing.',
    modules: Object.fromEntries(modules.map(m => [m, true])),
    policy: {
      destructiveScriptsRequireApproval: true,
      longRunningNeedsTimeoutOrWatchdog: true,
      packageInstallRequiresMainPersonaJudgment: true,
      memoryHeavyJobsNeedHeapPlan: true
    }
  };
  writeJson(args['write-json'], payload);
  console.log(JSON.stringify(payload,null,2));
}
function smokeTest(args){
  const out = args['out-dir'] || 'state/node_runtime/smoke_test'; ensureDir(out);
  const data = [{item:'alpha',value:1},{item:'beta',value:2},{item:'gamma',value:3}];
  const sum = data.reduce((a,b)=>a+b.value,0);
  const payload = {timestamp:nowIso(), ok:true, json:path.join(out,'smoke_result.json'), count:data.length, sum, node:process.version};
  writeJson(payload.json, payload);
  console.log(JSON.stringify(payload,null,2));
}
function runScript(args){
  const script = args._[1];
  if(!script || !fs.existsSync(script)){
    const payload={timestamp:nowIso(), ok:false, error:`script not found: ${script||''}`}; writeJson(args['write-json'], payload); console.log(JSON.stringify(payload,null,2)); process.exit(2);
  }
  const idx = process.argv.indexOf(script);
  const pass = idx >= 0 ? process.argv.slice(idx+1).filter(x=>!String(x).startsWith('--timeout') && !String(x).startsWith('--write-json')) : [];
  const result = run(process.execPath, [script, ...pass], Number(args.timeout||120), args.cwd);
  const payload={timestamp:nowIso(), script, timeout:Number(args.timeout||120), ...result};
  writeJson(args['write-json'], payload); console.log(JSON.stringify(payload,null,2)); process.exit(result.ok?0:1);
}
const args = parseArgs(process.argv.slice(2));
const cmd = args._[0];
if(cmd === 'probe') probe(args);
else if(cmd === 'smoke-test') smokeTest(args);
else if(cmd === 'run-script') runScript(args);
else { console.error('Usage: node_runtime.js <probe|smoke-test|run-script> [options]'); process.exit(2); }
