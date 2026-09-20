"""What can the 'read-only' account still change? THROWAWAY VM ONLY. Snapshot first, restore after.

Each step runs as pilot-readonly (least-privilege set + user-config-readonly). Between steps an
admin client reads the config backup list and the system log size to see what really changed.
"""
import json
import os

from probe_lib import client

HERE = os.path.dirname(os.path.abspath(__file__))
LOGQ = {"current": 1, "rowCount": 1, "searchPhrase": "", "severity": "", "validFrom": "0"}
out = []

with client("admin") as adm, client("readonly") as ro:
    def state():
        b = adm.get("/api/core/backup/backups/this").json()
        items = b.get("items", b) if isinstance(b, dict) else b
        newest = items[0] if isinstance(items, list) and items else {}
        log_total = adm.post("/api/diagnostics/log/core/system", json=LOGQ).json().get("total_rows")
        cron = next((s for s in adm.get("/api/core/service/search").json()["rows"] if s["id"] == "cron"), {})
        return {"backups": len(items), "newest_time": newest.get("time_iso") or newest.get("time"),
                "newest_by": newest.get("username"), "newest_descr": str(newest.get("description"))[:80],
                "system_log_rows": log_total, "cron_running": cron.get("running")}

    def step(label, method, path, body=None, who=None):
        before = state()
        r = (who or ro).request(method, path, json=body) if body is not None else (who or ro).request(method, path)
        after = state()
        changed = {k: [before[k], after[k]] for k in before if before[k] != after[k]}
        row = {"step": label, "request": f"{method} {path}", "status": r.status_code,
               "body": r.text[:300].replace("\n", " "), "changed": changed}
        out.append(row)
        print(json.dumps(row)[:600])

    print("initial", json.dumps(state()))
    step("guarded model write (VLAN add)", "POST", "/api/interfaces/vlan_settings/add_item",
         {"vlan": {"if": "vtnet0", "tag": "11", "pcp": "0", "vlanif": "vlan0.11", "descr": "readonly should not write"}})
    step("guarded custom write (alias_util add, fixed in 26.7.1)", "POST", "/api/firewall/alias_util/add/pilot_hosts",
         {"address": "192.0.2.77"})
    step("filter apply (configd reload, unguarded by design)", "POST", "/api/firewall/filter/apply", {})
    step("service restart cron (unguarded by design)", "POST", "/api/core/service/restart/cron", {})
    step("log clear (unguarded by design)", "POST", "/api/diagnostics/log/core/system/clear", {})
    step("assignment reconfigure (source: saves config with no guard)", "POST", "/api/interfaces/assignment/reconfigure", {})
    step("admin: savepoint API still present? (claimed removed at 26.7)", "POST", "/api/firewall/filter/savepoint", {}, who=adm)
    print("final", json.dumps(state()))

with open(os.path.join(HERE, "results", "destructive.json"), "w") as f:
    json.dump(out, f, indent=1)
