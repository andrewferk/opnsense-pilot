"""Show the limited user's current privileges and check which derived privilege ids exist on the box."""
import sys

from probe_lib import client

WANTED = """page-system-login-logout page-system-status page-status-interfaces
page-interfaces-assignnetworkports page-interfaces-vlan-edit page-firewall-virtualipaddress-edit
page-interfaces-lagg-edit page-interfaces-bridge-edit page-filter-api page-filter-snat-api
page-firewall-nat-portforward-edit page-firewall-nat-1-1-edit page-firewall-nat-npt
page-firewall-aliases page-diagnostics-tables page-interfaces-groups-edit page-firewall-rules
page-system-gateways page-system-gatewaygroups page-system-staticroutes
page-diagnostics-routingtables page-status-services page-services-unbound
page-services-dnsforwarder page-dhcp-kea-v4 page-dhcp-kea-v6 page-status-dhcpleases
page-wireguard-config page-wireguard-diagnostics page-diagnostics-logs-system
page-diagnostics-configurationhistory page-system-firmware-manualupdate
user-config-readonly page-all""".split()

with client("admin") as c:
    rows = c.get("/api/auth/user/search").json()["rows"]
    for u in rows:
        print(u["name"], u["uuid"], sorted(k for k in u if k not in ("name", "uuid")))
    ro = next(u for u in rows if u["name"] == "pilot-readonly")
    detail = c.get(f"/api/auth/user/get/{ro['uuid']}").json()["user"]
    privs = detail["priv"]
    print("priv field type:", type(privs).__name__, "options:", len(privs))
    print("selected:", [k for k, v in privs.items() if v.get("selected")])
    for w in WANTED:
        print(("OK      " if w in privs else "MISSING ") + w, "|", privs.get(w, {}).get("value", ""))
    if "--logs" in sys.argv:
        for k, v in sorted(privs.items()):
            if "log" in k.lower():
                print("LOGPRIV", k, "|", v.get("value"))
