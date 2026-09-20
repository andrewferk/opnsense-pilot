"""THROWAWAY: print the probe's request log, one line per request, from a marker on."""

import json
import sys

path, start = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
show = start is None
for line in open(path):
    r = json.loads(line)
    if "marker" in r:
        show = show or r["marker"] == start
        if show:
            print("----", r["marker"])
        continue
    if not show:
        continue
    print(
        r["http"], r.get("status"), "pv=" + str(r["protocol_header"]),
        "rpc=" + str(r.get("rpc_method")), r.get("rpc_name") or "",
        "sess(req/resp)=%s/%s" % (r["req_session_header"], r.get("resp_session_header")),
        "auth=" + str(r["has_authorization"]), "client=" + str(r.get("client")),
        "init=" + str(r.get("initialize_requested_version", "")),
        "path=" + r["path"], "wwwauth=" + str(r.get("www_authenticate")),
    )
