"""Second seed pass: gateway group and static route, using whatever gateway options the box offers."""
import json

from probe_lib import client

with client("admin") as c:
    g = c.get("/api/routing/group_settings/get").json()["gateway_group"]
    for k in ("item", "item2", "trigger"):
        print(k, {a: b.get("value") for a, b in g[k].items()} if isinstance(g[k], dict) else g[k])
    r = c.get("/api/routes/routes/getroute").json()["route"]
    gws = {a: b.get("value") for a, b in r["gateway"].items()}
    print("route.gateway", gws)
    gw4 = next((a for a in gws if a and "6" not in a), None)
    item = next((a for a in g["item"] if a), None)
    if item:
        p = c.post("/api/routing/group_settings/add", json={"gateway_group": {
            "name": "PILOT_GROUP", "item": item, "trigger": "down", "descr": "pilot seed group"}})
        print("group", p.status_code, json.dumps(p.json())[:300])
    if gw4:
        p = c.post("/api/routes/routes/addroute", json={"route": {
            "network": "203.0.113.0/24", "gateway": gw4, "descr": "pilot seed route", "disabled": "1"}})
        print("route", p.status_code, json.dumps(p.json())[:300])
