"""Print the blank-record field names for each model we want to seed (admin, GET only)."""
from probe_lib import client

TEMPLATES = [
    "firewall/alias/get_item", "firewall/filter/get_rule", "firewall/source_nat/get_rule",
    "firewall/d_nat/get_rule", "firewall/one_to_one/get_rule", "firewall/npt/get_rule",
    "firewall/group/get_item", "firewall/category/get_item",
    "interfaces/vlan_settings/get_item", "interfaces/vip_settings/get_item",
    "routing/settings/get_gateway", "routing/group_settings/get", "routes/routes/getroute",
    "unbound/settings/get_host_override", "dnsmasq/settings/get_host",
    "kea/dhcpv4/get_subnet", "kea/dhcpv4/get_reservation",
    "wireguard/server/get_server", "wireguard/client/get_client",
]


def keys(d, prefix=""):
    out = []
    for k, v in d.items():
        if isinstance(v, dict) and v and not all(isinstance(x, dict) and "selected" in x for x in v.values()):
            out += keys(v, prefix + k + ".")
        else:
            out.append(prefix + k)
    return out


with client("admin") as c:
    for t in TEMPLATES:
        r = c.get("/api/" + t)
        try:
            print(t, r.status_code, " ".join(keys(r.json())))
        except Exception:
            print(t, r.status_code, r.text[:120].replace("\n", " "))
