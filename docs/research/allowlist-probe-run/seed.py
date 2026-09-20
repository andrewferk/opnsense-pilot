"""Seed the throwaway probe VM (admin) so allowlist reads return rows with real shapes.

Config-only: nothing is applied/reconfigured, so the running firewall is untouched.
Every secret seeded here is a fake marker beginning with SEEDSECRET so leaks are greppable.
Idempotence is not attempted: run once on a snapshot.
"""
import base64
import json
import os

from probe_lib import client

MARK = "SEEDSECRET"
big = "\n".join(f"10.{a}.{b}.{c}" for a in range(1, 4) for b in range(0, 40) for c in range(1, 101))  # 12000 hosts


def fake_wg_key():
    return base64.b64encode(os.urandom(32)).decode()


with client("admin", timeout=600) as c:
    def post(path, payload):
        r = c.post("/api/" + path, json=payload)
        try:
            body = r.json()
        except Exception:
            body = r.text[:200]
        print(path, r.status_code, json.dumps(body)[:300])
        return body if isinstance(body, dict) else {}

    kp = c.get("/api/wireguard/server/key_pair").json()
    kp2 = c.get("/api/wireguard/server/key_pair").json()
    psk = c.get("/api/wireguard/client/psk").json()
    print("key_pair keys:", sorted(kp), "psk keys:", sorted(psk))

    post("firewall/category/add_item", {"category": {"name": "pilot-seed", "color": "00aa00"}})
    post("firewall/alias/add_item", {"alias": {"enabled": "1", "name": "pilot_hosts", "type": "host",
                                               "content": "192.0.2.10\n192.0.2.11", "description": "pilot seed"}})
    post("firewall/alias/add_item", {"alias": {"enabled": "1", "name": "pilot_urltable", "type": "urltable",
                                               "content": "https://192.0.2.99/list.txt", "updatefreq": "1",
                                               "username": "seeduser", "password": MARK + "-alias-password",
                                               "authtype": "Basic", "description": "pilot seed with auth"}})
    post("firewall/alias/add_item", {"alias": {"enabled": "0", "name": "pilot_big", "type": "host",
                                               "content": big, "description": "pilot seed large response"}})
    post("firewall/filter/add_rule", {"rule": {"enabled": "1", "action": "pass", "interface": "lan",
                                               "ipprotocol": "inet", "protocol": "TCP", "source_net": "pilot_hosts",
                                               "destination_net": "any", "destination_port": "443",
                                               "description": "pilot seed mvc rule"}})
    post("firewall/source_nat/add_rule", {"rule": {"enabled": "1", "interface": "wan", "ipprotocol": "inet",
                                                   "source_net": "192.168.1.0/24", "destination_net": "any",
                                                   "target": "wanip", "description": "pilot seed snat"}})
    post("firewall/d_nat/add_rule", {"rule": {"interface": "wan", "ipprotocol": "inet", "protocol": "tcp",
                                              "destination": {"network": "wanip", "port": "8443"},
                                              "target": "192.168.1.50", "local-port": "443",
                                              "descr": "pilot seed dnat"}})
    post("firewall/one_to_one/add_rule", {"rule": {"enabled": "1", "interface": "wan", "type": "binat",
                                                   "source_net": "192.168.1.60/32", "destination_net": "any",
                                                   "external": "198.51.100.60", "description": "pilot seed 1:1"}})
    post("firewall/npt/add_rule", {"rule": {"enabled": "1", "interface": "wan", "source_net": "fd00:1::/64",
                                            "destination_net": "2001:db8:1::/64", "description": "pilot seed npt"}})
    post("firewall/group/add_item", {"group": {"ifname": "pilotgrp", "members": "lan", "descr": "pilot seed"}})
    post("interfaces/vlan_settings/add_item", {"vlan": {"if": "vtnet0", "tag": "10", "pcp": "0",
                                                        "vlanif": "vlan0.10", "descr": "pilot seed vlan"}})
    post("interfaces/vip_settings/add_item", {"vip": {"interface": "lan", "mode": "carp", "network": "192.168.1.250/24",
                                                      "vhid": "5", "advbase": "1", "advskew": "0",
                                                      "password": MARK + "-carp-password", "descr": "pilot seed carp"}})
    post("routing/settings/add_gateway", {"gateway_item": {"name": "PILOT_GW", "interface": "lan", "ipprotocol": "inet",
                                                           "gateway": "192.168.1.254", "monitor_disable": "1",
                                                           "descr": "pilot seed gateway"}})
    post("routing/group_settings/add", {"gateway_group": {"name": "PILOT_GROUP", "item": "PILOT_GW", "trigger": "down",
                                                          "descr": "pilot seed group"}})
    post("routes/routes/addroute", {"route": {"network": "203.0.113.0/24", "gateway": "PILOT_GW",
                                              "descr": "pilot seed route", "disabled": "1"}})
    post("unbound/settings/add_host_override", {"host": {"enabled": "1", "hostname": "seed", "domain": "pilot.example",
                                                         "rr": "A", "server": "192.0.2.53", "description": "pilot seed"}})
    post("dnsmasq/settings/add_host", {"host": {"host": "seedmasq", "domain": "pilot.example", "ip": "192.0.2.54",
                                                "descr": "pilot seed"}})
    sub = post("kea/dhcpv4/add_subnet", {"subnet4": {"subnet": "192.168.1.0/24", "pools": "192.168.1.100-192.168.1.199",
                                                     "ddns_forward_zone": "pilot.example.", "ddns_dns_server": "192.0.2.53",
                                                     "ddns_domain_key_name": "seedkey",
                                                     "ddns_domain_key_secret": base64.b64encode((MARK + "-kea-tsig").encode()).decode(),
                                                     "ddns_domain_key_algorithm": "hmac-sha256",
                                                     "description": "pilot seed subnet"}})
    if sub.get("uuid"):
        post("kea/dhcpv4/add_reservation", {"reservation": {"subnet": sub["uuid"], "ip_address": "192.168.1.150",
                                                            "hw_address": "02:00:00:00:00:01", "hostname": "seedhost",
                                                            "description": "pilot seed reservation"}})
    peer = post("wireguard/client/add_client", {"client": {"enabled": "1", "name": "pilot-peer", "pubkey": kp2.get("pubkey", ""),
                                                           "psk": psk.get("psk", ""), "tunneladdress": "10.99.0.2/32",
                                                           "keepalive": "25"}})
    post("wireguard/server/add_server", {"server": {"enabled": "0", "name": "pilot-wg", "pubkey": kp.get("pubkey", ""),
                                                    "privkey": kp.get("privkey", ""), "port": "51999",
                                                    "tunneladdress": "10.99.0.1/24", "peers": peer.get("uuid", "")}})
