import pathlib
root=pathlib.Path(r'C:\\Users\\15305\\.openclaw\\workspace\\brainflow')
patterns=['subprocess.run','Popen(','CreateProcess','openclaw oracle','oracle run','--prompt','--message','--text']
files=[p for p in root.rglob('*') if p.is_file() and p.suffix in ('.py','.yaml') and any(part in p.parts for part in ('core','plugins','workflows'))]
for pat in patterns:
    for p in files:
        try:
            txt=p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        if pat in txt:
            for i,line in enumerate(txt.splitlines(),1):
                if pat in line:
                    print(f'{p}:{i}:{line.strip()}')
                    break
            raise SystemExit(0)
print('NO_MATCH')
