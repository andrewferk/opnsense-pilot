# Allowlist probe run: what the read-only allowlist really does on 26.7.4_1

Lab run for [issue #13](https://github.com/andrewferk/opnsense-pilot/issues/13), done **2026-09-20** against the
throwaway probe VM from [issue #12](https://github.com/andrewferk/opnsense-pilot/issues/12): OPNsense Community
**26.7.4_1** (amd64, core hash `4fd8ebfb1`, FreeBSD 15.1-RELEASE-p3), reached at `https://127.0.0.1:10443`, guest
network-isolated. It validates the source-reading predictions of the
[read-only endpoint review](https://github.com/andrewferk/opnsense-pilot/blob/research/read-only-endpoint-review/docs/research/read-only-endpoint-review.md)
(issue #10). Client: httpx 0.28.1 on Python, API key + secret as HTTP Basic, redirects never followed.

Everything here was observed, not read from source, unless marked otherwise. The owner's real firewall was not touched.

## Headline

- **The allowlist works.** As admin, 46 of 47 calls (43 entries plus the four `+v6` twins) return 200; the 47th is the
  ISC lease read, 404 because the plugin is not installed. As the least-privilege account, 43 return 200 with **exactly
  the same response shape as admin**; the other four are 403 (two privileges deliberately withheld, one upstream ACL
  bug) and the same 404. The whole pass takes 13 s.
- **Nothing mutated.** Across the full limited-user pass `config.xml` kept the same SHA-256 and mtime, the backup
  count stayed at 34, the process table was identical, and every one of the 166 configd jobs spawned was a
  list/show/request action.
- **OPNsense cannot make an account read-only.** The same account, holding `user-config-readonly`, reloaded the
  firewall, restarted a service, wiped the system log, and wrote a config revision. The typed client allowlist has to
  be the control; the privilege set is only defence in depth.
- **The httpx large-response claim does not reproduce.** 15 of 15 chunked responses of 145 to 239 KB parsed cleanly
  over HTTP/1.1. The suggested workaround (HTTP/2) is the path that fails with httpx on this box.

## Method

1. Warm snapshot `pre13`. Seeded config rows as admin (`seed.py`, `seed_fix.py`): aliases (one 12,000-host alias for
   a large response, one URL table with credentials), a filter rule, source/destination/1:1/NPT NAT rules, an
   interface group, a VLAN, a CARP VIP with a password, a gateway group, a static route, Unbound and dnsmasq hosts, a
   Kea subnet with a TSIG secret and a reservation, a WireGuard instance and peer. Config only; nothing applied. Fake
   secrets carry a greppable marker.
2. Ran the allowlist (`allowlist.py`, `run_allowlist.py`) three ways: admin; `pilot-readonly` with its original three
   privileges; `pilot-readonly` widened (`widen_readonly.py`) to the derived least-privilege set.
3. Around the widened pass, read guest state over the serial console (`guest_state.sh`): config hash and mtime, backup
   count, configd/audit/system log lengths, process table, WAN packet capture.
4. Edge cases (`edge_cases.py`, `h2_check.py`, `check_snat.py`, `f1_legacy.py`), syscall traces of the firmware scripts
   (`guest_cmds/`), then destructive checks (`destructive.py`) between snapshot `seeded13` and its restore.
5. `scan_for_secrets.py` checks this directory for credential values, API key ids, seed markers and unredacted secret
   fields; it passes. Raw console dumps were deleted because OPNsense's own log lines contain API key ids.

Run any script with `uv run --with 'httpx[http2]' python <script>`. Credentials are read from the probe directory
outside the repo.

## Capability table

Full machine-readable rows: `results/admin.json`, `results/readonly-minimal.json`, `results/readonly-wide.json`.
Sanitized response fixtures (rows truncated to three, long strings cut, secrets redacted): `fixtures/admin/`,
`fixtures/readonly-wide/`. The config export body (E1) was never written to disk.

See [`results/capability-table.md`](results/capability-table.md) for the per-call table (status for each of the three
passes, bytes, seconds, row count, shape equality, secret fields). Summary:

| Outcome as the least-privilege account | Calls |
| --- | --- |
| 200, same shape as admin | S1 S2 S3, I1 to I6, F1 to F12, G1 G2, R1 R2, V1, D1 D2, H1 to H5 and the v6 twins, W1 to W4, L1 L2 |
| 403 because the privilege was deliberately withheld | S4 firmware status (`page-system-firmware-manualupdate`), E1 config export (`page-diagnostics-configurationhistory`) |
| 403 **despite holding the intended privilege** | G3 gateway groups: `page-system-gatewaygroups` does not grant `/api/routing/group_settings/search`. Upstream ACL pattern bug confirmed |
| 404 for every caller | H6 ISC leases: plugin `os-isc-dhcp` absent; its privilege id `page-status-dhcpleases` does not exist on the box either |

Slowest calls under pure emulation: filter rules 1.4 s, dnsmasq leases 1.2 s, Kea leases 1.0 s, interface overview 0.8 s.
Every authenticated API call costs two extra configd jobs (`list shells`, `list locales`) before its own work.

### Privilege set for the read-only account (confirmed)

All 29 ids exist on 26.7.4_1 and together grant every 200 above:

`user-config-readonly`, `page-system-login-logout`, `page-system-status`, `page-status-interfaces`,
`page-interfaces-assignnetworkports`, `page-interfaces-vlan-edit`, `page-firewall-virtualipaddress-edit`,
`page-interfaces-lagg-edit`, `page-interfaces-bridge-edit`, `page-filter-api`, `page-filter-snat-api`,
`page-firewall-nat-portforward-edit`, `page-firewall-nat-1-1-edit`, `page-firewall-nat-npt`, `page-firewall-aliases`,
`page-diagnostics-tables`, `page-interfaces-groups-edit`, `page-system-gateways`, `page-system-gatewaygroups`
(currently useless, see G3), `page-system-staticroutes`, `page-diagnostics-routingtables`, `page-status-services`,
`page-services-unbound`, `page-services-dnsforwarder`, `page-dhcp-kea-v4`, `page-dhcp-kea-v6`, `page-wireguard-config`,
`page-wireguard-diagnostics`, `page-diagnostics-logs-system` (one such privilege per log scope wanted).

Not granted, on purpose: `page-system-firmware-manualupdate`, `page-diagnostics-configurationhistory`, `page-all`.
With only the original three privileges, S1 to S3 return 200 and everything else 403.

`page-interfaces-assignnetworkports` is the dangerous one: it is what lets this account write config (below). An
operator who drops it loses only I2 (interface assignments), which I1 largely covers.

## How the outcomes differ on the wire

| Situation | Status | Body | Notes |
| --- | --- | --- | --- |
| No credentials | **302** | empty, `Location: /?url=...` | never follow redirects; treat as auth failure |
| Wrong key or wrong secret | 401 | `{"status":401,"message":"Authentication Failed"}` | no `WWW-Authenticate` header |
| Authenticated, privilege missing | 403 | `{"status":403,"message":"Forbidden"}` | 0.04 s; logged with the caller's **API key id in clear text** |
| Endpoint absent (unknown module, controller, action, or uninstalled plugin) | 404 | `{"errorMessage":"Endpoint not found"}` | decided **before** the ACL check, so an unprivileged caller can still tell absent from denied; `Content-Type` is spelled `application/json;charset=utf-8` here and `application/json; charset=UTF-8` everywhere else |
| Write refused by `user-config-readonly` | **500** | `{"errorMessage":"User ... denied for write access (user-config-readonly set)","errorTitle":"General access","errorLevel":"error"}` | not a 403 |
| GET with `Content-Type: application/json` and no body | 400 | `{"status":400,"message":"Invalid JSON syntax"}` | confirmed; the client must not set that header on GETs |
| Wrong verb | **200** | GET on `alias/add_item` gives `{"result":"failed"}`; GET on the log query path gives `[]`; POST on `source_nat/get` just answers | unsupported use is **not** signalled by status. The registry must pin the verb; an empty 200 is not proof of "nothing there" |
| Unknown object in a path segment (`alias_util/list/no_such_alias`) | 200 | empty rowset | same caution |

## Side effects

- **Config:** SHA-256 `379fdd3f...ed7a6`, mtime, and 34 backups all unchanged across the widened pass. No dashboard or
  model cache write reached `config.xml`.
- **Jobs:** 169 configd log lines: 3 access denials and 166 jobs, all reads: `list shells`/`list locales` (46 each, the per-request auth overhead),
  `list gateways`, DHCP option lists, `request ifconfig`, pf table listings, routing table, Kea and dnsmasq lease
  lists, `system status`, `Show log`, `Stream log`, `Show disk usage`, `Retrieve firmware product info`, service list,
  WireGuard dump, and the three automatic/legacy rule listings. Same process table before and after.
- **Network:** the isolated guest has no IPv4 default route, so a WAN capture cannot prove anything (it saw zero
  packets even for a call that does try the mirror; a control ping was captured, so the capture itself worked). The
  stronger test was `truss -f` on the scripts. `firmware/product.php` (behind S1 and GET S4), including its
  `opnsense-update` and `opnsense-verify` children: **0 `connect`/`sendto`/`sendmsg`, 0 inet sockets.** Control,
  `query.sh remote` (behind the excluded `GET /api/core/firmware/info`): 16 network syscalls, DNS lookups for the
  mirror, and pkg fetch errors in the configd log. This closes the review's "external binaries assumed network-free"
  item for the installed-version read.

## What the "read-only" account could still do

Run as `pilot-readonly` with the set above. Snapshot taken before, restored after (hash verified).

| Attempt | Result | Effect verified in the guest |
| --- | --- | --- |
| `POST /api/interfaces/vlan_settings/add_item` | 500, write denied | none |
| `POST /api/firewall/alias_util/add/pilot_hosts` | 500, write denied (the 26.7.1 fix holds) | none |
| `POST /api/firewall/filter/apply` | **200** | `filter.reload` ran |
| `POST /api/core/service/restart/cron` | **200** | cron restarted (new start time) |
| `POST /api/diagnostics/log/core/system/clear` | **200** | system log went from 286 lines to 3 |
| `POST /api/interfaces/assignment/reconfigure` | **200** | `interface.apply` ran and **a new config revision and backup were written, attributed to `pilot-readonly`** (only the revision block changed, but it is a config write by a deny-config-write user) |

The last row is a live confirmation of the review's source finding and is reportable upstream, alongside the gateway
group ACL pattern. Neither was reported as part of this run.

## Corrections and additions to the source review

1. **Source NAT search hides stored rules.** With the mode at its default `automatic`, `source_nat/search_rule`
   returned zero rows although a manual rule was stored and retrievable by uuid (`check_snat.py`; controller lines
   120 to 134 at the pinned commit list manual rules only in `hybrid`/`advanced`). On this box it returned no
   automatic rows either. The inventory must read F3 (mode) with F2 and must not read an empty list as "no rules
   configured". GET and POST searches returned identical results everywhere tested.
2. **More secret fields than predicted.** Observed non-empty: VIP `password`, alias `password` (URL-table
   credentials, with `username`) in both alias search and alias export, Kea subnet `ddns_domain_key_secret`, WireGuard
   instance `privkey`, WireGuard peer `psk`. The WireGuard peer model also has a `privkey` field (empty here). Seed
   markers came back in plaintext in I4, F7 and F8. The redaction list is: `password`, `privkey`, `psk`,
   `ddns_domain_key_secret`, plus the GeoIP URL in the alias export.
3. **`legacy` does not mean "user's legacy rule".** In `filter/search_rule` all 33 system-generated rows carry
   `legacy: true` **and** `is_automatic: true` with 32-hex ids; MVC rows have neither flag and a real uuid. A fresh
   26.7 install has no user legacy rules (its default LAN rules are MVC rows), so how a genuine user legacy rule is
   flagged is still unobserved. `migration/count_rules` works for admin (count 0) and is 403 for the limited account,
   as predicted.
4. **Old path spellings still route.** `searchItem`, `getRoutes` and `aliasUtil` all answer 200 for admin on
   26.7.4_1, so the snake_case move did not remove camelCase routing. ACL patterns match the raw URL, so for the
   limited account `alias/searchItem` is allowed (pattern `search*`) while `getRoutes` and `aliasUtil` are 403. The
   registry should pin the snake_case spelling. `groupsettings/search` is 404 for everyone.
5. **Savepoint API is gone:** `POST /api/firewall/filter/savepoint` is 404 as admin, matching the third-party claim.
   The Kea and NAT paths in the allowlist exist as written. Nothing else about pre-26.7 paths was tested.
6. **HTTP/2.** The server offers HTTP/2 and follows the client's ALPN preference. httpx lists `http/1.1` first, so
   with `http2=True` it still lands on HTTP/1.1; forced to HTTP/2 only, httpx gets `Server disconnected` on every
   request, small or large, while curl's HTTP/2 works including the 145 KB body. Keep the connector on HTTP/1.1.
7. `system_time` reports the last config-change time, a cheap API-side change detector. `get_nameservers` returned
   `[]` on this isolated box.

## Coverage gaps (what the API still cannot give the inventory)

Confirmed by this run:

- **Gateway groups** for any non-admin account (ACL bug), and **legacy outbound NAT / legacy rule migration reads**
  (403 without `page-all`).
- **Stored source NAT rules while the mode is automatic or disabled.**
- **ISC DHCP leases** unless the plugin is installed; not exercised.

Carried over from the review, unchanged by this run (no API controller exists, so there was nothing to call):
per-interface IP configuration, PPP, scrub rules, schedules, ISC DHCP server configuration, general and advanced
system settings, NTP, auth servers. E1 (`backup/download/this`) returns the whole 183 KB `config.xml` for admin and
would close all of these, at the price of every secret on the box plus a privilege that also allows revert and delete
of backups.

## Not done

- No user legacy filter rules, legacy outbound NAT rules, or ISC DHCP were present, so their API visibility is untested.
- Row caps (9,999 for recordset searches) were not reached; largest rowset was 285 log rows.
- Only the `system` log scope was exercised. The firewall live log, IPsec, OpenVPN and the unreviewed interface
  device types were not added to the allowlist.
- Running services were mostly unconfigured (Kea and WireGuard not started), so lease and tunnel status fixtures are
  empty rowsets.
- One release only. The seed data and the widened account live in the VM's `seeded13` snapshot and overlay; a cold
  `reset.sh` discards them, and `seed.py`, `seed_fix.py` and `widen_readonly.py` recreate them.
