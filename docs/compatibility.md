# Compatibility: what OPNsense Pilot v1 supports and how it reads it

This document is the compatibility target for the read-only v1. It declares one supported release line, the edition and architecture, the plugin scope, the privileges the Pilot account holds, and, for every inventory category, which path collects it and what evidence stands behind that claim. Anything not listed here is not supported, and the service says so rather than guessing.

Decision record: [ADR 0010](adr/0010-v1-compatibility-target-and-support-tiers.md). Evidence: [release target](https://github.com/andrewferk/opnsense-pilot/issues/3), [version mapping](https://github.com/andrewferk/opnsense-pilot/issues/4), [allowlist source review](https://github.com/andrewferk/opnsense-pilot/issues/10), [allowlist lab run](https://github.com/andrewferk/opnsense-pilot/issues/13), [gap path](https://github.com/andrewferk/opnsense-pilot/issues/25).

## Target

| Item | Value |
| --- | --- |
| Product | OPNsense **Community** edition |
| Release line | **26.7** ("Xenial Xenops"), range `26.7.x`, floor `26.7.4` |
| Verified release | **26.7.4_1** (core `product_hash` `4fd8ebfb1`, one commit after tag `26.7.4` on `stable/26.7`) |
| Architecture | **amd64** only |
| Base system | FreeBSD 15.1-RELEASE (p3 at 26.7.4) |
| Pinned sources | `opnsense/core` `26.7.4` = `ace3b5b5f856261f77b71bd54f3fe63fa2447a12`; `opnsense/plugins` `26.7.4` = `6cb23d364671d7d409f2e9e9a14987efcc8ccc7e`; `opnsense/docs` `2c85e8a9ea43f4e008a536734ad428783fae94f9` |
| Plugins required | **none** |
| Lab | QEMU (TCG) from `OPNsense-26.7-nano-amd64.img.bz2`, upgraded in place to 26.7.4_1, no plugins installed |

Hotfix suffixes such as `_1` are untagged upstream; the verified release is identified by its build hash, not by a tag. Release numbers compare numerically per component (`26.7.10` is above `26.7.4`), never as strings.

## Support tiers

Every registered firewall is placed in exactly one **support tier** from the release it reports. The tier decides whether inventory is collected at all.

| Tier | Meaning | What Pilot does |
| --- | --- | --- |
| **verified** | A Community amd64 release on which the full read-only operation suite passed in the lab. Today: `26.7.4_1`. | Collects every category below; detectors run. |
| **assumed** | Inside the `26.7.x` range at or above the floor, but not run in the lab. Today: `26.7.4` without the hotfix and any later `26.7.x`. | Collects every category below; the snapshot carries a warning naming the nearest verified release; detectors run at their own verified ranges. |
| **unsupported** | Everything else: `26.7.0` to `26.7.3`, `26.1` and older, `27.x`, `-devel` packages, Business edition, non-amd64 builds (including the unofficial aarch64 build), and any release whose build hash cannot be mapped to upstream. | The firewall registers, Pilot reads only the network-free system-information operation, every inventory category is `not collected` with reason `unsupported release`, and every detector abstains. Nothing else is called. |

A point release moves from assumed to verified only after the lab suite is rerun on the probe VM upgraded to that release and any path changes are recorded in the operation registry (for example gateway groups move from export to API once upstream's ACL fix ships). That rerun is a standing v1 maintenance item.

Support tier is independent of **version confidence**, which says how the release was learned: `exact` when the firmware API's build hash maps to one upstream commit, `degraded` when only a version string or a user-declared release (config import) is available. An assumed-tier firewall can have exact confidence; an unsupported one is unsupported however confidently its release is known.

## Edition and architecture

- **Business edition** is unsupported. Its packages have no public source tags after 21.10, so no operation can be verified against it and no build hash can be mapped.
- **arm64 / aarch64** is unsupported, not merely untested: the only aarch64 build is unofficial and outside the upstream release process.
- Pilot never silently degrades on either: they land in the unsupported tier above.

## Plugins

v1 requires **no plugin** and grants the Pilot account **no plugin page privilege**. The plugins repository at the pinned tag contains 69 direct configuration saves across 13 plugins with no read-only guard, so any plugin privilege on the Pilot account voids the read-only claim. Consequences:

- ISC DHCP server configuration is read from the config export (see below); ISC DHCP **leases** are not collected in v1 (the only path needs a plugin privilege).
- The legacy firewall rules detector needs no plugin: it reads core's rule search and the export. `os-firewall-legacy` is only named in its recommended next step.
- The `plugin absent` coverage reason is reserved for future entries; no v1 category uses it.

## The Pilot account

The Pilot account is a local OPNsense user with an API key and the privilege set below, and nothing more. The set is the least the lab run needed for every API-collected category; it was verified on 26.7.4_1 to leave `config.xml` unchanged across the whole suite.

**Base set (26 privileges, always granted):**

`user-config-readonly`, `page-system-login-logout`, `page-system-status`, `page-status-interfaces`, `page-interfaces-vlan-edit`, `page-firewall-virtualipaddress-edit`, `page-interfaces-lagg-edit`, `page-interfaces-bridge-edit`, `page-filter-api`, `page-filter-snat-api`, `page-firewall-nat-portforward-edit`, `page-firewall-nat-1-1-edit`, `page-firewall-nat-npt`, `page-firewall-aliases`, `page-diagnostics-tables`, `page-interfaces-groups-edit`, `page-system-gateways`, `page-system-gatewaygroups`, `page-system-staticroutes`, `page-diagnostics-routingtables`, `page-status-services`, `page-services-unbound`, `page-services-dnsforwarder`, `page-dhcp-kea-v4`, `page-dhcp-kea-v6`, `page-wireguard-config`, `page-wireguard-diagnostics`

**Deliberately withheld:**

- `page-interfaces-assignnetworkports`: on 26.7.4_1 it also permits `POST /api/interfaces/assignment/reconfigure`, which writes a configuration revision as the Pilot user ([opnsense/core#10910](https://github.com/opnsense/core/issues/10910), guarded upstream by [core#10915](https://github.com/opnsense/core/pull/10915), not yet released). Interface assignments come from the export instead. This privilege returns as a per-release path once the guarded release is verified.
- All `page-diagnostics-logs-*` scopes: logs are not part of the v1 inventory, and the same privilege permits clearing them.
- `page-all`, every firmware privilege, and every plugin privilege.

**Opt-in (granted only when live config export is enabled for that firewall):**

- `page-diagnostics-configurationhistory` ("Diagnostics: Configuration History"). It is the only privilege short of `page-all` that allows `GET /api/core/backup/download/this`, and it **also allows backup revert and delete** over the API. Pilot never calls those; the operation registry, not this privilege, keeps Pilot read-only. The export contains every secret on the firewall and is redacted in memory before anything is stored ([ADR 0008](adr/0008-config-export-is-the-only-gap-path-in-v1.md)).

`user-config-readonly` is a courtesy, not a control: on 26.7.4_1 an account carrying it could still reload interfaces, restart services, and clear logs through privileges the base set does not include. What keeps Pilot read-only is that its connector can only issue operations in the reviewed operation registry ([ADR 0005](adr/0005-build-the-connector-and-operation-registry.md)).

## Inventory coverage on 26.7.4_1

Every category in a snapshot carries a coverage value (`collected`, `partial`, `not collected`) and, when not collected, one reason: `no API`, `privilege denied`, `export not enabled`, `plugin absent`, `outside v1 inventory`, `unsupported release`. Each collected item also records its evidence source: `API`, `live export`, or `imported export`. The table below is what a verified-tier firewall with the base privilege set reports; the export column applies when live export is enabled or a file is imported.

| Category | Item | Path | Notes |
| --- | --- | --- | --- |
| System | Installed release and build hash | API | Network-free; the only operation issued on an unsupported firewall |
| System | Firmware status, update availability | not collected: outside v1 inventory | The GET contacts mirrors or needs a withheld privilege |
| Interfaces | Overview and runtime state | API | |
| Interfaces | VLAN, LAGG, bridge, interface groups | API | |
| Interfaces | Assignments (port to interface) | export | API path withheld, see privileges |
| Interfaces | Per-interface IP configuration | export | No API on 26.7 |
| Interfaces | PPP | not collected: outside v1 inventory | |
| Firewall | Filter rules (MVC, legacy, and automatic in one read) | API | System-generated rows carry `legacy` and `is_automatic` flags |
| Firewall | Legacy rule count (detector cross-check) | export | Core's count API needs `page-all` |
| Firewall | Aliases and runtime tables | API | Alias URL-table credentials are secrets, redacted |
| Firewall | Categories | API | |
| Firewall | Schedules, scrub rules | not collected: outside v1 inventory | |
| NAT | Source NAT rules and mode | API, export | API hides stored rules while mode is `automatic`; the export holds them |
| NAT | Legacy outbound NAT | export | |
| NAT | Destination NAT (port forward), 1:1, NPT | API | |
| Gateways | Gateways and status | API | |
| Gateways | Gateway groups | export | API returns 403 on 26.7.4_1 from an upstream ACL pattern bug, fixed on master by [core#10909](https://github.com/opnsense/core/pull/10909); becomes an API path in the release that ships it |
| Routes | Configured and runtime routes | API | |
| Services | Service list and running state | API | Start, stop, and restart share the privilege and are excluded by the registry |
| DNS | Unbound, dnsmasq configuration | API | |
| DHCP | Kea general, subnets, reservations, leases (v4 and v6) | API | Kea TSIG secret is redacted |
| DHCP | dnsmasq leases | API | |
| DHCP | ISC DHCP server configuration | export | Legacy pages, no API |
| DHCP | ISC DHCP leases | not collected: outside v1 inventory | Only path needs a plugin privilege |
| WireGuard | Configuration and status | API | Private keys and preshared keys are redacted; status verified only with the service stopped |
| WireGuard | CARP virtual IP passwords | API (redacted) | Listed here because the VIP read is secret-bearing |
| System | General and advanced settings, NTP, auth servers | not collected: outside v1 inventory | |
| Logs | All scopes | not collected: outside v1 inventory | |

**Export path.** All `export` rows come from one parser over `config.xml`, delivered live over the backup API (per-firewall opt-in, off by default) or imported from a file. When neither is available those rows report `not collected` with reason `export not enabled`. An imported export carries no product version, so the user declares the release at import; it is recorded at `degraded` confidence and the support tier is derived from the declared release.

**Secrets.** Reads that return secrets on 26.7.4_1 (WireGuard `privkey` and `psk`, CARP VIP `password`, alias `password`, Kea `ddns_domain_key_secret`, everything in the export) are redacted at the connector boundary before persistence; the redaction list is reviewed and grows from lab data.

**Not verified, not promised.** IPv6 DHCP twins beyond the four run, GIF, GRE, VXLAN and wireless controllers, the firewall live log, and log scopes other than `system` were not exercised. They are not "unknown" here; they are outside the v1 inventory, and tracked in the risk register as candidates for a later slice.

## How to read a claim in this document

- An **API** row means a registered operation exists for the `26.7.x` range, the lab suite returned 200 with the base privilege set on 26.7.4_1, the response shape matched an admin's, and no configuration change or non-read background job was observed.
- An **export** row means the reviewed export parser covers that section and the row is filled only when an export is available.
- **not collected** rows are never rendered as empty lists; the reason travels with the snapshot through CLI, REST, and MCP.
- A permission error is never evidence that a feature is absent: `403` is recorded as `privilege denied`, `404` as a missing operation on that release, and neither is treated as "not configured".
