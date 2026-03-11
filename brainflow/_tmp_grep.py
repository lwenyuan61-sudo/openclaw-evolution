import os,re
roots=['core','plugins','workflows']
pat=re.compile(r"parse failed|codefence|```|jsonschema|schema|JSON",re.I)
for root in roots:
  for dp,_,fs in os.walk(root):
    for f in fs:
      if not any(f.endswith(ext) for ext in ['.py','.md','.json','.yaml','.yml']):
        continue
      p=os.path.join(dp,f)
      try:
        with open(p,'r',encoding='utf-8',errors='ignore') as fh:
          for i,line in enumerate(fh,1):
            if pat.search(line):
              print(f"{p}:{i}:{line.rstrip()}" )
      except Exception:
        pass
