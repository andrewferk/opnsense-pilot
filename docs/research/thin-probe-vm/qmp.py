#!/usr/bin/env python3
"""Send one human-monitor command to the probe VM over QMP and print the reply and elapsed time.
   qmp.py savevm warm | qmp.py loadvm warm | qmp.py info snapshots"""
import json, os, socket, sys, time

s = socket.socket(socket.AF_UNIX)
s.connect(os.path.expanduser("~/.local/share/opnsense-pilot-probe/run/qmp.sock"))
f = s.makefile("rw")
f.readline()
for cmd in ({"execute": "qmp_capabilities"},
            {"execute": "human-monitor-command", "arguments": {"command-line": " ".join(sys.argv[1:])}}):
    t = time.time()
    f.write(json.dumps(cmd) + "\n"); f.flush()
    while True:
        r = json.loads(f.readline())
        if "return" in r or "error" in r:
            break
print(r, f"{time.time() - t:.1f}s")
