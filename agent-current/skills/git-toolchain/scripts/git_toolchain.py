#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, time
from datetime import datetime, timezone
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from pathlib import Path
from typing import Any

def now_iso(): return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
def run(cmd:list[str], timeout:int=30)->dict[str,Any]:
    start=time.time()
    try:
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if sys.platform.startswith('win') else 0
        p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,creationflags=flags)
        return {'ok':p.returncode==0,'returncode':p.returncode,'durationMs':round((time.time()-start)*1000),'stdout':p.stdout,'stderr':p.stderr}
    except Exception as e:
        return {'ok':False,'returncode':None,'durationMs':round((time.time()-start)*1000),'stdout':'','stderr':repr(e)}
def write_json(path,data):
    if path:
        p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def probe(args):
    git=shutil.which('git')
    version=run([git,'--version']) if git else {'ok':False,'stderr':'git not found'}
    root=run([git,'rev-parse','--show-toplevel']) if git else {'ok':False,'stderr':'git not found'}
    payload={'timestamp':now_iso(),'gitExecutable':git,'version':version,'repoRoot':(root.get('stdout') or '').strip() if root.get('ok') else None,'policy':{'readOnlyByDefault':True,'destructiveResetCleanRequireApproval':True,'pushRequiresApproval':True,'commitRequiresExplicitInstruction':True}}
    write_json(args.write_json,payload); print(json.dumps(payload,ensure_ascii=False,indent=2)); return 0 if git else 1
def status(args):
    porcelain=run(['git','status','--porcelain=v1'],timeout=args.timeout)
    branch=run(['git','branch','--show-current'],timeout=args.timeout)
    files=[]
    if porcelain.get('ok'):
        for line in porcelain.get('stdout','').splitlines():
            if not line: continue
            files.append({'code':line[:2],'path':line[3:] if len(line)>3 else line})
    payload={'timestamp':now_iso(),'ok':porcelain.get('ok',False),'branch':(branch.get('stdout') or '').strip(),'changedCount':len(files),'files':files,'raw':porcelain}
    write_json(args.write_json,payload); print(json.dumps(payload,ensure_ascii=False,indent=2)); return 0 if payload['ok'] else 1
def diff_summary(args):
    stat=run(['git','diff','--stat'],timeout=args.timeout)
    names=run(['git','diff','--name-only'],timeout=args.timeout)
    diff=run(['git','diff','--',':!*.zip',':!*.docx',':!*.xlsx'],timeout=args.timeout)
    text=diff.get('stdout','')
    truncated=len(text)>args.max_chars
    payload={'timestamp':now_iso(),'ok':diff.get('ok',False),'stat':stat.get('stdout',''),'names':[x for x in names.get('stdout','').splitlines() if x],'diffPreview':text[:args.max_chars],'truncated':truncated,'policy':'review only; no commit/reset/clean/push'}
    write_json(args.write_json,payload); print(json.dumps(payload,ensure_ascii=False,indent=2)); return 0 if payload['ok'] else 1
def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('probe'); p.add_argument('--write-json'); p.set_defaults(func=probe)
    p=sub.add_parser('status'); p.add_argument('--write-json'); p.add_argument('--timeout',type=int,default=30); p.set_defaults(func=status)
    p=sub.add_parser('diff-summary'); p.add_argument('--write-json'); p.add_argument('--timeout',type=int,default=30); p.add_argument('--max-chars',type=int,default=12000); p.set_defaults(func=diff_summary)
    args=ap.parse_args(); raise SystemExit(args.func(args))
if __name__=='__main__': main()
