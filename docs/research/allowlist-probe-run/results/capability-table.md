| # | Call | admin | limited, minimal privs | limited, least-privilege set | bytes | s | rows | same shape as admin | non-empty secret fields |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | `GET /api/diagnostics/system/system_information` | 200 | 200 | 200 | 149 | 0.662 |  | yes |  |
| S2 | `GET /api/diagnostics/system/system_time` | 200 | 200 | 200 | 174 | 0.258 |  | yes |  |
| S3 | `GET /api/core/system/status` | 200 | 200 | 200 | 176 | 0.17 |  | yes |  |
| S4 | `GET /api/core/firmware/status` | 200 | 403 | 403 | 1723 | 0.045 |  | n/a |  |
| I1 | `GET /api/interfaces/overview/interfaces_info/1` | 200 | 403 | 200 | 7193 | 0.783 | 5 | yes |  |
| I2 | `GET /api/interfaces/assignment/search_item` | 200 | 403 | 200 | 395 | 0.547 | 2 | yes |  |
| I3 | `GET /api/interfaces/vlan_settings/search_item` | 200 | 403 | 200 | 260 | 0.225 | 1 | yes |  |
| I4 | `GET /api/interfaces/vip_settings/search_item` | 200 | 403 | 200 | 439 | 0.037 | 1 | yes | rows[].password |
| I5 | `GET /api/interfaces/lagg_settings/search_item` | 200 | 403 | 200 | 46 | 0.228 | 0 | yes |  |
| I6 | `GET /api/interfaces/bridge_settings/search_item` | 200 | 403 | 200 | 46 | 0.038 | 0 | yes |  |
| F1 | `GET /api/firewall/filter/search_rule` | 200 | 403 | 200 | 30304 | 1.386 | 36 | yes |  |
| F2 | `GET /api/firewall/source_nat/search_rule` | 200 | 403 | 200 | 46 | 0.391 | 0 | yes |  |
| F3 | `GET /api/firewall/source_nat/get` | 200 | 403 | 200 | 321 | 0.118 |  | yes |  |
| F4 | `GET /api/firewall/d_nat/search_rule` | 200 | 403 | 200 | 3061 | 0.365 | 3 | yes |  |
| F5 | `GET /api/firewall/one_to_one/search_rule` | 200 | 403 | 200 | 1029 | 0.152 | 1 | yes |  |
| F6 | `GET /api/firewall/npt/search_rule` | 200 | 403 | 200 | 724 | 0.119 | 1 | yes |  |
| F7 | `GET /api/firewall/alias/search_item` | 200 | 403 | 200 | 145540 | 0.289 | 10 | yes | rows[].password |
| F8 | `GET /api/firewall/alias/export` | 200 | 403 | 200 | 150162 | 0.255 |  | yes | aliases.alias.<uuid>.password |
| F9 | `GET /api/firewall/alias_util/aliases` | 200 | 403 | 200 | 94 | 0.218 |  | yes |  |
| F10 | `GET /api/firewall/alias_util/list/pilot_hosts` | 200 | 403 | 200 | 46 | 0.221 | 0 | yes |  |
| F11 | `GET /api/firewall/group/search_item` | 200 | 403 | 200 | 518 | 0.043 | 4 | yes |  |
| F12 | `GET /api/firewall/category/search_item` | 200 | 403 | 200 | 141 | 0.041 | 1 | yes |  |
| G1 | `GET /api/routing/settings/search_gateway` | 200 | 403 | 200 | 1386 | 0.41 | 2 | yes |  |
| G2 | `GET /api/routes/gateway/status` | 200 | 403 | 200 | 302 | 0.219 |  | yes |  |
| G3 | `GET /api/routing/group_settings/search` | 200 | 403 | 403 | 491 | 0.045 | 1 | n/a |  |
| R1 | `GET /api/routes/routes/searchroute` | 200 | 403 | 200 | 211 | 0.044 | 1 | yes |  |
| R2 | `GET /api/diagnostics/interface/get_routes` | 200 | 403 | 200 | 2869 | 0.234 |  | yes |  |
| V1 | `GET /api/core/service/search` | 200 | 403 | 200 | 1035 | 0.672 | 12 | yes |  |
| D1 | `GET /api/unbound/settings/get` | 200 | 403 | 200 | 3795 | 0.076 |  | yes |  |
| D2 | `GET /api/dnsmasq/settings/get` | 200 | 403 | 200 | 3599 | 0.089 |  | yes |  |
| H1 | `GET /api/kea/dhcpv4/get` | 200 | 403 | 200 | 978 | 0.078 |  | yes |  |
| H1-6 | `GET /api/kea/dhcpv6/get` | 200 | 403 | 200 | 897 | 0.077 |  | yes |  |
| H2 | `GET /api/kea/dhcpv4/search_subnet` | 200 | 403 | 200 | 1096 | 0.104 | 1 | yes | rows[].ddns_domain_key_secret |
| H2-6 | `GET /api/kea/dhcpv6/search_subnet` | 200 | 403 | 200 | 46 | 0.079 | 0 | yes |  |
| H3 | `GET /api/kea/dhcpv4/search_reservation` | 200 | 403 | 200 | 654 | 0.078 | 1 | yes |  |
| H3-6 | `GET /api/kea/dhcpv6/search_reservation` | 200 | 403 | 200 | 46 | 0.076 | 0 | yes |  |
| H4 | `GET /api/kea/leases4/search` | 200 | 403 | 200 | 106 | 0.984 | 0 | yes |  |
| H4-6 | `GET /api/kea/leases6/search` | 200 | 403 | 200 | 106 | 0.962 | 0 | yes |  |
| H5 | `GET /api/dnsmasq/leases/search` | 200 | 403 | 200 | 62 | 1.201 | 0 | yes |  |
| H6 | `GET /api/dhcpv4/leases/search_lease` | 404 | 404 | 404 | 37 | 0.003 |  | n/a |  |
| W1 | `GET /api/wireguard/general/get` | 200 | 403 | 200 | 27 | 0.035 |  | yes |  |
| W2 | `GET /api/wireguard/server/search_server` | 200 | 403 | 200 | 626 | 0.073 | 1 | yes | rows[].privkey |
| W3 | `GET /api/wireguard/client/search_client` | 200 | 403 | 200 | 419 | 0.078 | 1 | yes | rows[].psk |
| W4 | `GET /api/wireguard/service/show` | 200 | 403 | 200 | 46 | 0.285 | 0 | yes |  |
| L1 | `POST /api/diagnostics/log/core/system` | 200 | 403 | 200 | 61776 | 0.342 | 282 | yes |  |
| L2 | `GET /api/diagnostics/log/core/system/export` | 200 | 403 | 200 | 27306 | 0.363 |  | n/a |  |
| E1 | `GET /api/core/backup/download/this` | 200 | 403 | 403 | 183474 | 0.035 |  | n/a |  |
