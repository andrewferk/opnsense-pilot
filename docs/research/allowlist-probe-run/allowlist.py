"""The proposed read-only allowlist from the endpoint review (ticket #10), as data.

Ids match the review's table; `6` suffixes are the v6 twins it marked `+v6`.
"""
import time

LOG_BODY = {"current": 1, "rowCount": 500, "searchPhrase": "", "severity": "", "validFrom": "0"}

ALLOWLIST = [
    ("S1", "GET", "/api/diagnostics/system/system_information"),
    ("S2", "GET", "/api/diagnostics/system/system_time"),
    ("S3", "GET", "/api/core/system/status"),
    ("S4", "GET", "/api/core/firmware/status"),
    ("I1", "GET", "/api/interfaces/overview/interfaces_info/1"),
    ("I2", "GET", "/api/interfaces/assignment/search_item"),
    ("I3", "GET", "/api/interfaces/vlan_settings/search_item"),
    ("I4", "GET", "/api/interfaces/vip_settings/search_item"),
    ("I5", "GET", "/api/interfaces/lagg_settings/search_item"),
    ("I6", "GET", "/api/interfaces/bridge_settings/search_item"),
    ("F1", "GET", "/api/firewall/filter/search_rule"),
    ("F2", "GET", "/api/firewall/source_nat/search_rule"),
    ("F3", "GET", "/api/firewall/source_nat/get"),
    ("F4", "GET", "/api/firewall/d_nat/search_rule"),
    ("F5", "GET", "/api/firewall/one_to_one/search_rule"),
    ("F6", "GET", "/api/firewall/npt/search_rule"),
    ("F7", "GET", "/api/firewall/alias/search_item"),
    ("F8", "GET", "/api/firewall/alias/export"),
    ("F9", "GET", "/api/firewall/alias_util/aliases"),
    ("F10", "GET", "/api/firewall/alias_util/list/pilot_hosts"),
    ("F11", "GET", "/api/firewall/group/search_item"),
    ("F12", "GET", "/api/firewall/category/search_item"),
    ("G1", "GET", "/api/routing/settings/search_gateway"),
    ("G2", "GET", "/api/routes/gateway/status"),
    ("G3", "GET", "/api/routing/group_settings/search"),
    ("R1", "GET", "/api/routes/routes/searchroute"),
    ("R2", "GET", "/api/diagnostics/interface/get_routes"),
    ("V1", "GET", "/api/core/service/search"),
    ("D1", "GET", "/api/unbound/settings/get"),
    ("D2", "GET", "/api/dnsmasq/settings/get"),
    ("H1", "GET", "/api/kea/dhcpv4/get"),
    ("H1-6", "GET", "/api/kea/dhcpv6/get"),
    ("H2", "GET", "/api/kea/dhcpv4/search_subnet"),
    ("H2-6", "GET", "/api/kea/dhcpv6/search_subnet"),
    ("H3", "GET", "/api/kea/dhcpv4/search_reservation"),
    ("H3-6", "GET", "/api/kea/dhcpv6/search_reservation"),
    ("H4", "GET", "/api/kea/leases4/search"),
    ("H4-6", "GET", "/api/kea/leases6/search"),
    ("H5", "GET", "/api/dnsmasq/leases/search"),
    ("H6", "GET", "/api/dhcpv4/leases/search_lease"),
    ("W1", "GET", "/api/wireguard/general/get"),
    ("W2", "GET", "/api/wireguard/server/search_server"),
    ("W3", "GET", "/api/wireguard/client/search_client"),
    ("W4", "GET", "/api/wireguard/service/show"),
    ("L1", "POST", "/api/diagnostics/log/core/system"),
    ("L2", "GET", "/api/diagnostics/log/core/system/export"),
    ("E1", "GET", "/api/core/backup/download/this"),
]

# Bodies that must never be written to disk, even sanitized.
NEVER_SAVE = {"E1"}


def request_kwargs(eid):
    if eid == "L1":
        return {"json": LOG_BODY}
    if eid == "L2":
        return {"params": {"validFrom": str(int(time.time()) - 3600)}}
    return {}
