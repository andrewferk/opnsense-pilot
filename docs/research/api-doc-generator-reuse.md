# Can the official API-doc tooling seed the endpoint registry?

Research for [issue #8](https://github.com/andrewferk/opnsense-pilot/issues/8). Researched 2026-09-19.

Pinned refs used throughout (all shallow clones, read as data):

| Repo | Ref | Commit |
| --- | --- | --- |
| [opnsense/docs](https://github.com/opnsense/docs) | `master` | `2c85e8a9ea43f4e008a536734ad428783fae94f9` (2026-09-11) |
| [opnsense/core](https://github.com/opnsense/core) | tag `26.7.4` | `ace3b5b5f856261f77b71bd54f3fe63fa2447a12` |
| [opnsense/plugins](https://github.com/opnsense/plugins) | tag `26.7.4` | `6cb23d364671d7d409f2e9e9a14987efcc8ccc7e` |

`26.7.4` was picked only because it was the newest stable tag on the day; it is an example of "a pinned ref", not a proposal for the compatibility target (that is another ticket's decision).

## Answer

**Yes as a discovery/proposal seed, no as anything the registry may trust. Reuse the generator's *library* (not the published pages) as a cheap cross-check oracle; build the registry's own extractor on Tree-sitter as the handoff baseline already plans.**

- The generator is `collect_api_endpoints.py` + `lib/` in `opnsense/docs`. It is a real parser, not regex: a vendored, patched copy of the `phply` PLY grammar builds a PHP AST, and a ~200-line walker turns every class method named `*Action` into a row. It extracts module, controller, command, URL-path parameters (with defaults), a *guessed* HTTP method, the model XML file, the model container name and a per-action model path. It returns typed pydantic objects, so it can be driven as a library without the RST templating.
- It runs cleanly against a pinned core/plugins checkout. I ran it against core and plugins at tag `26.7.4`: exit 0, 125 core controllers / 937 actions, 222 plugin controllers / 1,477 actions, a few seconds each, only `ply`, `pydantic` and `jinja2` needed. A per-release catalog is therefore practical.
- The **published pages on docs.opnsense.org are not a per-release catalog and are stale**: the site is unversioned, regeneration is a manual, sporadic step (last bulk run 2026-05-13, before 26.7), and regenerating against `26.7.4` adds four whole core controllers and ~30 rows the site does not show. Do not seed from the published output.
- Its **HTTP method column is a heuristic and is unsafe as a read-only signal**: 267 of 937 core actions (28%) get `GET` purely as a fallback because nothing was detected, and that set includes real mutators (`firewall/*/upload_rules`, `move_rule_before`, `toggle_rule_log`, `diagnostics/netflow/setconfig`, `wireguard/client/add_client`).
- It **does not resolve inheritance**: only two base classes are covered, by a hard-coded table, one level deep. Controllers that extend an intermediate class lose inherited actions, and two real read endpoints (`kea/leases4/search`, `kea/leases6/search`) plus the whole `diagnostics/log` controller vanish from the output entirely.
- It extracts nothing about request body/query fields, response shape, ACL privileges, side effects (configd calls, config writes), or which plugin package provides a controller. Those are exactly the fields the registry review needs.
- License is permissive (BSD 2-clause for the script and the docs repo; the vendored `phply` is BSD 3-clause upstream but is vendored without its license file).

Because every registry entry needs human review of semantics and side effects anyway, the generator's value is limited to *enumerating candidates*. Tree-sitter extraction is needed regardless, since the facts a reviewer needs (inherited actions, `isPost` guards in helpers, configd/`Config` write calls, ACL patterns, request field names) are not in the generator's output and adding them means rewriting most of its walker on top of an old, error-recovering grammar. Keeping the upstream library as a second opinion ("does our extractor find at least every module/controller/command upstream finds for this ref?") costs almost nothing and catches extractor regressions.

## Findings

### 1. Where the generator lives and how it is run

- Entry point: [`collect_api_endpoints.py`](https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/collect_api_endpoints.py). Arguments: positional `source` directory, `--repo core|plugins` (only selects the output directory and source-link prefix), `--debug`, `--filter` (lines 40-46).
- Extraction logic: [`lib/__init__.py`](https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/lib/__init__.py) (`ApiParser`, pydantic `Action` / `Controller`), tree walk in [`lib/utils.py`](https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/lib/utils.py), PHP grammar in [`lib/phply/`](https://github.com/opnsense/docs/tree/2c85e8a9ea43f4e008a536734ad428783fae94f9/lib/phply).
- Output template: [`collect_api_endpoints.in`](https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/collect_api_endpoints.in) (Jinja2 to an RST `csv-table` with columns Method, Module, Controller, Command, Parameters, plus a `<<uses>>` row linking the model XML). A module can override the template with `<module>.rst.in` (script lines 85-88); `firewall.rst.in` is the only one for core.
- Documented usage, from the [README](https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/README.md) ("Update API endpoints"): `./collect_api_endpoints.py --repo core /path/to/core/repository`. It is a manual step; it is not wired into the Sphinx `Makefile`.
- History (via `gh api repos/opnsense/docs/commits?path=...`): first added 2020-02-16 (`c0d7a022b2`) as a regex harvester; rewritten 2025-04-29 to 2025-05-05 to use a lexer/parser (`02823b6055`, "uses a lexer now"), `phply` imported from `viraptor/phply` on 2025-04-30 (`12cb1a4e32`) "so we can add some missing language constructs on our end", pydantic typing added in [PR #713](https://github.com/opnsense/docs/pull/713), tree walk split out for reuse in [PR #712](https://github.com/opnsense/docs/pull/712) (whose author states the goal of re-using the parsing code from outside). Last change to the tooling: 2026-01-28 (`935c07c206`). So upstream has deliberately made it consumable as a library, but offers no stability promise.

### 2. What it extracts, and how

All from `lib/__init__.py` at `2c85e8a`:

| Field | How it is derived | Lines |
| --- | --- | --- |
| Files considered | any `*Controller.php` whose path contains `mvc/app/controllers` and whose directory is named `Api`; `Core/Api/FirmwareController.php` is hard-excluded | `lib/utils.py` 5, 19-21 |
| `module` | third-from-last path segment, lowercased (vendor namespace is ignored) | 71 |
| `controller` | file name minus `Controller.php`, CamelCase to snake_case | 70 |
| `command` | every class method whose name ends in `Action`, CamelCase to snake_case. **Visibility is not checked.** | 105-106 |
| `parameters` | the PHP function signature only (positional URL segments) with defaults rendered as text | 107-116 |
| `methods` | heuristic over method calls found anywhere inside the action body: `isPost` gives POST, `isGet` gives GET, `addBase`/`setBase`/`delBase`/`toggleBase`/`setAction` give POST, `searchBase` gives GET+POST. **If nothing is detected: POST when the command is `set`, otherwise GET.** | 119-143 |
| `model_filename` | class property `$internalModelClass`, mapped to `models/<Class>.xml` if that file exists | 80-86 |
| `model_container` | class property `$internalModelName` | 87-88 |
| `model_path` (per action) | the path argument of the `*Base` call (e.g. `snatrules.rule`) | 126-133 |
| `base_class`, `is_abstract` | from the class declaration | 164-165 |
| `type` | `Abstract [non-callable]`, else `Service` if the controller name contains `service`, else `Resources` | 181-186 |
| Inherited actions | a **hard-coded table**: `ApiMutableModelControllerBase` adds `get` (GET) and `set` (POST); `ApiMutableServiceControllerBase` adds `status` (GET), `start`/`stop`/`restart`/`reconfigure` (POST). Applied only when the class *directly* extends one of those two names. | 31-62, 176-179 |

The hard-coded table is correct for core `26.7.4`: those are exactly the public `*Action` methods of [`ApiMutableModelControllerBase.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Base/ApiMutableModelControllerBase.php) (`getAction` l.204, `setAction` l.392) and [`ApiMutableServiceControllerBase.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Base/ApiMutableServiceControllerBase.php) (`start` l.101, `stop` l.117, `restart` l.133, `reconfigure` l.186, `status` l.234). It would silently drift if upstream added a base action.

The snake_case command names round-trip through the real router: core's [`Router.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/library/OPNsense/Mvc/Router.php) (l.185-189) converts each URL element with `lcfirst(str_replace('_', '', ucwords($element, '_'))) . "Action"`, so the generator's odd-looking `del_r_r_d` does resolve to `delRRDAction`.

Parser robustness: the parser's error handler discards unexpected tokens and continues (`_p_error`, l.147-153). With `--debug`, a run over core `26.7.4` reports 246 ignored tokens and plugins 107, i.e. the vendored grammar does not fully cover the PHP in use and recovers silently. I cross-checked the result against a naive regex for `public function \w+Action(` over the same 126 core + 222 plugin files: **no action found by the regex was missed** by the parser at this ref. The only differences were two actions the parser found and the regex did not (see 3d).

### 3. Accuracy and completeness (measured against core/plugins `26.7.4`)

Run summary (upstream library driven directly, JSON dumped from the pydantic models):

| | core | plugins |
| --- | --- | --- |
| modules | 24 | 69 |
| controllers parsed | 125 (+1 excluded: Firmware) | 222 |
| controllers with zero actions (dropped from docs) | 3 | 0 |
| actions | 937 | 1,477 |
| method = `POST` / `GET` / `GET,POST` | 505 / 356 / 76 | 870 / 489 / 118 |
| of which `GET` by **fallback default**, not detection | **267** | **314** |
| controllers linked to a model XML | 64 | 127 |
| direct base class | 63 MutableModel, 44 ApiControllerBase, 11 MutableService, 5 `FilterBaseController`, 2 `LeasesController` | 128 / 42 / 51, 1 `\OPNsense\Proxy\Api\ServiceController` |

**3a. Method inference is a guess, and wrong in the dangerous direction.** The heuristic only sees calls lexically inside the action body. Anything delegated is invisible:

- `firewall/source_nat/upload_rules`, `move_rule_before`, `toggle_rule_log` (and the same trio on `d_nat`, `npt`, `one_to_one`, plus `filter/upload_rules`, `filter/toggle_rule_log`) are emitted as `GET`. The actions are one-line delegations ([`SourceNatController.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Firewall/Api/SourceNatController.php) l.191-209) to helpers in [`FilterBaseController.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Firewall/Api/FilterBaseController.php) that each start with `if (!$this->request->isPost())` (l.333, l.391, l.492) and then mutate configuration.
- `diagnostics/netflow/setconfig` is emitted as `GET`; the body guards on `hasPost("netflow")`, which the heuristic does not recognise, then writes the model ([`NetflowController.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Diagnostics/Api/NetflowController.php) l.79-87).
- `wireguard/client/add_client` is emitted as `GET`; it delegates to `setClientAction(null)` ([`ClientController.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Wireguard/Api/ClientController.php) l.78-81).
- A name-pattern scan of the fallback-`GET` set finds 16 such mutating-sounding commands in core and 31 in plugins (e.g. `freeradius/*/toggle_*`, `ftpproxy/service/start|stop|restart`, `acmeclient/certificates/import`, `redis/service/resetdb`). I verified the core examples above in source; the plugin ones are name-based only.
- The converse also holds and is already noted in the handoff: a detected `POST` does not mean "mutation" (`search_*` endpoints are `GET,POST`), and one action can behave differently per verb. `core/firmware/status` runs a synchronous `firmware probe` via configd only when called with POST ([`FirmwareController.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Core/Api/FirmwareController.php) l.96-107), while the hand-written docs list it as `POST` only.

Consequence for the registry: the generator's method column must never feed the read-only allowlist. It is documentation of the usual calling convention, at best.

**3b. Inheritance is not resolved.**

- Subclasses of an intermediate controller get neither the intermediate's actions nor the base defaults. `firewall/source_nat` is emitted without `apply`, `list_categories`, `list_network_select_options`, `list_port_select_options`, which it inherits from the abstract `FilterBaseController` (l.166, 203, 256, 309). Those appear only under a separate `filter_base` table marked "Abstract [non-callable]", and a reader must know to union them. (`source_nat` shows `get`/`set` only because it overrides them itself.)
- `kea/leases4` and `kea/leases6` extend the abstract [`LeasesController`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Kea/Api/LeasesController.php) and declare no actions of their own, so they parse to zero actions and the script drops them (`collect_api_endpoints.py` l.62-63). `kea/leases4/search` is a plausible v1 read endpoint and is absent from the concrete-controller output.
- In plugins, `proxysso/service` extends `\OPNsense\Proxy\Api\ServiceController` and is emitted with only its own five actions, without the inherited service actions, for the same reason.
- `diagnostics/log` implements everything through `__call` ([`LogController.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Diagnostics/Api/LogController.php) l.39), so it has zero `*Action` methods and is dropped. No static extractor will enumerate its commands either (the dispatcher explicitly allows `__call` controllers, [`Dispatcher.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/library/OPNsense/Mvc/Dispatcher.php) l.94-97); such controllers need hand-written registry entries.

**3c. Things it does not extract at all:** request body or query field names (`request->get('searchPhrase')`, `getPost('rowCount')`), response shape, model field types (the model XML is linked, not parsed), ACL privilege patterns (`ACL.xml`), configd actions invoked, config writes, and the providing plugin package. `Controller.filename` is a basename and `module` is a bare directory name, so two plugins contributing to one module are merged without provenance (at `26.7.4`: `proxy` is fed by both `www/OPNProxy` and `www/squid`; `diagnostics` exists in both core and plugins).

**3d. Visibility is ignored.** `private function remoteServiceAction(...)` in [`HasyncStatusController.php`](https://github.com/opnsense/core/blob/ace3b5b5f856261f77b71bd54f3fe63fa2447a12/src/opnsense/mvc/app/controllers/OPNsense/Core/Api/HasyncStatusController.php) (l.40) is published as the endpoint `core/hasync_status/remote_service` ([`core.rst`](https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/source/development/api/core/core.rst) l.48). (The other parser-only hit, `getOcspInfoDataAction` in `Trust/Api/CrlController.php` l.427, has no modifier and is therefore legitimately public.)

**3e. The Firmware controller is excluded and documented by hand.** [`firmware.rst`](https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/source/development/api/core/firmware.rst) was last edited 2023-11-21 (`943811aede`), still uses camelCase commands (`getOptions`, `syncPlugins`), and omits `cleanup`, which exists at `26.7.4` (`FirmwareController.php` l.523). This matters because the handoff names `core/firmware/status` as the first candidate read.

### 4. Published pages versus a pinned ref

- The site has no per-release versions: `source/conf.py` sets a single `version` string from the docs repo's own revision (l.84-86) and the generated links are hard-wired to `blob/master` (`collect_api_endpoints.py` l.33-38). Fetched 2026-09-19, [docs.opnsense.org/development/api/core/interfaces.html](https://docs.opnsense.org/development/api/core/interfaces.html) shows no release selector.
- Regeneration is manual and irregular: commits touching `source/development/api/core` are 2026-07-22 (hand edit, below), 2026-05-13 (`a95e5806c5`, "run api collection script"), 2026-01-28 ("update core (stable/26.1)"), 2025-12-10 ("stable/25.7"), 2025-07-23. The source branch used varies by run and is only recorded in the commit message.
- Regenerating at `26.7.4` and diffing against docs `2c85e8a` changes 9 core and 5 plugin module pages and adds one plugin page (`cloudflared`). New in core relative to the published pages: whole controllers `interfaces/assignment`, `interfaces/wireless_settings`, `routing/group_settings`, `captiveportal/template`; new actions such as `firewall/{d_nat,npt,one_to_one,source_nat}/download_rules|upload_rules`, `firewall/migration/count_rules|count_outbound|download_outbound|flush_outbound`, `diagnostics/netflow/reset`, `unbound/overview/reset`, `core/menu/set_favorite`; renamed parameters (`del_item` `$uuid` to `$uuids`); and a command rename `diagnostics/interface/_carp_status` to `carp_status`. The live `interfaces` page confirmed the staleness: no `AssignmentController` or `WirelessSettingsController` table.
- Upstream acknowledges the drift: [docs PR #892](https://github.com/opnsense/docs/pull/892) (2026-07-22) hand-edited the generated `filter_base` table to drop the savepoint/rollback actions removed in 26.7 and states that "the rest of the firewall endpoint tables carry unrelated drift that a full `collect_api_endpoints.py` refresh would pick up".

So "reuse its output" can only mean *output we generate ourselves from a pinned ref*, never the published pages.

### 5. Running it against a pinned ref

Verified by doing it: shallow clones of core and plugins at tag `26.7.4`, Python 3.13 venv with `ply 3.11`, `pydantic 2.13.5`, `jinja2 3.1.6`, then the README command for each repo. Both runs exit 0 in seconds. Notes:

- Python 3.10+ is required (`str | None` annotations in pydantic models); the macOS system Python 3.9 will not work.
- The script always writes RST into its own checkout (`os.path.dirname(__file__)/source/development/api/<repo>/`). For a catalog, skip the script and call `lib.utils.collect_api_modules(path)` directly, then `model_dump()` each `Controller`; that needs only `ply` and `pydantic`.
- It only reads and parses files. Nothing from the core/plugins tree is imported or executed, which is consistent with the handoff's "parse upstream source as data; never execute it".
- Plugins coverage is the whole plugins repo at that ref (69 modules), far wider than the map's "plugins limited to what the v1 inventory needs", and carries no package provenance, so filtering has to be done by path by the caller.
- The output contains no ref, tag or commit. Provenance must be recorded by the caller.

### 6. License

- `collect_api_endpoints.py` carries a BSD 2-clause header, Copyright (c) 2020-2025 Ad Schellevis (l.2-26). `lib/__init__.py` has the same header. The docs repo [`LICENSE`](https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/LICENSE) is BSD 2-clause (worded for "documentation"). core and plugins are BSD-2-Clause per the GitHub license API.
- `lib/phply/` is a modified copy of [`viraptor/phply`](https://github.com/viraptor/phply) (import commit `12cb1a4e32`). Upstream phply's [`LICENSE`](https://github.com/viraptor/phply/blob/050aaa269bf88a6996003005b6afd163a7233ab8/LICENSE) is BSD 3-clause, Copyright (c) 2010 Dave Benjamin and contributors. The vendored files in `opnsense/docs` carry **no license header and no LICENSE file**, so anyone vendoring that directory must restore the phply notice themselves. Upstream phply was last pushed 2023-02-20.
- Nothing here blocks reuse. Generated facts about endpoints (module/controller/command names) are derived from BSD-2-Clause source.

### 7. Recommendation

Three options were on the table. Given that every registry entry still requires human review of semantics and side effects:

1. **Reuse the published output: reject.** Unversioned, stale against the newest stable tag, hand-edited in places, firmware page hand-maintained and incomplete.
2. **Reuse the generator as the registry's proposal stage: reject as the primary mechanism.** It enumerates candidates well (no missed `*Action` methods at this ref) but the three things a reviewer most needs help with are the things it gets wrong or omits: effective action set after inheritance, whether an action is guarded by `isPost` or writes state, and what it touches (configd, config, ACL). Fixing that means replacing the walker and extending a vendored 2010-era PLY grammar that already silently skips hundreds of tokens in current core. We would own a fork of a parser we did not choose.
3. **Tree-sitter extraction, with the upstream library as a cross-check: recommended.** Tree-sitter is already in the handoff baseline for PHP extraction, so this adds no technology. The extractor should emit, per pinned ref: module/controller/command using the same naming rules as upstream (section 2, so names match the official docs), the *resolved* action set across the full `extends` chain, signature parameters, request keys read, evidence flags (`isPost`/`hasPost` guards including one level of helper delegation, `*Base` mutators, `configdRun`/`configdpRun` action strings, `Config` lock/save, `__call` presence, method visibility), model class/container/path, ACL patterns, and source path (which gives plugin provenance). Then, in CI for each pinned ref, run upstream's `collect_api_modules` and assert our `(module, controller, command)` set is a superset of theirs minus known false positives (private methods). That is a few dozen lines, keeps us honest against the official view, and needs no fork.

Either way the extractor output is a *proposal*; nothing in it may populate the allowlist without review, and `__call` controllers (`diagnostics/log`) and per-verb behaviour (`core/firmware/status`) need hand-written entries confirmed in the lab.

## Limitations

- Measurements are for one ref pair (core/plugins `26.7.4`) and docs `master` at `2c85e8a`. The compatibility target is not decided here; counts will differ on another release, though the structural blind spots come from the generator's code, not the ref.
- "No missed actions" was checked only against a line-anchored regex for `public function …Action(`; an action the regex and the parser both miss (unusual formatting, traits, or methods injected another way) would go unnoticed. I did not check whether any controller uses PHP traits to contribute actions.
- The 16 core / 31 plugin "fallback GET but mutating-sounding" figures come from a command-name pattern. I confirmed the core firewall, netflow and wireguard cases in source; the plugin cases were not individually read, and some may be harmless.
- I did not test whether the private `remoteServiceAction` is actually reachable over HTTP; the claim is only that the generator lists it without checking visibility.
- No request was made to any OPNsense instance. Whether GET to a fallback-`GET` mutator is rejected, ignored or executed at runtime is a lab question.
- The live site reported build revision `59093b8`, which is not the docs `master` head I cloned; I compared one live page (`interfaces`) and it matched the committed RST, but did not diff the whole site.
- Tree-sitter's PHP grammar was not exercised here. That it parses current core cleanly is an assumption carried from the handoff baseline, to be confirmed when the extractor is prototyped.
- The upstream library has no versioning or stability promise; using it as a CI cross-check means pinning the docs commit too.
