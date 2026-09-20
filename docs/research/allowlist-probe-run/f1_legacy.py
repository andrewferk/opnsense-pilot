"""How does filter/search_rule mark MVC, legacy and automatic rows? (limited user, GET)"""
import collections

from probe_lib import client

with client("readonly") as c:
    rows = c.get("/api/firewall/filter/search_rule").json()["rows"]
    kinds = collections.Counter((bool(r.get("legacy")), bool(r.get("is_automatic")), len(str(r.get("uuid", ""))) == 36) for r in rows)
    for (legacy, auto, real_uuid), n in kinds.items():
        print(f"legacy={legacy} is_automatic={auto} uuid_is_real={real_uuid}: {n} rows")
    for r in rows:
        if r.get("legacy") or not r.get("is_automatic"):
            print(" ", {k: r.get(k) for k in ("uuid", "legacy", "is_automatic", "interface", "action", "description")})
    print("migration count (needs page-all):", c.get("/api/firewall/migration/count_rules").status_code)
