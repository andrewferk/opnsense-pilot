"""Protocol edge cases: how denial, absence, bad auth, wrong verb and old path spellings look. Read-only calls only."""
import hashlib
import json
import os
import time

import httpx

from probe_lib import client, creds

HERE = os.path.dirname(os.path.abspath(__file__))
out = []


def rec(label, r=None, err=None, **extra):
    row = {"case": label, **extra}
    if r is not None:
        row.update(status=r.status_code, http=r.http_version, ctype=r.headers.get("content-type"),
                   location=r.headers.get("location"), www_authenticate=r.headers.get("www-authenticate"),
                   bytes=len(r.content), body_head=r.text[:160].replace("\n", " "))
    if err:
        row["error"] = err
    out.append(row)
    print(json.dumps(row)[:330])


S1 = "/api/diagnostics/system/system_information"
with client("none") as c:
    rec("no credentials", c.get(S1))
c0 = creds()
with httpx.Client(base_url=c0["PROBE_URL"], verify=False, auth=("bogus-key", "bogus-secret")) as c:
    rec("wrong key and secret", c.get(S1))
with httpx.Client(base_url=c0["PROBE_URL"], verify=False, auth=(c0["PROBE_READONLY_API_KEY"], "wrong-secret")) as c:
    rec("right key, wrong secret", c.get(S1))

for role in ("admin", "readonly"):
    with client(role) as c:
        rec(f"{role}: GET with Content-Type json and empty body", c.get(S1, headers={"Content-Type": "application/json"}))
        rec(f"{role}: unknown module", c.get("/api/nosuchmodule/thing/get"))
        rec(f"{role}: unknown controller", c.get("/api/firewall/nosuchcontroller/get"))
        rec(f"{role}: unknown action on real controller", c.get("/api/firewall/alias/no_such_action"))
        rec(f"{role}: absent plugin (ISC leases)", c.get("/api/dhcpv4/leases/search_lease"))
        rec(f"{role}: excluded migration read", c.get("/api/firewall/migration/count_rules"))
        rec(f"{role}: excluded migration outbound", c.get("/api/firewall/migration/count_outbound"))
        rec(f"{role}: GET on a POST-only mutator (alias add_item)", c.get("/api/firewall/alias/add_item"))
        rec(f"{role}: GET on log query path (needs POST)", c.get("/api/diagnostics/log/core/system"))
        rec(f"{role}: POST on a GET-only getter", c.post("/api/firewall/source_nat/get", json={}))
        rec(f"{role}: legacy camelCase action searchItem", c.get("/api/firewall/alias/searchItem"))
        rec(f"{role}: legacy camelCase getRoutes", c.get("/api/diagnostics/interface/getRoutes"))
        rec(f"{role}: legacy camelCase controller aliasUtil", c.get("/api/firewall/aliasUtil/aliases"))
        rec(f"{role}: gateway groups via un-snake path", c.get("/api/routing/groupsettings/search"))
        rec(f"{role}: alias_util list unknown alias", c.get("/api/firewall/alias_util/list/no_such_alias"))
        rec(f"{role}: nameservers read", c.get("/api/unbound/settings/get_nameservers"))
        rec(f"{role}: legacy rule count via filter search", c.get("/api/firewall/filter/search_rule"),
            note="see fixtures F1 for legacy markers")

# Large responses, HTTP/1.1 vs HTTP/2 (third-party claim: chunked framing breaks httpx above ~100 KB on 26.7).
big_calls = [("GET", "/api/firewall/alias/search_item", None),
             ("GET", "/api/firewall/alias/export", None),
             ("POST", "/api/diagnostics/log/core/configd", {"current": 1, "rowCount": 9999, "searchPhrase": "", "severity": "", "validFrom": "0"})]
for h2 in (False, True):
    with client("admin", http2=h2, http1=not h2) as c:
        for method, path, body in big_calls:
            sizes, hashes, errs, vers = [], set(), [], set()
            t = time.time()
            for _ in range(5):
                try:
                    r = c.request(method, path, json=body) if body else c.request(method, path)
                    r.json()
                    sizes.append(len(r.content))
                    vers.add(r.http_version)
                    if "log" not in path:
                        hashes.add(hashlib.sha256(r.content).hexdigest()[:10])
                except Exception as e:
                    errs.append(repr(e)[:200])
            rec(f"large response x5 {'h2' if h2 else 'h1'} {path}", None, sizes=sizes, versions=sorted(vers),
                distinct_bodies=len(hashes), errors=errs, seconds=round(time.time() - t, 2))

with open(os.path.join(HERE, "results", "edge-cases.json"), "w") as f:
    json.dump(out, f, indent=1)
