"""One request, for targeted experiments:  one_call.py ROLE METHOD PATH [json-body] [--ctype-json] [--http2]"""
import json
import sys
import time

from probe_lib import client

args = [a for a in sys.argv[1:] if not a.startswith("--")]
role, method, path = args[:3]
kw = {}
if len(args) > 3:
    kw["json"] = json.loads(args[3])
if "--ctype-json" in sys.argv:
    kw["headers"] = {"Content-Type": "application/json"}
with client(role, http2="--http2" in sys.argv) as c:
    t = time.time()
    r = c.request(method, path, **kw)
    print(r.http_version, r.status_code, r.headers.get("content-type"), "location=" + str(r.headers.get("location")),
          "www-auth=" + str(r.headers.get("www-authenticate")), len(r.content), "bytes", f"{time.time() - t:.2f}s")
    print(r.text[:400].replace("\n", " "))
