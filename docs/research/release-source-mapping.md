# How reliably does an installed package version map to upstream source?

Research for [issue #4](https://github.com/andrewferk/opnsense-pilot/issues/4). Researched 2026-09-19 against primary sources only (upstream repos at pinned refs, the official package mirror, docs.opnsense.org). Version numbers below are observations used as worked examples, not a compatibility-target decision.

## Short answer

**For `opnsense` (core) on Community edition: very reliably, down to an exact commit, provided the inspector reads the build hash and not just the version string.**

- The core package version is not hand-written. It is computed at build time from git: `<nearest tag>` plus `_<number of commits since that tag>`, and the 9-character HEAD hash is baked into the package. So `26.7.4` means "the commit tagged `26.7.4`", and hotfix `26.7.4_1` means "exactly 1 commit after tag `26.7.4` on `stable/26.7`". Hotfixes are **not** tagged; `_N` is the locator.
- The firewall carries the hash: `/usr/local/opnsense/version/core` (JSON, `product_hash` / `CORE_HASH` / `CORE_COMMIT`), readable with `opnsense-version -H`, and returned by the read-only `GET /api/core/firmware/status` and `GET /api/core/firmware/info` under `product`.
- **Plugins are weaker.** A plugin's version (`PLUGIN_VERSION[_PLUGIN_REVISION]`) is hand-maintained per plugin and is independent of release tags. The same plugin version is rebuilt at every release from a different `opnsense/plugins` commit (observed: `os-ddclient-1.31_1` built at both tag `26.7.3` and tag `26.7.4`, different package checksums). The build hash exists on the box (`/usr/local/opnsense/version/<plugin>`), but I found no firmware API field that exposes it. Without the hash, a plugin version maps to a *range* of commits, not one.
- Stable branches are protected against force-push and deletion by a public GitHub ruleset. Tags are **not** covered by any visible ruleset, are unsigned, and the upstream build tooling explicitly says "sometimes tagging needs to be redone". So pin citations to **commit SHAs**, never to tag names.
- What no version field can prove: that files on disk still equal the package contents. `opnsense-patch` applies upstream commits to the live system without changing the package version or hash.

Recommended claim wording: "source for the `opnsense` package build `<version>` (`<hash>`)", with confidence **exact** when version-derived commit and on-box hash agree, **degraded** when only the version string is known, and **unsupported** for Business edition and `-devel` packages.

## Findings

Pinned refs used throughout: `opnsense/core` tag `26.7.4` (commit `ace3b5b5f856261f77b71bd54f3fe63fa2447a12`), `opnsense/plugins` tag `26.7.4` (commit `6cb23d364671d7d409f2e9e9a14987efcc8ccc7e`), `opnsense/tools` master at `d07e13074326610d7e4adf7a1b47774df723dc4f`, `opnsense/changelog` master at `e38c5c2f6d517267f4b6efb8fc7e742521fdf485`, `opnsense/update` master at `b185bb1ea4bd007157713dfe4ab09205a267fe8c`.

### 1. How core and plugins tag releases

- `opnsense/core` has 423 tags, **all annotated**, and **none contains an underscore** (`git ls-remote --tags https://github.com/opnsense/core`, 2026-09-19). Tag shapes observed: `YY.M` (major, e.g. `26.7`), `YY.M.N` (point release, e.g. `26.7.4`), and pre-releases `YY.M.a`, `YY.M.b`, `YY.M.r`, `YY.M.rN` (core); plugins uses `YY.M.d` and `YY.M.rN` for pre-releases. Source: <https://github.com/opnsense/core/tags>, <https://github.com/opnsense/plugins/tags>.
- The same tag names exist in `core`, `plugins`, `ports`, `src` and `tools` (e.g. `26.7.4` in all five), each pointing at that repo's own commit. `tools` is missing some (e.g. no `26.1.6` tag in the first page of <https://github.com/opnsense/tools/tags>), so do not assume every repo has every tag.
- Release tags live on `stable/<series>` branches, not on `master`. `core` `26.7.4...master` is `diverged` (ahead 344, behind 233): stable commits are cherry-picks with different SHAs. Example: <https://github.com/opnsense/core/commit/35b64b84c> carries `(cherry picked from commit 5fdad5ba9977b492b5a172d20395c8ede0990e5d)`. A citation must therefore use the **stable-branch SHA**; the master SHA of "the same change" is a different object and may differ in content.
- The 59 commits between core `26.7.3` and `26.7.4` all have exactly one parent (linear history, no merges), so "N commits after the tag" is unambiguous. Source: `GET /repos/opnsense/core/compare/26.7.3...26.7.4`.
- The annotated tag object for core `26.7.4` is **unsigned** (`verification.reason: "unsigned"`, message "stable release"). Source: `GET /repos/opnsense/core/git/tags/4b70db4090faca26f2854752535e5958410cff32`.

### 2. How the core package version is defined

- `Scripts/version.sh` computes three values: `git describe --abbrev=0 --always <match>` (nearest tag), `git rev-list <tag>.. --count` (commits since), and the first 9 characters of `HEAD`. Source: <https://github.com/opnsense/core/blob/26.7.4/Scripts/version.sh>.
- The core `Makefile` assigns those to `CORE_VERSION`, `CORE_REVISION`, `CORE_HASH`, and sets `CORE_PKGVERSION` to `${CORE_VERSION}_${CORE_REVISION}` when the revision is non-zero, else `${CORE_VERSION}`. The tag match is restricted to the series (`--match=${CORE_ABI}*`) for community builds. Source: <https://github.com/opnsense/core/blob/26.7.4/Makefile> (lines 63-110).
- The package manifest sets `desc` to `CORE_HASH` and embeds the whole version file as pkg annotations. Same file, `manifest:` target.
- **So `_N` on the core package is a commit count, not a FreeBSD-style hand-bumped PORTREVISION.** Verified empirically:
  - The changelog for 26.7.3 lists hotfixes `26.7.3_2`, `26.7.3_8`, `26.7.3_11` (<https://github.com/opnsense/changelog/blob/e38c5c2f6d517267f4b6efb8fc7e742521fdf485/community/26.7/26.7.3>). The commits after tag `26.7.3` on `stable/26.7` line up exactly: commits 1-2 are the two `_2` items, 3-8 the six `_8` items, 9-11 the three `_11` core items (commit 11 is `577d94c66`).
  - The official mirror's frozen 26.7.3 catalogue lists `opnsense 26.7.3_11` with `product_hash` `577d94c66`. Source: `https://pkg.opnsense.org/FreeBSD:15:amd64/26.7/MINT/26.7.3/latest/packagesite.pkg`.
  - The live catalogue lists `opnsense 26.7.4_1` with `product_hash` `4fd8ebfb1` and `CORE_COMMIT` `26.7.4 1 4fd8ebfb1`; `4fd8ebfb1` is the first commit after tag `26.7.4` on `stable/26.7` and matches the single core item in the `26.7.4_1` changelog note. Source: `https://pkg.opnsense.org/FreeBSD:15:amd64/26.7/latest/packagesite.pkg` (fetched 2026-09-19).
- Consequence: the stable branch head runs **ahead** of what is shipped. On 2026-09-19 `stable/26.7` was 7 commits ahead of tag `26.7.4` while the shipped package was `_1`. Never cite the branch head.

### 3. How plugin package versions are defined

- Each plugin's `Makefile` hand-sets `PLUGIN_VERSION` and optionally `PLUGIN_REVISION`; `Mk/plugins.mk` forms `PLUGIN_PKGVERSION` as `${PLUGIN_VERSION}_${PLUGIN_REVISION}` when the revision is non-zero. Example: <https://github.com/opnsense/plugins/blob/26.7.4/security/acme-client/Makefile> (`PLUGIN_VERSION= 4.17`); logic at <https://github.com/opnsense/plugins/blob/26.7.4/Mk/plugins.mk>. **For plugins, `_N` is a hand-bumped revision, unlike core.**
- `plugins.mk` still runs the same `Scripts/version.sh` and records the 9-character repo HEAD as `PLUGIN_HASH`, written into `/usr/local/opnsense/version/<plugin-name>` as `product_hash` (template: <https://github.com/opnsense/plugins/blob/26.7.4/Templates/version>) and into the pkg annotations.
- Plugin versions do not track release tags. Observed in the mirror catalogues: all 105 non-devel `os-*` packages in the live 26.7 catalogue carry `product_hash` `6cb23d364` (= plugins tag `26.7.4`); all 105 in the frozen 26.7.3 catalogue carry `335042e98` (= plugins tag `26.7.3`). `os-ddclient` is `1.31_1` in both, with different package checksums. In that instance no `dns/ddclient` file changed between the two tags (`GET /repos/opnsense/plugins/compare/26.7.3...26.7.4`), so the source was identical; nothing in the build enforces that in general.
- Whether an installed firewall picks up the rebuilt same-version plugin package on upgrade was **not verified** (it depends on pkg's upgrade rules). The on-box version file reports whichever build is actually installed, so reading it sidesteps the question.

### 4. How opnsense/tools builds, and from which refs

- Defaults: `COREBRANCH?= stable/${ABI}`, `PLUGINSBRANCH?= stable/${ABI}`, `SRCBRANCH?= stable/${ABI}`, `PORTSBRANCH?= master`. Source: <https://github.com/opnsense/tools/blob/d07e13074326610d7e4adf7a1b47774df723dc4f/Makefile> (lines 128-147).
- `build/core.sh` and `build/plugins.sh` check the expected branch, `git reset --hard` to it, and ask the repo's own Makefile for the version (`make -v CORE_PKGVERSION` / `PLUGIN_PKGVERSION`). They build the **branch head as checked out on the build host**, not a tag by name; a release is "the head happened to be the tag". Sources: <https://github.com/opnsense/tools/blob/d07e13074326610d7e4adf7a1b47774df723dc4f/build/core.sh>, <https://github.com/opnsense/tools/blob/d07e13074326610d7e4adf7a1b47774df723dc4f/build/plugins.sh>.
- `make update VERSION=git.tag` checks out a matching tag instead of HEAD; `make hotfix[-<step>]` is the documented hotfix rebuild pass. Source: <https://github.com/opnsense/tools/blob/d07e13074326610d7e4adf7a1b47774df723dc4f/README.md>.
- Escape hatches that break the version-to-commit rule: `COREVERSION` overrides `CORE_PKGVERSION` outright (`build/core.sh`), and `EXTRABRANCH` builds additional branches. Whether official builds ever use `COREVERSION` is unknown; the two catalogue observations above show version and hash agreeing.
- Ports (third-party packages such as PHP, Unbound) build from `opnsense/ports` `master`, which is tagged per release (<https://github.com/opnsense/ports/tags>). Mapping a third-party package version to a ports commit was not investigated.

### 5. Are stable branches rewritten or tags moved?

- **Branches:** both `opnsense/core` and `opnsense/plugins` have an active repository ruleset named `stable` targeting `refs/heads/stable/*` with rules `deletion`, `update`, `creation`, `non_fast_forward` (created 2024-10-18). Force-pushes and deletions of stable branches are blocked for non-bypass actors. Sources: `GET /repos/opnsense/core/rulesets/2299729`, `GET /repos/opnsense/plugins/rulesets/2299677`. The bypass-actor list is not publicly readable, and nothing covers history before October 2024.
- **Tags:** the only ruleset in each repo targets branches; no tag ruleset is visible. The upstream build tooling documents that tags do get redone: `git_fetch()` in `build/common.sh` says "sometimes tagging needs to be redone but a fetch will fail because of clobbered tags so when passing a tag to be stripped try removal to unbreak" (<https://github.com/opnsense/tools/blob/d07e13074326610d7e4adf7a1b47774df723dc4f/build/common.sh>, lines 327-339). I did not find a concrete instance of a published release tag being moved; frequency is unknown.
- Practical rule: resolve tag to commit SHA once, store the SHA, cite the SHA. Cross-check it against the on-box `product_hash`.

### 6. How the changelog repo relates

- `opnsense/changelog` holds one text file per tagged release under `community/<series>/<version>` and `business/<series>/<version>`; the file name is the release name. It is shipped to firewalls as a signed set "including amendments for previous versions". Source: <https://github.com/opnsense/changelog/blob/e38c5c2f6d517267f4b6efb8fc7e742521fdf485/README.md>.
- Hotfixes get **no file of their own**. They are appended to the parent release's file as "A hotfix release was issued as `<version>_N`:" followed by items. The changelog is thus the only upstream place that names which `_N` values were actually shipped (e.g. 26.7.3 shipped `_2`, `_8`, `_11`, not `_1` or `_5`).
- Changelog entries are prose, not commit references. They corroborate a mapping; they do not define it. Files are amended after the fact by design, so pin the changelog by commit SHA too.
- The mirror keeps only the last hotfix of a superseded release (`MINT/26.7.3/` holds only `opnsense-26.7.3_11.pkg`), so intermediate hotfix packages cannot be re-downloaded for verification.

### 7. Business edition (label unsupported)

- Business series use `.4` and `.10` minors; the core Makefile treats `CORE_TYPE` business differently (verbatim tag match) and the package/product id is `opnsense-business` (`opnsense-version` tests `product_id` for `-business`). Sources: <https://github.com/opnsense/core/blob/26.7.4/Makefile>, <https://github.com/opnsense/core/blob/26.7.4/src/sbin/opnsense-version>.
- Public `opnsense/core` has business-style tags and stable branches only for `21.4` and `21.10`. Business changelogs exist through `26.4.2`, but there are **no public tags or branches** for 22.4 onward. There is no public ref to pin a Business citation to.
- Docs describe a "Commercial firmware repository", changes "included in a more conservative manner", and BE-only features (central management, WAF, OpenID Connect, etc.). Source: <https://docs.opnsense.org/be.html>.
- Detection from a live firewall: `product_id` equal to `opnsense-business`, or `product_series` with minor `4`/`10`, or non-empty `product_license` in the firmware `product` payload (`src/opnsense/scripts/firmware/product.php`). Any of these means: label unsupported, make no source claim.

### 8. What an inspector can read from a live firewall

| Signal | Where | Carries |
| --- | --- | --- |
| `GET /api/core/firmware/status` (GET does not trigger a remote check; POST does) | `FirmwareController::statusAction` | `product` = full version file: `product_version`, `product_hash`, `product_id`, `product_series`, `product_abi`, `CORE_COMMIT` ("tag count hash"), plus `product_repos`, `product_mirror`, `product_time` |
| `GET /api/core/firmware/info` | `FirmwareController::infoAction` | same `product` block, plus per-package `name`, `version`, `locked`, `repository`, `origin` for every installed package including plugins. **No per-plugin hash.** |
| `/usr/local/opnsense/version/core` | file / `opnsense-version -H`, `-v`, `-n` | core hash, version, product id |
| `/usr/local/opnsense/version/<plugin>` | file / `opnsense-version -H <plugin>` | plugin `product_hash`, `product_version`, `product_tier` |
| pkg annotations | `pkg info -A <pkg>` (shell) | same JSON as the version file |
| `/var/cache/opnsense-patch` | `opnsense-patch -l` (shell) | cached patches that have been fetched (applied or not is not recorded there as far as I could see) |
| `POST /api/core/firmware/health` | runs `pkg check -sa` and core checks | detects files modified relative to the package. It is a POST that starts a job, so it is outside a strictly read-only API surface. |

Sources: <https://github.com/opnsense/core/blob/26.7.4/src/opnsense/mvc/app/controllers/OPNsense/Core/Api/FirmwareController.php>, <https://github.com/opnsense/core/blob/26.7.4/src/opnsense/scripts/firmware/product.php>, <https://github.com/opnsense/core/blob/26.7.4/src/opnsense/version/core.in>, <https://github.com/opnsense/core/blob/26.7.4/src/opnsense/scripts/firmware/health.sh>, <https://github.com/opnsense/update/blob/b185bb1ea4bd007157713dfe4ab09205a267fe8c/src/patch/opnsense-patch.8>.

A code search of `opnsense/core` (default branch) for `product_hash` finds only `opnsense-version`, `version/core.in`, and the firmware view. I found no API that returns a plugin's hash. None of this was exercised against a live firewall; field presence is from source reading plus the mirror catalogue.

Suggested resolution procedure for core: (1) read `product_version` and `product_hash`; (2) split the version into tag and `_N`; (3) resolve the tag to a SHA on `stable/<series>` and walk N commits forward (linear history); (4) require that SHA to start with `product_hash`. Agreement gives an exact, immutable citation target. Disagreement (moved tag, custom build, `COREVERSION` override) means trust the hash if it resolves in `opnsense/core`, else claim nothing.

## Residual uncertainty

1. **Package identity is not file identity.** `opnsense-patch` "treats all arguments as upstream git repository commit hashes, downloads them and finally applies them in order" (<https://docs.opnsense.org/manual/opnsense_tools.html>) and leaves the package version and hash untouched. Manual edits do the same. Only the health audit (`pkg check -sa`, a POST) detects this. A citation can honestly claim "the source of the installed package build", not "the bytes on disk".
2. **Nine hex characters.** `product_hash` is a 9-character prefix. It must be resolved inside the expected repo and checked for uniqueness; combined with the version-derived position it is strong, alone it is a prefix.
3. **Plugins via API.** Plugin version alone maps to one commit per release in which that version was built. Exact mapping needs the on-box version file (SSH or config/export path), or a bounded claim ("plugin source as of release tag X", where X is inferred from the core version, which assumes the plugin was installed or upgraded at that release). Whether any API outside `FirmwareController` exposes plugin hashes is unverified.
4. **Tags can move and are unsigned.** Frequency unknown; no instance found. Mitigated entirely by pinning SHAs and cross-checking the hash.
5. **Branch protection limits.** The ruleset dates from 2024-10-18 and its bypass list is not public. Older series may have been rewritten before then; not investigated.
6. **Build-side overrides.** `COREVERSION`, `EXTRABRANCH`, and locally built packages (`make upgrade` in a core checkout, `opnsense-code`) can produce versions that do not follow the tag-plus-count rule. For official mirror builds the rule held in both catalogues inspected (26.7.3_11 and 26.7.4_1); that is two data points, not a guarantee.
7. **`-devel` packages** (`opnsense-devel 27.1.a_287` at `6e3cda346`, plugin `-devel` builds at a master commit) build from `master`-side refs with alpha/beta tag matching. Treat as unsupported or hash-only.
8. **Beyond core and plugins.** Base, kernel, and third-party ports packages were not mapped. The firmware payload identifies their versions, and `src`/`ports` are tagged per release, but hotfix-level mapping for them is unknown.
9. **Reproducibility.** Nothing here shows that rebuilding the cited commit yields the same package bytes; the claim is about source provenance as recorded by the builder, which the firewall trusts via the signed repository.
10. **Intermediate hotfix packages are not retained** on the mirror, so past `_N` builds cannot be independently re-fetched to confirm their hash; the rule is inferred from the build scripts and confirmed only on the latest hotfix of each inspected release.
