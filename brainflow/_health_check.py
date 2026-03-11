import json
from plugins.health_monitor.plugin import run
s = json.dumps(run(), ensure_ascii=False, indent=2)
import sys
sys.stdout.buffer.write(s.encode('utf-8', 'replace'))
sys.stdout.buffer.write(b"\n")
