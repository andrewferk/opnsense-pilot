# Legacy and migration cases as first-detector candidates

Research for [issue #11](https://github.com/andrewferk/opnsense-pilot/issues/11). All facts were read on **2026-09-19** from the cited primary source. Nothing is carried over from the handoff or from memory; the handoff's illustrative claims (DHCP backends, NAT/rule representation, WireGuard plugin-to-core) were treated as leads and are each confirmed or refuted below. This document ranks; the owner picks the detector in a later ticket.

## Pinned sources

Working target (provisional, from [issue #3](https://github.com/andrewferk/opnsense-pilot/issues/3)): OPNsense Community 26.7.4. Tags verified with `gh api repos/opnsense/<repo>/git/ref/tags/26.7.4` and dereferenced (both are annotated tags).

| Short name | Repo and ref | Commit |
| --- | --- | --- |
| `CORE` | `opnsense/core` tag `26.7.4` (tag object `4b70db4090faca26f2854752535e5958410cff32`) | `ace3b5b5f856261f77b71bd54f3fe63fa2447a12` |
| `PLUGINS` | `opnsense/plugins` tag `26.7.4` (tag object `d4d67cd58cbd1ad1b5282467f0d7ed0ac3057ab4`) | `6cb23d364671d7d409f2e9e9a14987efcc8ccc7e` |
| `CHANGELOG` | `opnsense/changelog` master | `e38c5c2f6d517267f4b6efb8fc7e742521fdf485` |
| `DOCS` | `opnsense/docs` master (no tags exist) | `2c85e8a9ea43f4e008a536734ad428783fae94f9` |
| `CORE@25.1` | `opnsense/core` branch `stable/25.1` head, same commit as tag `25.1.12` | `d143c9ec25253ee8bd26e8636c8dc5b1fd63eb30` |
| `CORE@25.7` | `opnsense/core` branch `stable/25.7` head | `2e9ac2defb5e6df55b4055179bdea8606cbef235` |
| `CORE@26.1.11` | `opnsense/core` tag `26.1.11` | `c930ab586ffe2d2e010e5135657e5e054316ff58` |
| `PLUGINS@26.1` | `opnsense/plugins` tag `26.1` | `b681e4dd5c11a9d9c0361a3ed22a612c08908d78` |

Citations below are `NAME:path:lines`. Build a permalink as `https://github.com/opnsense/<repo>/blob/<commit>/<path>#L<a>-L<b>`. Changelog paths are under `community/`.

## Ranked shortlist

Ranked by evidence strength first, fixture feasibility second. "Status" is the feature status only; every one of these configurations can be perfectly healthy.

| # | Candidate | Status at 26.7.4 | Evidence strength | Fixture feasibility |
| --- | --- | --- | --- | --- |
| 1 | Legacy firewall rules (`filter.rule`) with MVC rules as successor | legacy_supported, migration_available (manual assistant) | Strongest: release notes, core's own `legacyPaths` list, a core API that counts them, plugin split, docs | High: config import or `os-firewall-legacy` on a clean 26.7.4 |
| 2 | Legacy outbound NAT rules (`nat.outbound.rule`) with Source NAT as successor | deprecated (word used in core source), migration_available (manual assistant) | Very strong: explicit "deprecated" string at the tag, `legacyPaths`, count API, release notes | High: the legacy page still ships in core at 26.7.4; good inert boundary case |
| 3 | ISC DHCP (`dhcpd`, `dhcpdv6`, `os-isc-dhcp`) with Dnsmasq or Kea as successor | legacy_supported, upstream end-of-life, no migration tool found | Strong: docs say EOL, release notes, `legacyPaths`, plugin | High, but full answer needs config plus package presence, and DHCPv6 has an implicit-enable rule |
| 4 | Legacy OpenVPN servers/clients (`openvpn.openvpn-server`, `openvpn.openvpn-client`) with Instances as successor | legacy_supported, "first step to deprecation", not migrated | Strong: release notes, docs, `legacyPaths`, upstream's own "is it active" script | Medium-high: needs `os-openvpn-legacy` and certificates to build a positive on a clean box |
| 5 | Legacy IPsec tunnels (`ipsec.phase1`, `ipsec.phase2`) with Connections as successor | legacy_supported, "first step to deprecation", not migrated, "No timeline" | Strong, slightly weaker than 4: not in `legacyPaths` | Medium-high: needs `os-strongswan-legacy` |
| 6 | IKEv1 IPsec connections, with IKEv2 as successor | supported today; deprecation announced for 27.1 on the roadmap only | Weak: one roadmap line, no source change at the tag | High: a model field value |
| 7 | Orphaned plugin configuration (for example `OPNsense.ndproxy` after `os-ndproxy` was removed) | removed plugin, config remains | Medium: generic mechanism confirmed in core, one concrete removal confirmed | Medium: needs the installed-model set, so not a pure config check |

Cross-cutting finding that matters for whichever is picked: core at the tag carries an explicit, five-entry list of legacy configuration paths, and an API endpoint that reports which of them are present. See "Upstream's own legacy inventory" next.

## Upstream's own legacy inventory

`OPNsense\Core\ConfigMaintenance` hard-codes the legacy (non-model) config sections that core considers flushable:

```
'dhcpd' => 'Services: ISC DHCPv4 [legacy]'
'dhcpdv6' => 'Services: ISC DHCPv6 [legacy]'
'filter.rule' => 'Firewall: Rules [legacy]'
'nat.outbound.rule' => 'Firewall: NAT: Outbound [legacy]'
'openvpn' => 'VPN: OpenVPN [legacy]'
```

Source: `CORE:src/opnsense/mvc/app/library/OPNsense/Core/ConfigMaintenance.php:40-46`.

- `traverseConfig()` walks `config.xml` and yields every section that is an installed model, one of these legacy paths, or a node carrying a `version` attribute with no installed model (reported with `installed = 0`). Source: same file, lines 90-134.
- It is exposed read-only as `GET /api/core/defaults/get_installed_sections`. Source: `CORE:src/opnsense/mvc/app/controllers/OPNsense/Core/Api/DefaultsController.php:84-93`.
- Caveat for the least-privilege API user: the only ACL pattern covering it is `api/core/defaults/*` under "Diagnostics: Factory defaults", the same privilege that covers the factory-reset POST (`CORE:src/opnsense/mvc/app/models/OPNsense/Core/ACL/ACL.xml:60-66`). The destructive actions call `throwReadOnly()` (DefaultsController lines 71, 100), which blocks users holding `user-config-readonly` (`CORE:src/opnsense/mvc/app/controllers/OPNsense/Base/ApiControllerBase.php:46-57`). Whether the project wants to grant that privilege at all is a question for the API-access ticket. Not exercised against a live box.
- Legacy IPsec is absent from this list, so the list is not a complete inventory.

How migrations run, which decides what can survive as "legacy" on an upgraded box: model migrations run through `pluginctl -M` / `-m` (`CORE:src/sbin/pluginctl:309-312`), called from `convert_config()` (`CORE:src/etc/inc/config.inc:161-173`), which runs at boot (`CORE:src/etc/rc.bootup:57-63`), on firmware update (`CORE:src/etc/rc.configure_firmware:49`, triggered by `CORE:src/etc/rc.syshook.d/update/10-refresh.sh`), and on config restore in the GUI (`CORE:src/www/diag_backup.php:147,294,343`). Anything covered by a model migration is therefore rewritten automatically and does not persist as a legacy form. The candidates below are exactly the cases that are **not** covered by an automatic migration.

Config export through the API exists: `GET /api/core/backup/download/this` (`CORE:src/opnsense/mvc/app/controllers/OPNsense/Core/Api/BackupController.php:179`). Package presence is available from `GET /api/core/firmware/info` (`CORE:src/opnsense/mvc/app/controllers/OPNsense/Core/Api/FirmwareController.php:801`). Neither was exercised against a live box here.

## Candidate 1: legacy firewall rules

**Legacy form and successor.** Legacy: `<filter><rule>` entries in `config.xml`, edited by static PHP pages. Successor: the MVC model `OPNsense\Firewall\Filter` mounted at `//OPNsense/Firewall/Filter`, model version 1.0.6, described as "Firewall rules (new)" (`CORE:src/opnsense/mvc/app/models/OPNsense/Firewall/Filter.xml:2-5`). Both are loaded into the running ruleset: legacy via `filter_core_rules_user()` (`CORE:src/etc/inc/filter.lib.inc:674-699`, called at `CORE:src/etc/inc/filter.inc:191-192`), MVC via `CORE:src/etc/inc/plugins.inc.d/pf.inc:168-174`.

**Versions.**
- 26.1: "firewall: added a rule migration page (use with care)" and "The firewall migration page is not something you need to jump into right away" (`CHANGELOG:community/26.1/26.1:49,123`). The successor pages were the former "automation" pages, promoted in 26.1 (`CHANGELOG:community/26.1/26.1:12,44`).
- 26.7: successor became the default. "firewall rules now defaulting to MVC/API", "firewall: move config.xml default LAN allow rules to new rules GUI", "firewall: legacy rules pages move to plugin", "os-firewall-legacy 1.0 contains the static PHP firewall rules pages" (`CHANGELOG:community/26.7/26.7:12,46,47,81`). The factory config at the tag has an empty `<filter>` and two default LAN rules under `OPNsense/Firewall/Filter/rules` (`CORE:src/etc/config.xml.sample:105-117`); at 26.1.11 the same two default rules were still legacy `<filter><rule>` entries (`CORE@26.1.11:src/etc/config.xml.sample:107-132`).
- Removal: no date announced. Docs say "**Rules [new]** will replace **Rules** over time" (`DOCS:source/manual/firewall.rst:24-25,538`). The roadmap lists "Legacy firewall rules to plugin (eases new installs)" as a completed 26.7 item and nothing about removal under 27.1 (https://opnsense.org/about/road-map/, read through a summarising fetch).

**Migration.** Manual. "All rules will continue to work regardless of the plugin being installed or not and are easily migrated using the given assistant." (`CHANGELOG:community/26.7/26.7:98`). The assistant exports legacy rules as CSV in MVC shape for re-import, then offers to flush `filter.rule` (`CORE:src/opnsense/mvc/app/controllers/OPNsense/Firewall/Api/MigrationController.php:37-73`, conversion in `CORE:src/opnsense/scripts/filter/list_legacy_rules.php:37-150`). No upgrade hook installs `os-firewall-legacy`: the 26.7 note says it "can be manually installed before or after the upgrade", and `stable/26.1` ships only `10-sanity.sh` under `src/etc/rc.syshook.d/upgrade/`. The plugin is GUI pages only: "backend code still exists in the core and legacy rules can be migrated without this plugin installed" (`PLUGINS:net/firewall-legacy/pkg-descr`, files `src/www/firewall_rules.php` and `firewall_rules_edit.php`).

**Detection evidence.** Config only, no runtime state: one or more `filter.rule` elements. Core uses the identical test to decide whether to show the "Migration assistant" menu entry: `!empty($config->filter->rule) && !empty($config->filter->rule->count())` (`CORE:src/opnsense/mvc/app/models/OPNsense/Firewall/Menu/Menu.php:51-61`). Plugin presence (`/usr/local/www/firewall_rules.php`, package `os-firewall-legacy`) changes only whether the rules are still editable, not whether they are enforced (`Menu.php:63-71`, `filter.lib.inc:676,692-693`).

**API reachability.**
- `GET /api/firewall/migration/count_rules` returns the legacy rule count; `download_rules` returns them as CSV (`MigrationController.php:48-61`). No ACL pattern for `api/firewall/migration` was found anywhere in core at the tag (the only hits for `firewall/migration` are the view, menu and two links), so it may be reachable only with the all-pages privilege. **Unverified on a live box.**
- `GET /api/firewall/filter/search_rule` always merges non-MVC rules (`CORE:src/opnsense/mvc/app/controllers/OPNsense/Firewall/Api/FilterController.php:186-189`), and legacy ones carry `legacy = true` (`CORE:src/opnsense/scripts/filter/list_non_mvc_rules.php:120`). Covered by the ordinary "Firewall: Rules [new]" privilege (`CORE:src/opnsense/mvc/app/models/OPNsense/Firewall/ACL/ACL.xml:3-8`). The backend action is cached for 60 s (`CORE:src/opnsense/service/conf/actions.d/actions_filter.conf:207-212`).
- `get_installed_sections` reports id `filter.rule`.
- Config export shows it directly.

**Fixtures.** A clean 26.7.4 install can be put into the legacy state: restore a config containing `<filter><rule>` (no model migration touches it), or install `os-firewall-legacy` and add rules in its pages. A genuinely upgraded system is not required.
- Positive: legacy rules only. Negative: factory 26.7 config (empty `<filter>`).
- Boundary version: the 26.1.11 factory config is positive by construction while the 26.7 factory config is negative, so the same "fresh install" differs across the series boundary.
- Healthy legacy: legacy rules, no plugin, ruleset loads. Mixed: legacy and MVC rules together (ordering between them is a real question; the 26.1 note warns "Single interface from the floating interface will not be considered 'floating' in priorities").
- Incomplete input: export with `<filter>` stripped or redacted; API-only input without config export.
- Genuinely upgraded configs may differ in incidental shape: core adds missing `uuid` attributes to legacy rules when sorting (`CORE:src/etc/inc/filter.inc:90-97`), so older exports can lack them.

**Prevalence.** Structural argument from source, not measured: until 26.7 the factory config itself shipped two legacy rules and the legacy pages were the main rules GUI, and no automatic migration exists. Every system installed before 26.7 whose owner has not run the assistant is positive. This is likely the most common legacy state on upgraded 26.7 systems.

## Candidate 2: legacy outbound NAT rules

**Legacy form and successor.** Legacy: `<nat><outbound><rule>` entries edited by `firewall_nat_out.php`. Successor: Source NAT rules in the same Filter model, `OPNsense/Firewall/Filter/snatrules` (`CORE:src/opnsense/mvc/app/models/OPNsense/Firewall/Filter.xml:453`). The mode is shared, not legacy: the model's volatile `general.snat_mode` field is persisted into `nat.outbound.mode` (`Filter.xml:7-18`, `CORE:src/opnsense/mvc/app/models/OPNsense/Firewall/Filter.php:433-441`). So `nat.outbound.mode` must never be used as the legacy signal; only `nat.outbound.rule` is.

**Versions.**
- 26.1: "Firewall: NAT: Source NAT is from the set of pages formerly known as automation, but Outbound NAT is still the main page for these types of rules." (`CHANGELOG:community/26.1/26.1:125`).
- 26.1.11: "this update brings the outbound to source NAT migration page, but it is only a formality as outbound NAT will stay in 26.7"; also "the source NAT rules entered in the system will no longer work unless the mode is set to either 'manual' or 'hybrid'" (`CHANGELOG:community/26.1/26.1.11:11-16,35`).
- 26.7: "outbound NAT to source NAT migration assistant" (`CHANGELOG:community/26.7/26.7:13`). 26.7.2: "working on feature parity between Outbound NAT and Source NAT" (`CHANGELOG:community/26.7/26.7.2:9-12`). 26.7.4: "a final push for better source NAT replacement over outbound NAT", "firewall: add source NAT migration banner to outbound NAT" (`CHANGELOG:community/26.7/26.7.4:5-6,40`).
- Deprecation is stated in core source at the tag: "This legacy outbound NAT page is deprecated and will be replaced by the new Source NAT rules interface." (`CORE:src/www/firewall_nat_out.php:276-282`).
- Removal: no version announced. The roadmap lists "Merge outbound NAT into source NAT page" as a completed 26.7 item. The legacy pages are still in core at 26.7.4 (`src/www/firewall_nat_out.php`, `firewall_nat_out_edit.php`), not in a plugin.

**Migration.** Manual, same assistant: `count_outbound`, `download_outbound`, `flush_outbound` (`MigrationController.php:75-101`), conversion in `CORE:src/opnsense/scripts/filter/list_legacy_outbound_nat.php`. Nothing runs on upgrade.

**Detection evidence.** Config only: one or more `nat.outbound.rule` elements (`Menu.php:52-53`). Legacy rules are only enforced when the mode is `advanced` or `hybrid` (`CORE:src/etc/inc/filter.inc:194-206`); the same gate applies to MVC source NAT rules (`pf.inc:176-183`). Legacy rules register at priority 100 and MVC ones at 50, so both can be active together.

**API reachability.** `GET /api/firewall/migration/count_outbound` (same ACL caveat as candidate 1); `get_installed_sections` id `nat.outbound.rule`; config export. No hit for legacy outbound rules was found in the source NAT search API; not examined exhaustively.

**Fixtures.** Clean 26.7.4 works: restore a config with `<nat><outbound><rule>`, or use `firewall_nat_out.php`, which core still ships. The menu entry only appears when legacy rules already exist (`Menu.php:111-118`), so on a clean box the page would be opened by URL; **not verified on a live box**.
- Positive: mode `hybrid` or `advanced` with legacy rules. Negative: factory config (`<mode>automatic</mode>`, no rules, `CORE:src/etc/config.xml.sample:100-104`).
- Boundary (inert legacy): legacy rules present with mode `automatic` or `disabled`; they are configured but not loaded. A good test that status stays separate from health and effect.
- Boundary version: 26.1.11 introduced the assistant and the mode gating of source NAT; before that only the legacy page was "the main page".
- Mixed: legacy and MVC source NAT rules together. Incomplete: `<nat>` stripped.

**Prevalence.** Lower than candidate 1. Only systems that ever wrote manual or hybrid outbound NAT rules are positive; the factory mode is automatic with no rules. No primary data on how common that is.

## Candidate 3: ISC DHCP

**Legacy form and successor.** Legacy: `<dhcpd>` and `<dhcpdv6>` sections (per-interface children, legacy PHP, no model) served by the `os-isc-dhcp` plugin. Successors: Dnsmasq (default) and Kea, both core MVC models.

**Versions.**
- 24.1: Kea added "as an alternative to the end of life ISC DHCP"; "ISC DHCP functionality is slowly being deprecated" (`CHANGELOG:community/24.1/24.1:56,116`).
- 25.7: successor became default: "system: change default DHCP use from ISC to Dnsmasq for factory reset and console port and address assignments" (`CHANGELOG:community/25.7/25.7:31`). The 25.1.12 factory config enables `<dhcpd><lan>` (`CORE@25.1:src/etc/config.xml.sample:94-96`); the 26.7.4 one configures `<dnsmasq>` DHCP ranges and has no `<dhcpd>` (`CORE:src/etc/config.xml.sample:77-96`).
- 26.1: "ISC-DHCP moves to a plugin. It will be automatically installed during upgrades. It is not installed on new installations because it is not being used, but you can still install and keep using it." (`CHANGELOG:community/26.1/26.1:93,116`). Plugin: `PLUGINS:net/isc-dhcp/Makefile` (version 1.0, revision 7, tier 2), `pkg-descr` "used to be the standard implementation of DHCP until better alternatives such as Dnsmasq and Kea were supplied".
- Docs: "ISC DHCP is end-of-life and no longer receives updates or security patches. It is strongly recommended to migrate to KEA or Dnsmasq." and the server list marks "ISC (EOL)" (`DOCS:source/manual/isc.rst:13`, `DOCS:source/manual/dhcp.rst:14-17,79`).
- Removal of the plugin: none announced that I could find.

**Migration.** No automatic configuration migration. The only automatic step was package installation: the 25.7-to-26.1 upgrade hook installs `os-isc-dhcp` **unconditionally** unless the marker file `/usr/local/opnsense/version/isc-dhcp` exists (`CORE@25.7:src/etc/rc.syshook.d/upgrade/20-isc-dhcp-plugin.sh`; the hook was removed again from master in commit `b5bcb5f5243f2281ac86dc0180983343511998e2`). Consequence: on a system upgraded through 26.1, plugin presence alone says nothing about use. A word-boundary search for ISC in the Kea and Dnsmasq models, controllers, views and scripts at the tag found no importer; the only tooling is CSV export of static mappings in the plugin (`CHANGELOG:community/25.7/25.7:71`, `CHANGELOG:community/25.7/25.7.2:37`). Whether Kea or Dnsmasq can import that CSV was not checked.

**Detection evidence.** Upstream's own enable logic (`PLUGINS:net/isc-dhcp/src/etc/inc/plugins.inc.d/dhcpd.inc:52-93`):
- DHCPv4 is on when any `dhcpd.<if>.enable` is set and `interfaces.<if>` exists.
- DHCPv6 is on when any `dhcpdv6.<if>.enable` is set and not `-1` on an enabled interface, **or implicitly** when an enabled interface has `ipaddrv6 = track6` without `dhcpd6track6allowoverride` and is not explicitly switched off with `-1`. The 26.1 notes introduced the sibling IPv6 mode "Identity Association" (`idassoc6`) precisely so that this implicit start does not happen (`CHANGELOG:community/26.1/26.1:117`). Note the 26.7.4 factory config still sets LAN to track6 (`CORE:src/etc/config.xml.sample:73-74`), so the implicit rule only matters when the plugin is installed.
- All of this is config, but whether ISC is actually serving also depends on the package: with `<dhcpd>` enabled and no plugin, nothing runs. That orphaned case is a health finding, separate from the legacy status.
- Secondary signals: Dnsmasq's "ISC / KEA DHCP (legacy)" lease registration options (`CORE:src/opnsense/mvc/app/controllers/OPNsense/Dnsmasq/forms/general.xml:228-237`) and Unbound's ISC lease template (`CORE:src/opnsense/service/templates/OPNsense/Unbound/core/unbound_dhcpd.conf`).

**API reachability.** Settings are not in the API: the plugin only ships `Api/ServiceController.php` and `Api/LeasesController.php` for DHCPv4 and DHCPv6. `get_installed_sections` reports ids `dhcpd` and `dhcpdv6` when the sections exist, but not whether they are enabled. Package presence comes from the firmware info API. A precise answer (which interfaces, enabled or not, implicit DHCPv6) needs a config export.

**Fixtures.** Clean 26.7.4 works: install `os-isc-dhcp` from the 26.7 repo and enable it on LAN, or restore a config with `<dhcpd>`.
- Positive: `<dhcpd><lan><enable/>` plus plugin. Negative: factory 26.7 config.
- Boundary version: 25.1 factory config is positive by default; 25.7 and later factory configs are negative; 26.1 is where the package boundary appears.
- Boundary cases: plugin installed but no `<dhcpd>` enabled (expected on any box upgraded through 26.1, because of the unconditional hook); `<dhcpd>` present but every interface disabled; `<dhcpd>` enabled with plugin missing (orphaned); implicit DHCPv6 through track6; ISC and Dnsmasq both configured.
- Incomplete input: config without package list, or the reverse.

**Prevalence.** Structural argument: ISC was the factory default through 25.1, so any system installed at or before 25.1 has `<dhcpd>` enabled unless the owner moved. Likely common, second to candidate 1. No measurement.

## Candidate 4: legacy OpenVPN servers and clients

**Legacy form and successor.** Legacy: `<openvpn><openvpn-server>` and `<openvpn><openvpn-client>`. Successor: Instances in `//OPNsense/OpenVPN` (model 1.0.1, `CORE:src/opnsense/mvc/app/models/OPNsense/OpenVPN/OpenVPN.xml:2-3`).

**Versions.** Instances arrived in 23.7: "Legacy client/server settings cannot be managed from the API and are not migrated, but will continue to work independently." (`CHANGELOG:community/23.7/23.7:78,122`). 25.7: "os-openvpn-legacy 1.0 for legacy OpenVPN components support" and "Moved OpenVPN legacy to plugins as a first step to deprecation." (`CHANGELOG:community/25.7/25.7:102,114`). 26.1.8: "system: allow flushing legacy OpenVPN legacy config" (`CHANGELOG:community/26.1/26.1.8:20`). 26.7.4: "openvpn: moved legacy CARP hook to os-openvpn-legacy plugin" (`CHANGELOG:community/26.7/26.7.4:51`). Docs: Instances "will eventually replace the existing client and server options in a future version of OPNsense, leaving enough time to migrate older setups" (`DOCS:source/manual/vpnet.rst:678-683`). No removal version announced.

**Migration.** None for servers and clients; no migration tooling was found under the OpenVPN controllers, views or scripts at the tag. Only client-specific overrides were auto-migrated into the model (`CORE:src/opnsense/mvc/app/models/OPNsense/OpenVPN/Migrations/M1_0_0.php`). The 25.1-to-25.7 upgrade hook installed the plugin **conditionally**, and its condition is upstream's own definition of "legacy is active": any `openvpn-server` or `openvpn-client` entry with empty `disable` (`CORE@25.1:src/etc/rc.syshook.d/upgrade/20-openvpn-plugin.php`).

**Detection evidence.** Config for the status; config plus package for whether it runs. At the tag legacy OpenVPN is only started when the plugin's page exists **and** config is present: `file_exists('/usr/local/www/vpn_openvpn_server.php') && !empty($config['openvpn']["openvpn-{$mode}"])` (`CORE:src/etc/inc/plugins.inc.d/openvpn.inc:49-55`). Enabled legacy entries without the plugin are silently inactive, which is a health finding.

**API reachability.** Legacy servers are not manageable through the API. Indirect signals: `get_installed_sections` id `openvpn`; enabled legacy servers show up as client-export providers with a numeric `vpnid` rather than a UUID (`CORE:src/opnsense/mvc/app/controllers/OPNsense/OpenVPN/Api/ExportController.php:97-124`). Full detail needs a config export.

**Fixtures.** Clean 26.7.4 works with `os-openvpn-legacy` (`PLUGINS:security/openvpn-legacy/Makefile`, 1.0 revision 2) or by config restore; a positive needs a CA and certificates, so it is more work than candidates 1 to 3. Boundary cases: all entries disabled; enabled entries with plugin missing; legacy and Instances side by side. Boundary versions: 25.7 (plugin split), 23.7 (successor appears).

**Prevalence.** Limited to systems that configured OpenVPN before or without Instances. No data.

## Candidate 5: legacy IPsec tunnels

**Legacy form and successor.** Legacy: `<ipsec><phase1>` and `<ipsec><phase2>` ("Tunnel settings"). Successor: Connections in `//OPNsense/Swanctl` (`CORE:src/opnsense/mvc/app/models/OPNsense/IPsec/Swanctl.xml:2-3`).

**Versions.** Connections arrived in 23.1: "Legacy tunnel settings cannot be managed from the API and are not migrated." (`CHANGELOG:community/23.1/23.1:73,123`). 25.7: "os-strongswan-legacy 1.0 for legacy IPsec components support", "Moved IPsec legacy to plugins as a first step to deprecation.", and 25.7.2 "ipsec: deprecate legacy stroke and implement swanctl for overview" (`CHANGELOG:community/25.7/25.7:104,115`, `CHANGELOG:community/25.7/25.7.2:36`). Docs: "we decided to plan for deprecation of the legacy 'Tunnel settings' ... No timeline has been set, only a feature freeze" (`DOCS:source/manual/vpnet.rst:41-46`).

**Migration.** None automatic; docs describe manual conversion (`DOCS:source/manual/vpnet.rst:134-138`). The conditional upgrade hook defines "active" as any `ipsec.phase1` entry with empty `disabled` (`CORE@25.1:src/etc/rc.syshook.d/upgrade/20-strongswan-plugin.php`).

**Detection evidence.** Same pattern as OpenVPN: `file_exists('/usr/local/www/vpn_ipsec_phase1.php') && !empty($config['ipsec']['phase1'])` (`CORE:src/etc/inc/plugins.inc.d/ipsec.inc:138-144`); every consumer falls back to an empty list when that is false (for example lines 401, 801, 890). The `<ipsec>` node also holds non-legacy settings, and it is not in `legacyPaths`, so only `ipsec.phase1` and `ipsec.phase2` are the signal.

**API reachability.** Weak. `GET /api/ipsec/legacy_subsystem/status` returns only `enabled` and `isDirty` (`CORE:src/opnsense/mvc/app/controllers/OPNsense/IPsec/Api/LegacySubsystemController.php:47-53`). Session, SAD and SPD endpoints join runtime data against `ipsec.phase1` descriptions, which is runtime-dependent. Config export is the reliable route.

**Fixtures.** Clean 26.7.4 with `os-strongswan-legacy` (`PLUGINS:security/strongswan-legacy/Makefile`) or config restore. Same boundary set as candidate 4.

**Prevalence.** Site-to-site IPsec users who set up before 23.1 or kept using Tunnel settings. No data.

## Candidate 6: IKEv1 connections

Roadmap for 27.1 lists "IPSec: Deprecate IKEv1" (https://opnsense.org/about/road-map/; read through a summarising fetch tool, so the wording is lower confidence than the GitHub citations). Nothing at the 26.7.4 tag marks IKEv1 as deprecated: the Connections model still offers `IKEv1+IKEv2` (default, value 0), `IKEv1` (1) and `IKEv2` (2) (`CORE:src/opnsense/mvc/app/models/OPNsense/IPsec/Swanctl.xml:32-40`). Detection would be a pure model-field check reachable through the normal IPsec connections API, and fixtures are trivial. It ranks low because the evidence is a single forward-looking roadmap line: for the target release it is an announced future deprecation, not a legacy form with a preferred successor in source. Worth revisiting when 27.1 is targeted. What "deprecate" will mean for the default `IKEv1+IKEv2` value is unknown.

## Candidate 7: orphaned plugin configuration

`traverseConfig()` reports any config node with a `version` attribute and no installed model as `installed = 0` (`ConfigMaintenance.php:101-128`). Concrete confirmed case in the window: "plugins: os-ndproxy has been removed, use os-ndp-proxy-go instead" (`CHANGELOG:community/26.7/26.7:82`). The old model mounted at `//OPNsense/ndproxy` (`PLUGINS@26.1:net/ndproxy/src/opnsense/mvc/app/models/OPNsense/Ndproxy/Ndproxy.xml`), the replacement mounts at `//OPNsense/ndpproxy` and ships no `Migrations` directory (`PLUGINS:net/ndp-proxy-go/src/opnsense/mvc/app/models/OPNsense/NdpProxy/`), and `net/ndproxy` no longer exists at the 26.7.4 tag. So an upgraded box that used `os-ndproxy` keeps an unreferenced `OPNsense/ndproxy` section. Detection needs the set of installed models (the API gives it; a bare config export does not), and prevalence for this specific plugin is probably small. It is a generic hygiene detector more than a "legacy but working" one, since the orphaned config does nothing.

## Rejected and unconfirmed leads

**Refuted as detector candidates for this target (automatic, in-place, or out of window):**

- **WireGuard plugin-to-core.** Confirmed as history, refuted as a candidate. "plugins: os-wireguard moved to core" and "os-wireguard-go was discontinued" are 24.1 notes (`CHANGELOG:community/24.1/24.1:67,92-93`), five series before the target. At the tag the core models mount at `//OPNsense/wireguard/{client,general,server}` (`CORE:src/opnsense/mvc/app/models/OPNsense/Wireguard/*.xml`) and no wireguard plugin exists under `PLUGINS:net/`. No dual representation was found, so there is nothing legacy to detect in config.
- **NAT port forward to Destination NAT (26.1).** In place: the `DNat` model mounts directly on the legacy path `/nat/rule+` (`CORE:src/opnsense/mvc/app/models/OPNsense/Firewall/DNat.xml:2-3`, `CHANGELOG:community/26.1/26.1:43`). No separate legacy form survives.
- **One-to-one NAT and NPTv6.** Automatic: migrations `MFP1_0_4` and `MFP1_0_3` copy `nat.onetoone` and `nat.npt` into the Filter model and `post()` deletes the legacy nodes (`CORE:src/opnsense/mvc/app/models/OPNsense/Firewall/Migrations/MFP1_0_4.php`, `MFP1_0_3.php`).
- **Gateway groups, interface assignments, wireless, VLAN/LAGG/bridge/GIF/GRE, VIPs, users/groups, certificates, radvd.** All either mount in place on the legacy path (`/gateways/gateway_group+`, `/wireless`, `/vlans`, `/virtualip`, `/system/user+`, `/cert+`, ...) or have a migration with `post()` cleanup (`Routing/Migrations/M1_0_0.php:121-129`, `Radvd/Migrations/M1_0_0.php:155-163`, `Interfaces/Migrations/WLAN1_0_0.php:55-63`). These run on upgrade, boot and restore, so the legacy form does not persist.
- **Deprecated Unbound blocklists (25.7.6, 25.7.10).** Normalised automatically by `Unbound/Migrations/M1_0_13.php` (line 111, "Normalize deprecated blocklists").
- **`mwexec()` / `mwexec_bg()` removal (26.1.3).** Code-level API for custom PHP, not configuration (`CHANGELOG:community/26.1/26.1:119`, `CHANGELOG:community/26.1/26.1.3:66`).
- **"Track interface" versus "Identity Association" IPv6 mode.** Not a deprecation: upstream calls `idassoc6` a "sibling" (`CHANGELOG:community/26.1/26.1:117`). It matters only as an input to the ISC DHCPv6 implicit-enable rule in candidate 3.
- **Scrub rules and interface settings to MVC.** Planned for 27.1 per the roadmap; still legacy-only at 26.7.4, so there is no successor to prefer yet.

**Could not confirm:**

- **Suricata `custom.yaml` (removed in 26.1)**, successor `/usr/local/etc/suricata/conf.d` (`CHANGELOG:community/26.1/26.1:121`). The evidence would be a file on disk, not `config.xml`; out of reach for an API or config-export inspector. Not investigated further.
- **Google Drive backup moved to `os-gdrive-backup` (25.7)** "for existing users" with a conditional upgrade hook (`CORE@25.1:src/etc/rc.syshook.d/upgrade/20-gdrive-plugin.php`, contents not read). Upstream says "Deprecated ... due to upstream policy changes" (`CHANGELOG:community/25.7/25.7:109`). No preferred successor is named, so it does not fit "legacy with a preferred successor". Config paths not examined.
- **Merged privilege `page-system-usermanager-addprivs` (26.7)** (`CHANGELOG:community/26.7/26.7:97`). The string does not occur anywhere in core at the tag, and no migration that strips it from stored users or groups was found by that search. Whether stale privilege names persist in upgraded configs is unconfirmed. Relevant to the least-privilege API user ticket more than to this one.
- **Removal dates.** No upstream statement gives a removal version for any of candidates 1 to 5. The roadmap page was read through a summarising fetch, not raw.
- **ACL coverage of `api/firewall/migration/*`.** No pattern found at the tag; behaviour for a restricted API user must be checked on the probe VM.
- **Prevalence.** No primary data exists in the sources read. All prevalence statements above are structural inferences from factory defaults and the absence of automatic migration.
- **Nothing here was exercised on a running 26.7.4 system.** Endpoint shapes, the direct-URL access to `firewall_nat_out.php` on a clean box, and config-restore behaviour are read from source only.

## Notes for whoever designs the detector

- Candidates 1 to 5 share one shape: legacy config section present, optional GUI plugin, no automatic migration. Candidates 3 to 5 add a second axis that 1 and 2 do not have: without the plugin the legacy config is **inactive**, not merely uneditable. That is a health fact and should be reported separately from the `legacy_supported` status.
- Upstream's own predicates are available for each and can be cited as the detector's definition: `Menu.php:51-53` (rules, outbound NAT), `dhcpd.inc:52-93` (ISC), the 25.1 upgrade hooks (OpenVPN, IPsec "active"), `openvpn.inc:49-55` and `ipsec.inc:138-144` (runs or not).
- Config export is sufficient for the status of all of 1 to 5. The API alone is sufficient for 1 and 2 (counts), partially for 3 and 4 (section presence, package list), and weak for 5.
