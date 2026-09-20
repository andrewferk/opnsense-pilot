"""Set pilot-readonly's privileges (admin write on the throwaway VM).

  widen_readonly.py            the derived least-privilege set
  widen_readonly.py +priv ...  the set plus extra privilege ids (for targeted experiments)
"""
import sys

from probe_lib import client

LEAST_PRIVILEGE = """user-config-readonly
page-system-login-logout page-system-status page-status-interfaces
page-interfaces-assignnetworkports page-interfaces-vlan-edit page-firewall-virtualipaddress-edit
page-interfaces-lagg-edit page-interfaces-bridge-edit page-filter-api page-filter-snat-api
page-firewall-nat-portforward-edit page-firewall-nat-1-1-edit page-firewall-nat-npt
page-firewall-aliases page-diagnostics-tables page-interfaces-groups-edit
page-system-gateways page-system-gatewaygroups page-system-staticroutes
page-diagnostics-routingtables page-status-services page-services-unbound
page-services-dnsforwarder page-dhcp-kea-v4 page-dhcp-kea-v6
page-wireguard-config page-wireguard-diagnostics page-diagnostics-logs-system""".split()

privs = LEAST_PRIVILEGE + [a[1:] for a in sys.argv[1:] if a.startswith("+")]
with client("admin") as c:
    ro = next(u for u in c.get("/api/auth/user/search").json()["rows"] if u["name"] == "pilot-readonly")
    r = c.post(f"/api/auth/user/set/{ro['uuid']}", json={"user": {"priv": ",".join(privs)}})
    print(r.status_code, r.text[:200])
    got = c.get(f"/api/auth/user/get/{ro['uuid']}").json()["user"]["priv"]
    sel = sorted(k for k, v in got.items() if v.get("selected"))
    print(len(sel), "privileges now set; missing:", sorted(set(privs) - set(sel)))
