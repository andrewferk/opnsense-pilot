"""Why does GET source_nat/search_rule return no rows when a rule exists?"""
import json

from probe_lib import client

UUID = "61e0b13e-279f-47fb-89c9-45c4dbf471b6"
with client("admin") as c:
    g = c.get(f"/api/firewall/source_nat/get_rule/{UUID}").json()
    print("get_rule descr:", g.get("rule", {}).get("description"), "| keys:", len(g.get("rule", {})))
    print("mode:", json.dumps(c.get("/api/firewall/source_nat/get").json())[:400])
    for label, kw in [
        ("GET bare", {}),
        ("POST std", {"json": {"current": 1, "rowCount": -1, "searchPhrase": ""}}),
        ("POST empty obj", {"json": {}}),
    ]:
        m = "POST" if "POST" in label else "GET"
        r = c.request(m, "/api/firewall/source_nat/search_rule", **kw)
        b = r.json()
        print(label, r.status_code, "rows", len(b.get("rows", [])), "total", b.get("total"),
              [x.get("description") for x in b.get("rows", [])])
    # same comparison on the filter controller, where GET returned 36 rows
    for label, kw in [("GET bare", {}), ("POST std", {"json": {"current": 1, "rowCount": -1, "searchPhrase": ""}})]:
        m = "POST" if "POST" in label else "GET"
        b = c.request(m, "/api/firewall/filter/search_rule", **kw).json()
        print("filter", label, "rows", len(b["rows"]), "total", b.get("total"))
