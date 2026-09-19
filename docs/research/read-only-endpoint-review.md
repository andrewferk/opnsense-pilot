# Read-only endpoint review for the v1 inventory

Research for [issue #10](https://github.com/andrewferk/opnsense-pilot/issues/10). Done on **2026-09-19** by reading controller, ACL, configd and script source at the pinned tags. Nothing here was run against a live OPNsense; every classification is a source-reading result that the lab probe still has to confirm.

**Provisional target** (a research recommendation from [issue #3](https://github.com/andrewferk/opnsense-pilot/issues/3), not yet an owner decision): OPNsense Community 26.7.4.

| Repo | Tag | Tag object | Commit (verified with `gh api .../git/ref/tags/26.7.4`, then dereferenced) |
| --- | --- | --- | --- |
| `opnsense/core` | `26.7.4` | `4b70db4090faca26f2854752535e5958410cff32` | `ace3b5b5f856261f77b71bd54f3fe63fa2447a12` |
| `opnsense/plugins` | `26.7.4` | `d4d67cd58cbd1ad1b5282467f0d7ed0ac3057ab4` | `6cb23d364671d7d409f2e9e9a14987efcc8ccc7e` |

**Citation convention.** Unless a full URL is given, a citation like `controllers/OPNsense/Core/Api/FirmwareController.php:96-107` is relative to `src/opnsense/mvc/app/` in `opnsense/core` at commit `ace3b5b`, i.e. `https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/<path>#L96-L107`. Paths starting with `service/` or `scripts/` are relative to `src/opnsense/`. Plugin paths are relative to `opnsense/plugins` at `6cb23d3`.

## Summary

- **43 allowlist entries proposed**: 32 SAFE, 11 SAFE-WITH-CAVEAT. 8 further candidates are EXCLUDED. 42 of the 43 are plain `GET`; only the paged log query needs `POST`.
- **Use GET wherever possible.** On this release the search actions read their paging parameters with `request->get()` (model searches) or fall back to defaults (recordset searches), so they answer a body-less GET with all rows. Almost every mutating action in the reviewed controllers is gated on `isPost()`, so a GET-only client is structurally unable to reach them. "POST is used for searches" is true of the GUI, not a requirement of the API. One trap: an API-key GET must not send `Content-Type: application/json` with an empty body, or the request is rejected with 400 (`controllers/OPNsense/Base/ApiControllerBase.php:244-250`).
- **The installed version is available without touching a mirror**: `GET /api/diagnostics/system/system_information` (configd `firmware product`, which reads `/usr/local/opnsense/version/core` and local tools only). `GET /api/core/firmware/status` is equally local, but the **same path with POST** runs a synchronous mirror check, and `GET /api/core/firmware/info` always runs `pkg update -q` against the mirror. `POST /api/core/firmware/check` is the explicit remote check.
- **ACLs cannot be trusted to make a user read-only.** Privileges are URL-prefix patterns with no notion of HTTP method (`models/OPNsense/Core/ACL.php:202-211`), and most are controller-wide (`api/firewall/filter/*`), so the privilege that grants a read also grants the writes next to it. The `user-config-readonly` privilege only takes effect where a controller calls `throwReadOnly()`: the shared model `save()` and about a dozen custom actions. It does **not** cover configd-driven mutations (service start/stop/restart, firmware update, log clear, lease delete, ARP flush, interface reload, state kill). At this tag `POST /api/interfaces/assignment/reconfigure` even calls `Config::getInstance()->save()` directly with no `throwReadOnly()`. The 26.7.1 fix GHSA-vw8q-pqq7-2q7v (commit `f580358f`) patched six such gaps, which shows the guard is opt-in per action, not systemic. **The client-side typed allowlist (exact method + exact path + fixed payload) is the primary control; the OPNsense-side privileges are defence in depth.**
- **Response secrets are the main caveat class.** Several clean reads return secrets: WireGuard server `privkey` and peer `psk`, CARP VIP `password`, Kea subnet `ddns_domain_key_secret`, possibly a GeoIP URL with a licence key. The adapter must redact at the boundary.
- **Logs are the riskiest category.** The paged log read is `POST /api/diagnostics/log/core/<scope>`; the same prefix with `/clear` appended wipes the log, is granted by the same privilege, and is not blocked by `user-config-readonly`.
- **API-invisible categories** (candidate config-export or SSH gaps): per-interface IP configuration (`interfaces.php`), legacy outbound NAT rules for any non-admin user, scrub/normalization rules, schedules, ISC DHCP server configuration, general system settings (DNS servers, `system_general.php`, `system_advanced_*`), PPP, NTP, auth servers. Gateway groups have an API but its ACL pattern appears not to match the real URL, so a least-privilege user is probably locked out (lab check needed).

### Classification key

- **SAFE**: for the pinned method, path and payload the handler writes no config and starts no mutating job. It may run read-only configd jobs (a root-owned script such as `pfctl`/`ifconfig` wrappers, logged in the configd log) and may populate configd's or the model's temp-file caches.
- **SAFE-WITH-CAVEAT**: the pinned call is read-only, but something adjacent is dangerous: the same path mutates under another verb or suffix, the read needs POST, a caller-supplied path segment exists, the response carries secrets, or the ACL looks broken.
- **EXCLUDE**: contacts a remote host, or needs `page-all`, or is otherwise not fit for v1.

"ACL blast radius" lists what else the granting privilege lets that user do. It matters only if the allowlist is bypassed, but it decides how much the OPNsense-side account can be locked down.

### Proposed allowlist

Fixed payload for every GET: **no query string, no body, no `Content-Type` header** unless stated. Rows marked `+v6` have an identical `dhcpv6`/`leases6` twin.

| # | Category | Method and path | Class | Granting privilege (pattern) | ACL blast radius | Side effects of the pinned call |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Version | `GET /api/diagnostics/system/system_information` | SAFE | `page-system-login-logout` "Lobby: Dashboard" (exact `api/diagnostics/system/system_information`) | Dashboard widgets only, incl. `api/core/dashboard/*` (saves the user's own widget layout; `product_info_feed` fetches the forum RSS) | configd `firmware product` + `system openssl version`; local only |
| S2 | System | `GET /api/diagnostics/system/system_time` | SAFE | same privilege (exact pattern) | same | configd `system sysctl values`; also returns last config-change time |
| S3 | System status | `GET /api/core/system/status` | SAFE | `page-system-status` (`api/core/system/status*`) | `dismiss_status` (POST) | configd `system status` (status collectors) |
| S4 | Firmware status | `GET /api/core/firmware/status` | CAVEAT | `page-system-firmware-manualupdate` (`api/core/firmware/*`) | **update, upgrade, reboot, poweroff, install/remove packages**, none guarded by `user-config-readonly` | GET: `firmware product` only, returns cached last check from `/tmp/pkg_upgrade.json`. **POST on the same path contacts the mirror.** Prefer S1 and do not grant this privilege |
| I1 | Interfaces (runtime) | `GET /api/interfaces/overview/interfaces_info/1` | SAFE | `page-status-interfaces` (`api/interfaces/overview/*`) | `reload_interface` (POST, reconfigures an interface) | configd `interface list ifconfig`, `routes list -n json`, `address`, `list stats` |
| I2 | Interface assignments (MVC) | `GET /api/interfaces/assignment/search_item` | SAFE | `page-interfaces-assignnetworkports` (`api/interfaces/assignment/*`) | add/set/del (guarded), **`reconfigure` POST saves config with no read-only guard** | model read |
| I3 | VLANs | `GET /api/interfaces/vlan_settings/search_item` | SAFE | `page-interfaces-vlan-edit` | writes (guarded by `save()`), reconfigure (POST) | model read |
| I4 | Virtual IPs | `GET /api/interfaces/vip_settings/search_item` | CAVEAT | `page-firewall-virtualipaddress-edit` | as I3 | model read; **rows include CARP `password`** |
| I5 | LAGG | `GET /api/interfaces/lagg_settings/search_item` | SAFE | `page-interfaces-lagg-edit` | as I3 | model read |
| I6 | Bridges | `GET /api/interfaces/bridge_settings/search_item` | SAFE | `page-interfaces-bridge-edit` | as I3 | model read |
| F1 | Firewall rules | `GET /api/firewall/filter/search_rule` | SAFE | `page-filter-api` (`api/firewall/filter/*`) | all rule writes (guarded), `apply` POST = filter reload (not guarded) | model read + configd `filter list non_mvc_rules` (cached 60 s): returns MVC, legacy and automatic rules in one list. Do not send `interface` or `show_all` |
| F2 | Source NAT rules | `GET /api/firewall/source_nat/search_rule` | SAFE | `page-filter-snat-api` (`api/firewall/source_nat/*`) | as F1 | model read + configd `filter list automatic_source_nat` (cached 60 s) when mode is automatic/hybrid |
| F3 | Source NAT mode | `GET /api/firewall/source_nat/get` | SAFE | same | as F1 | model read (general settings only) |
| F4 | Destination NAT | `GET /api/firewall/d_nat/search_rule` | SAFE | `page-firewall-nat-portforward-edit` (`api/firewall/d_nat/*`) | as F1 | model read + configd `filter list automatic_destination_nat` (cached 60 s) |
| F5 | 1:1 NAT | `GET /api/firewall/one_to_one/search_rule` | SAFE | `page-firewall-nat-1-1-edit` | as F1 | model read |
| F6 | NPTv6 | `GET /api/firewall/npt/search_rule` | SAFE | `page-firewall-nat-npt` | as F1 | model read |
| F7 | Aliases (config) | `GET /api/firewall/alias/search_item` | SAFE | `page-firewall-aliases` (**read-scoped**: `alias/search*`, `get*`, `list*`, `export`) | none beyond reads | model read |
| F8 | Aliases (full dump) | `GET /api/firewall/alias/export` | CAVEAT | same | same | model read, raw values; includes the `geoip` node whose URL can embed a licence key |
| F9 | Alias tables (runtime) | `GET /api/firewall/alias_util/aliases` | SAFE | `page-diagnostics-tables` (`api/firewall/alias_util/*`) | add/delete/flush table entries (POST; guarded since 26.7.1) | configd `filter list tables` |
| F10 | Alias table contents | `GET /api/firewall/alias_util/list/{alias}` | CAVEAT | same | same | configd `filter list table <alias>`; **caller-supplied path segment**, must be validated against F9 output |
| F11 | Interface groups | `GET /api/firewall/group/search_item` | SAFE | `page-interfaces-groups-edit` | writes (guarded), reconfigure POST | model read |
| F12 | Categories | `GET /api/firewall/category/search_item` | SAFE | `page-firewall-rules` and others (`api/firewall/category/search_item*`, read-scoped) | none | model read |
| G1 | Gateways (config + status) | `GET /api/routing/settings/search_gateway` | SAFE | `page-system-gateways` (`api/routing/settings/*`) | writes (guarded), reconfigure POST | model read + configd `interface list ifconfig`, `interface gateways status` |
| G2 | Gateway status | `GET /api/routes/gateway/status` | SAFE | `page-system-gateways` (exact pattern) | as G1 | configd `interface gateways status` |
| G3 | Gateway groups | `GET /api/routing/group_settings/search` | CAVEAT | `page-system-gatewaygroups`, **but its pattern is `api/routing/groupsettings/*`** | n/a | model read + configd `interface gateways status`. Pattern does not match the real URL, so expect 403 without `page-all`; verify in the lab |
| R1 | Static routes (configured) | `GET /api/routes/routes/searchroute` | SAFE | `page-system-staticroutes` (`api/routes/*`) | writes (guarded), reconfigure POST | model read |
| R2 | Routing table (runtime) | `GET /api/diagnostics/interface/get_routes` | SAFE | `page-diagnostics-routingtables` (**read-scoped**: `get_routes*`) | none | configd `interface routes list -n json`. Never send `resolve` (turns on reverse DNS) |
| V1 | Services | `GET /api/core/service/search` | SAFE | `page-status-services` (`api/core/service/*`) | **start/stop/restart any service (POST, not guarded)** | configd `service list` (`pluginctl -S`) |
| D1 | Unbound config | `GET /api/unbound/settings/get` | SAFE | `page-services-unbound` (`api/unbound/*`) | writes (guarded), service control and DNSBL reload (POST, not guarded), cache/stat resets | model read (whole model: general, advanced, overrides, forwards, ACLs, DNSBL) |
| D2 | dnsmasq config (DNS + DHCP) | `GET /api/dnsmasq/settings/get` | SAFE | `page-services-dnsforwarder` (`api/dnsmasq/*`) | writes (guarded), service control (POST) | model read (whole model: hosts, domains, ranges, options, tags, boot) |
| H1 | Kea general `+v6` | `GET /api/kea/dhcpv4/get` | SAFE | `page-dhcp-kea-v4` (`api/kea/dhcpv4/*`, `leases4/*`, `service/*`) | writes (guarded), **lease delete and service control (POST, not guarded)** | model read (general, lexpire, ha only) |
| H2 | Kea subnets `+v6` | `GET /api/kea/dhcpv4/search_subnet` | CAVEAT | same | same | model read; **rows include `ddns_domain_key_secret`** |
| H3 | Kea reservations `+v6` | `GET /api/kea/dhcpv4/search_reservation` | SAFE | same | same | model read |
| H4 | Kea leases `+v6` | `GET /api/kea/leases4/search` | SAFE | same | same | configd `kea list leases4`: queries the Kea control socket (`config-get`, lease get) + `interface list macdb` |
| H5 | dnsmasq leases | `GET /api/dnsmasq/leases/search` | SAFE | `page-services-dnsforwarder` | as D2 | configd `dnsmasq list leases` (reads `/var/db/dnsmasq.leases`), `interface list ifconfig`, `list macdb` |
| H6 | ISC leases (plugin `os-isc-dhcp`) | `GET /api/dhcpv4/leases/search_lease` | SAFE | `page-status-dhcpleases` (`api/dhcpv4/leases/*`) | `del_lease` (POST, not guarded) | configd `dhcpd list leases/static/arp`. Only exists when the plugin is installed; 404 otherwise |
| W1 | WireGuard general | `GET /api/wireguard/general/get` | SAFE | `page-wireguard-config` | writes (guarded), service control (POST) | model read |
| W2 | WireGuard instances | `GET /api/wireguard/server/search_server` | CAVEAT | `page-wireguard-config` | same | model read; **rows include `privkey`** |
| W3 | WireGuard peers | `GET /api/wireguard/client/search_client` | CAVEAT | `page-wireguard-config` | same | model read; **rows include `psk`** |
| W4 | WireGuard status | `GET /api/wireguard/service/show` | SAFE | `page-wireguard-diagnostics` (`api/wireguard/service/*`) | start/stop/restart/reconfigure (POST, not guarded) | configd `wireguard show` (`wg show all dump`; script strips private and preshared keys) |
| L1 | Logs (paged) | `POST /api/diagnostics/log/core/{scope}` body `{"current":1,"rowCount":500,"searchPhrase":"","severity":"","validFrom":"0"}` | CAVEAT | one privilege per scope, e.g. `page-diagnostics-logs-system` (`api/diagnostics/log/core/system/*`) | **`POST .../{scope}/clear` wipes the log (not guarded)** | configd `system diag log` (`queryLog.py`). Needs POST. `{scope}` from a fixed enum; path must have no trailing segment |
| L2 | Logs (stream) | `GET /api/diagnostics/log/core/{scope}/export?validFrom=<epoch>` | CAVEAT | same | same | configd stream `system diag log_stream`; GET-only but unpaged (whole log since `validFrom`) |
| E1 | Config export (gap filler) | `GET /api/core/backup/download/this` | CAVEAT | `page-diagnostics-configurationhistory` (`api/core/backup/*`) | delete/revert backup (POST, guarded by `throwReadOnly()`) | streams the newest `config-*.xml` from the backup directory. **Contains every secret on the box.** Not inventory; listed for the export/SSH gap decision |

### Excluded

| Candidate | Why |
| --- | --- |
| `POST /api/core/firmware/status` | Runs `firmware probe` synchronously before answering: `launcher.sh check`, i.e. contacts the mirror |
| `POST /api/core/firmware/check` | Spawns the background update check (`daemon -f launcher.sh check`) |
| `GET /api/core/firmware/info` | Unconditionally runs configd `firmware remote` and `firmware tiers`, both `pkg update -q && pkg rquery` (mirror contact, updates the local pkg catalogue) |
| `GET /api/core/dashboard/product_info_feed` | `curl` to `forum.opnsense.org`. Proof that GET does not mean local |
| `GET /api/firewall/migration/{count_rules,download_rules,count_outbound,download_outbound}` | Read-only, but **no ACL pattern covers `api/firewall/migration/*`**, so only `page-all` users reach it |
| any read with `resolve=yes` (`get_routes`, `get_arp`) | Triggers reverse DNS lookups |
| `GET /api/wireguard/client/psk`, `GET /api/wireguard/server/key_pair` | Generate key material; harmless but pointless |
| Firewall live log (`api/diagnostics/firewall/log`, `stream_log`) | Not reviewed; out of time box. Use L1 with scope `filter`/`firewall` |

## Evidence

### 1. How the API layer decides what is allowed

- **Routing.** `/api/<module>/<controller>/<action>/<params...>`; each segment is converted snake_case to CamelCase, the controller gets `Controller` appended and the action `Action` (`library/OPNsense/Mvc/Router.php:183-192`). The controller file is looked up by exact file name (`Router.php:90-99`); only the namespace directory has a case-insensitive fallback (`Router.php:78-89`). Hence `GroupSettingsController` is `group_settings`, never `groupsettings`.
- **Authentication and ACL.** For API-key requests `beforeExecuteRoute` authenticates, then calls `ACL::isPageAccessible($user, $_SERVER['REQUEST_URI'])` and returns 403 on a miss (`controllers/OPNsense/Base/ApiControllerBase.php:286-335`). `urlMatch` turns the pattern into a regex where `*` is the only wildcard and matches `^/<pattern>$` (`models/OPNsense/Core/ACL.php:202-211`). The HTTP method is never consulted. A URL no pattern covers is reachable only through `page-all`.
- **`user-config-readonly`.** Defined as "System: Deny config write" (`models/OPNsense/Core/ACL/ACL.xml:2-4`). Enforced only by `throwReadOnly()` (`ApiControllerBase.php:46-57`). Call sites at this tag: the shared `save()` (`controllers/OPNsense/Base/ApiMutableModelControllerBase.php:327-342`) and custom actions in `CaptivePortal/TemplateController`, `Core/BackupController` (141, 160), `Core/DefaultsController`, `Firewall/AliasUtilController` (106, 123, 170), `Firewall/MigrationController` (66, 94), `OpenVPN/ExportController`, `IPsec/ConnectionsController`, `Diagnostics/NetflowController`, `Trust/CrlController`, `Unbound/SettingsController` (48). `Config.php` itself contains no read-only check, so any action that calls `Config::getInstance()->save()` directly is unguarded.
- **The 26.7.1 fix.** Changelog: "mvc: safeguard some write operations with missing throwReadOnly() actions for custom action (reported by lujiefsi)", GHSA-vw8q-pqq7-2q7v ([changelog 26.7.1, line 28](https://github.com/opnsense/changelog/blob/e38c5c2f6d517267f4b6efb8fc7e742521fdf485/community/26.7/26.7.1#L28)). Commit [`f580358f`](https://github.com/opnsense/core/commit/f580358f9cf8219d3b4eb26262e5c1b3eaa4468d) (2026-07-20) adds the call in six controllers: Netflow, AliasUtil, IPsec Connections, OpenVPN Export, Trust CRL, Unbound Settings. It is a per-action patch, not a framework change.
- **Still unguarded at 26.7.4 (source reading).** `AssignmentController::reconfigureAction` runs `interface apply`, edits `interfaces` and calls `Config::getInstance()->save()` with no `throwReadOnly()` (`controllers/OPNsense/Interfaces/Api/AssignmentController.php:140-166`). All configd-only mutations are unguarded by design: `Core/Api/SystemController.php:42-59` (halt, reboot), `Core/Api/ServiceController.php:71-79` (start), `ApiMutableServiceControllerBase.php:101-142, 186-227` (start/stop/restart/reconfigure), `Diagnostics/Api/LogController.php:53-56` (clear log), `Kea/Api/LeasesController.php:118-126` (delete lease), `Interfaces/Api/OverviewController.php:298-312` (reload interface).
- **POST gating.** All of the mutators above, and the base `setAction`, `addBase`, `delBase`, `setBase`, `toggleBase` (`ApiMutableModelControllerBase.php:395, 505, 548, 592, 644`), check `isPost()` first. `getAction` answers only GET (`:204-212`).
- **GET works for searches.** `searchBase` reads `searchPhrase` with `request->get()` (`ApiMutableModelControllerBase.php:447`) and `UIModelGrid::fetchBindRequest` reads `rowCount` (default -1 = all) and `current` with `request->get()` (`models/OPNsense/Base/UIModelGrid.php:69-70`). `searchRecordsetBase` reads `rowCount` from POST with a default of 9999 rows (`ApiControllerBase.php:94-97`), so a GET returns up to 9999 rows unfiltered. If POST is preferred anyway, the fixed payload is `{"current":1,"rowCount":-1,"searchPhrase":""}`.
- **What a "pure read" still touches.** Loading a model only parses `config.xml` and runs `init()`; it does not run migrations or write (`models/OPNsense/Base/BaseModel.php:451-513`). `getCachedData()` may write `mdl_cache_*.json` in the temp dir (`BaseModel.php:407-432`). configd `script_output` actions with `cache_ttl` write a temp file and reuse it until expiry (`service/modules/actions/script_output.py:53-90`); a leading `!` on the command flushes that cache first (`service/modules/processhandler.py:166-179`). Each configd call is a root-executed script and is logged.

### 2. System and firmware

- `systemInformationAction` runs configd `firmware product` and `system openssl version`, reads hostname/domain from config, and returns `versions[0] = "<name> <version>-<arch>"` (`controllers/OPNsense/Diagnostics/Api/SystemController.php:90-130`). `systemTimeAction`: `:132-155`.
- `firmware product` is `scripts/firmware/product.php` (`service/conf/actions.d/actions_firmware.conf:219-223`). It reads `/usr/local/opnsense/version/core`, runs `latest.php` (compares against the on-disk `/usr/local/opnsense/changelog/index.json`, `scripts/firmware/latest.php:32-50`), `opnsense-update -M`, `opnsense-verify -l`, `opnsense-update -G`, and embeds the last check result from `/tmp/pkg_upgrade.json` (`scripts/firmware/product.php:32-45`). No network call is visible in these scripts; `opnsense-update -M/-G` and `opnsense-verify -l` are external binaries not read here (assumed to print local settings).
- `statusAction`: "run a synchronous check prior to the result fetch" only `if ($this->request->isPost())`, via configd `firmware probe`; GET goes straight to `firmware product` (`controllers/OPNsense/Core/Api/FirmwareController.php:96-109`). `probe` = `launcher.sh check` (`actions_firmware.conf:7-11`).
- `checkAction` requires POST and starts `firmware check` in the background (`FirmwareController.php:77-90`; `actions_firmware.conf:1-5`).
- `infoAction` has no verb check and always runs `firmware tiers`, `firmware remote`, `firmware local` (`FirmwareController.php:801-840`). `remote` and `tiers` are `pkg update -q && pkg rquery ...` (`scripts/firmware/query.sh:57-63`; `actions_firmware.conf:201-217`).
- Privilege: `page-system-firmware-manualupdate` covers `api/core/firmware/*` (`models/OPNsense/Core/ACL/ACL.xml:512-520`), which includes `update`, `upgrade`, `reboot`, `poweroff`, `install`, `remove` (`FirmwareController.php:421-740`).
- `Core/Api/SystemController::statusAction` runs configd `system status` with the optional `path` request parameter (`controllers/OPNsense/Core/Api/SystemController.php:62-80`); the script only dismisses when called as `dismiss <subject>`, which needs two arguments and the action template passes one (`scripts/system/status.php:34-38`; `service/conf/actions.d/actions_system.conf:178-182`). Pin the call with no `path`. ACL: `ACL.xml:40-46`.
- Dashboard privilege patterns: `ACL.xml:11-27`. `productInfoFeedAction` curls the forum: `controllers/OPNsense/Core/Api/DashboardController.php:196-201`.

### 3. Interfaces

- Runtime overview: `interfacesInfoAction($details)` and `exportAction` both call `parseIfInfo`, which runs configd `interface list ifconfig`, `interface routes list -n json`, `interface address`, and (with details) `interface list stats` (`controllers/OPNsense/Interfaces/Api/OverviewController.php:116-122, 246-253, 314-319`). Those are `pluginctl -D`, `show_routes.py`, `pluginctl -46`, `pluginctl -I` (`service/conf/actions.d/actions_interface.conf:14-18, 117-127, 147-151`). ACL `api/interfaces/overview/*`: `ACL.xml:369-375`.
- Assignments (MVC since 26.7): `searchItemAction` = `searchBase("interface")` on `OPNsense\Interfaces\NetworkInterface` (`controllers/OPNsense/Interfaces/Api/AssignmentController.php:36-44`). ACL: `ACL.xml:288-294`.
- VLAN/VIP/LAGG/bridge search actions: `VlanSettingsController.php:83`, `VipSettingsController.php:108-119`, `LaggSettingsController.php:58-60`, `BridgeSettingsController.php:48-50`. ACLs: `models/OPNsense/Interfaces/ACL/ACL.xml` (VIP 16-22, VLAN 46-52, LAGG 53-59) and `Core/ACL/ACL.xml:295-301` (bridge). GIF, GRE, loopback, VXLAN, wireless and neighbor controllers follow the same base-class pattern but were not read individually.
- VIP secret: `<password type="TextField"/>` (`models/OPNsense/Interfaces/Vip.xml:35`); `searchBase` with `$fields = null` returns every field of the node (`ApiMutableModelControllerBase.php:431-445`).
- **Gap:** per-interface settings (IPv4/IPv6 mode, static addresses, MTU, block-private) are still the legacy page `src/www/interfaces.php`; there is no controller for them under `controllers/OPNsense/Interfaces/Api/`. The API shows the resulting runtime addresses (I1) but not the configured intent. PPP is likewise legacy (`src/www/interfaces_ppps*.php`).

### 4. Firewall rules, NAT, aliases

- `FilterController::searchRuleAction` merges MVC rules with configd `filter list non_mvc_rules` ("always fetch internal and legacy rules"), and only queries `filter rule stats` when `show_all` is set (`controllers/OPNsense/Firewall/Api/FilterController.php:84-216`, merge at 186-190). configd: `service/conf/actions.d/actions_filter.conf:207-211` (cache 60 s), `:128-132` (stats, cache 300 s). With `show_all` plus an IP in `searchPhrase` it also runs `filter find_table_references` (`:194-206`); the pinned call sends neither.
- `POST /api/firewall/filter_util/rule_stats` and `flush_inspect_cache` use the `!` prefix to flush the configd cache (`FilterUtilController.php:43-45`, `FilterController.php:414-420`); not needed for inventory.
- `applyAction` reloads the filter on POST with no read-only guard (`controllers/OPNsense/Firewall/Api/FilterBaseController.php:309-313`).
- Source NAT: `getAction` returns only `general` (`SourceNatController.php:56-63`, matching the 26.7/26.7.2 changelog notes), `searchRuleAction` adds automatic rules from configd `filter list automatic_source_nat` when the mode is automatic or hybrid (`:65-67, 120-162`; `actions_filter.conf:69-73`). Destination NAT does the same with `automatic_destination_nat` (`DNatController.php:50, 144-180`; `actions_filter.conf:76-80`). 1:1 and NPT are plain model searches (`OneToOneController.php:35-57`, `NptController.php:35`).
- ACLs: `models/OPNsense/Firewall/ACL/ACL.xml:2-29` (filter, source_nat, npt, one_to_one), `Core/ACL/ACL.xml:215-221` (d_nat).
- **Legacy outbound NAT** (`nat.outbound.rule`, coexisting with source NAT in 26.7) is exposed only by `MigrationController` (`download_outbound`, `count_outbound`, configd `filter list legacy_outbound_nat`; `controllers/OPNsense/Firewall/Api/MigrationController.php:42-45, 76-88`). No ACL file contains a `firewall/migration` pattern (grep over `models/OPNsense/*/ACL/ACL.xml`), so it needs `page-all`. The legacy pages `src/www/firewall_nat_out.php` and `firewall_nat_out_edit.php` still ship in core. Legacy filter rules, by contrast, are visible through F1.
- Aliases: `searchItemAction` (`AliasController.php:51-60`), `exportAction` answers GET with raw node values for the whole model (`:373-398`), `getGeoIPAction` (`:466-497`), `getTableSizeAction` (`:348-351`). The read-scoped privilege `page-firewall-aliases` is at `Core/ACL/ACL.xml:185-194`; note `get*` also matches `get_geo_i_p` and `get_table_size`. Runtime tables: `AliasUtilController.php:76-96`; ACL `:110-116`.
- **Gaps:** scrub/normalization (`src/www/firewall_scrub*.php`) and schedules (`src/www/firewall_schedule*.php`) are legacy pages with no API controller.

### 5. Gateways, gateway groups, routes

- `searchGatewayAction` reads the gateway model and merges configd `interface list ifconfig` and `interface gateways status` (`controllers/OPNsense/Routing/Api/SettingsController.php:54-60`); `GatewayController::statusAction` is the status alone (`controllers/OPNsense/Routes/Api/GatewayController.php:40-44`). configd `gateways.status` = `gateway_status.php` (`actions_interface.conf:180-183`). ACL: `Core/ACL/ACL.xml:521-528`.
- Gateway groups (MVC since 26.7): `GroupSettingsController::searchAction` (`controllers/OPNsense/Routing/Api/GroupSettingsController.php:53-90`). The GUI calls `/api/routing/group_settings/search` (`views/OPNsense/Routing/groups.volt:30-34`), but the privilege pattern is `api/routing/groupsettings/*` (`Core/ACL/ACL.xml:529-535`). Given the router's exact file-name lookup, `groupsettings` cannot resolve to `GroupSettingsController.php` on a case-sensitive filesystem, and `group_settings` does not match the pattern. Expected result: 403 for any user without `page-all`. The 26.7.4 changelog's "acl: add missing and fix some issues" did not fix this one. Lab check; possible upstream report.
- Configured static routes: `searchrouteAction` (`controllers/OPNsense/Routes/Api/RoutesController.php:49-52`), ACL `api/routes/*` (`Core/ACL/ACL.xml:555-561`). Runtime table: `getRoutesAction` uses `-n` unless `resolve` is sent (`controllers/OPNsense/Diagnostics/Api/InterfaceController.php:160-184`); read-scoped ACL `get_routes*` (`models/OPNsense/Diagnostics/ACL/ACL.xml:30-36`).

### 6. Services

- `searchAction` runs configd `service list` and maps `is running` to `running: 1` (`controllers/OPNsense/Core/Api/ServiceController.php:44-63`). configd: `pluginctl -S` (`service/conf/actions_service.conf:13-17`). ACL `api/core/service/*` (`Core/ACL/ACL.xml:383-389`) also covers `start`, `restart`, `stop` (`ServiceController.php:71-120`).
- Per-service `GET /api/<module>/service/status` (`ApiMutableServiceControllerBase.php:234-261`) is equally read-only but redundant with V1.

### 7. DNS and DHCP

- Unbound: `SettingsController` extends the mutable model base, so `GET /api/unbound/settings/get` returns the whole `OPNsense\Unbound\Unbound` model (`controllers/OPNsense/Unbound/Api/SettingsController.php:36-39`; base `getAction`). The narrower Unbound privileges only list specific override actions (`models/OPNsense/Unbound/ACL/ACL.xml:23-46`); `settings/get` needs `page-services-unbound` = `api/unbound/*` (`:54-60`). Optional runtime reads under the same privilege: `GET /api/unbound/diagnostics/stats`, `listlocaldata`, `listlocalzones` (`DiagnosticsController.php:45-99`, all `unbound-control` read wrappers, `actions_unbound.conf:13-17, 74-78`). `GET /api/unbound/settings/get_nameservers` runs `system list nameservers` (`SettingsController.php:114-124`) and is the only API view of the system's DNS servers.
- dnsmasq (DNS and DHCP in one model): `getAction` (`controllers/OPNsense/Dnsmasq/Api/SettingsController.php:76-84`), leases `searchAction` (`Dnsmasq/Api/LeasesController.php:39-48`; script reads `/var/db/dnsmasq.leases`, `scripts/dnsmasq/get_dnsmasq_leases.py:36-48`). ACL `api/dnsmasq/*` (`models/OPNsense/Dnsmasq/ACL/ACL.xml`).
- Kea: `getAction` returns only `general`, `lexpire`, `ha` (`controllers/OPNsense/Kea/Api/Dhcpv4Controller.php:44-57`), so subnets and reservations need `search_subnet` (`:59-62`) and `search_reservation` (`:95-98`). Subnet secret: `ddns_domain_key_secret` (`models/OPNsense/Kea/KeaDhcpv4.xml:228`, same in `KeaDhcpv6.xml:201`). Leases: `LeasesController::searchAction` runs `kea list leases4` (`Kea/Api/LeasesController.php:40-57`, `Leases4Controller.php:33`), which sends `config-get` and a lease query to the Kea control socket (`scripts/kea/get_kea_leases.py:117-125`). ACL: `models/OPNsense/Kea/ACL/ACL.xml`.
- ISC DHCP is no longer in core. It is the plugin `net/isc-dhcp` (`os-isc-dhcp`): leases via `DHCPv4/Api/LeasesController.php:38-59` (`search_lease`), ACL `api/dhcpv4/leases/*` ([plugin ACL.xml](https://github.com/opnsense/plugins/blob/6cb23d364671d7d409f2e9e9a14987efcc8ccc7e/net/isc-dhcp/src/opnsense/mvc/app/models/OPNsense/DHCPv4/ACL/ACL.xml)). **Gap:** its configuration is legacy pages only (`net/isc-dhcp/src/www/services_dhcp*.php`), no API.

### 8. WireGuard

- Config: `searchServerAction` = `searchBase('servers.server')` (`controllers/OPNsense/Wireguard/Api/ServerController.php:45-48`), `searchClientAction` (`ClientController.php:63-71`), general via base `getAction` (`GeneralController.php:34-38`). Secrets in the returned rows: `privkey` (`models/OPNsense/Wireguard/Server.xml:22`), `psk` (`models/OPNsense/Wireguard/Client.xml:30`).
- Status: `showAction` runs configd `wireguard show` and joins names from the models (`Wireguard/Api/ServiceController.php:69-110`). The script runs `wg show all dump` and deliberately drops the private and preshared keys (`scripts/wireguard/wg_show.py:38-58`; `service/conf/actions.d/actions_wireguard.conf:47-51`).
- ACL: `models/OPNsense/Wireguard/ACL/ACL.xml` (`page-wireguard-config`, `page-wireguard-diagnostics`, `page-wireguard-logs`).

### 9. Logs

- One magic controller: `LogController::__call` takes `/api/diagnostics/log/<module>/<scope>[/<action>]`. POST + action `clear` runs `system clear log`; any other POST runs the paged query `system diag log` with `rowCount` (default 5000, capped 9999), `current`, `searchPhrase`, `severity`, `validFrom`; GET serves only `export` (CSV stream) and `live` (SSE) (`controllers/OPNsense/Diagnostics/Api/LogController.php:39-110`). configd: `service/conf/actions.d/actions_system.conf:8-18, 35-38`.
- Privileges are per scope and end in `/*`, so each one covers `clear` too: e.g. system/audit/configd/boot/lighttpd (`Core/ACL/ACL.xml:88-102`), gateways (`:81-87`), firewall (`:256-269`), routing (`:411-417`), pkg (`:518`), resolver (Unbound ACL `:47-53`), dnsmasq, kea, wireguard in their module ACL files.
- Consequence: the log entry must be modelled as an enum of scopes, the path must be built by the adapter (never from caller text), and a request whose path has a third segment other than `export` must be unrepresentable in the typed client.

## Gaps and open questions

**Inventory the API cannot see (candidate config-export or SSH reads)**

1. Per-interface configuration (legacy `interfaces.php`), PPP, legacy wireless status page.
2. Legacy outbound NAT rules for a non-admin user (migration endpoints have no ACL pattern).
3. Scrub/normalization rules and schedules.
4. ISC DHCP server configuration (plugin legacy pages); only leases have an API.
5. General system settings: `system_general.php` (DNS servers, timezone), `system_advanced_admin/firewall/misc.php`, auth servers, NTP (`services_ntpd*.php`). Only hostname (S1) and effective nameservers (`unbound/settings/get_nameservers`) leak through.
6. Gateway groups, if the ACL mismatch is confirmed.

E1 (`GET /api/core/backup/download/this`) would close all of these in one call, at the price of pulling every secret in `config.xml` across the wire. That trade-off belongs to the export/SSH gap ticket, not here.

**To validate in the lab probe**

- Every SAFE/CAVEAT row: status 200 with a least-privilege + `user-config-readonly` API user, `config.xml` revision unchanged before/after, no new entries in the audit log beyond the configd read lines, no outbound connections during S1 and `GET` S4 (packet capture on WAN).
- That GET really returns all rows for model searches and up to 9999 for recordset searches, and that an empty-body GET with `Content-Type: application/json` is rejected with 400.
- G3: confirm the 403 for a user holding only `page-system-gatewaygroups`.
- Confirm that a `user-config-readonly` user holding `page-interfaces-assignnetworkports` can still drive `POST /api/interfaces/assignment/reconfigure` to a config save (source says yes). If so, consider reporting upstream; either way it is one more reason not to lean on the flag.
- Confirm `POST /api/diagnostics/log/core/system/clear` succeeds for a `user-config-readonly` user (source says yes). Do this only on the throwaway VM.
- Which exact secret fields appear in I4, H2, W2, W3, F8 responses, to drive the redaction list.
- F1 on a box with legacy `<filter>` rules and with `os-firewall-legacy` absent: do legacy rows appear and how are they marked (`legacy` field)?

**Not verified or not reviewed**

- `opnsense-update -M/-G` and `opnsense-verify -l` are compiled/external tools; their being network-free is assumed from their documented purpose, not read from source. The WAN capture above settles it.
- The status collector classes behind `system status` were not read individually.
- GIF/GRE/loopback/VXLAN/wireless/neighbor settings controllers, the `dhcpv6`/`leases6` twins, the firewall live-log endpoints, IPsec/OpenVPN, `hasync_status`, and the Syslog settings controller were not reviewed.
- Hotfix 26.7.4_1 is untagged; this review is of tag `26.7.4` only.
- The "legacy-only" list is derived from the presence of `src/www/*.php` pages and the absence of an API controller at this tag, not from an exhaustive config.xml section audit.
- Least-privilege set for the full allowlist (derived, to be confirmed): `page-system-login-logout`, `page-system-status`, `page-status-interfaces`, `page-interfaces-assignnetworkports`, the four interface device privileges, `page-filter-api`, `page-filter-snat-api`, `page-firewall-nat-portforward-edit`, `page-firewall-nat-1-1-edit`, `page-firewall-nat-npt`, `page-firewall-aliases`, `page-diagnostics-tables`, `page-interfaces-groups-edit`, `page-system-gateways`, `page-system-gatewaygroups`, `page-system-staticroutes`, `page-diagnostics-routingtables`, `page-status-services`, `page-services-unbound`, `page-services-dnsforwarder`, `page-dhcp-kea-v4`/`v6`, `page-status-dhcpleases` (plugin), `page-wireguard-config`, `page-wireguard-diagnostics`, the per-scope log privileges, plus `user-config-readonly`. Deliberately **not** granted: `page-system-firmware-manualupdate`, `page-diagnostics-configurationhistory`, `page-all`.
