# Compatibility target release

Research for [issue #3](https://github.com/andrewferk/opnsense-pilot/issues/3). All facts below were fetched on **2026-09-19** from the cited primary source; nothing is carried over from the handoff or from memory.

## Answer

**Target OPNsense Community Edition 26.7 "Xenial Xenops", pinned at `26.7.4` (hotfix level `26.7.4_1`), on FreeBSD 15.1, amd64.**

- Series: **26.7**, released 2026-07-15. It is the current stable Community series; 27.1 exists only as development tags (`27.1.a` in core, `27.1.d` in plugins).
- Exact latest version: **26.7.4**, released 2026-09-15, with hotfix **26.7.4_1** issued 2026-09-16.
- Source pins: `opnsense/core` tag `26.7.4` = `ace3b5b5f856261f77b71bd54f3fe63fa2447a12`; `opnsense/plugins` tag `26.7.4` = `6cb23d364671d7d409f2e9e9a14987efcc8ccc7e`; `opnsense/docs` has **no tags and no release branches**, so pin by commit: `2c85e8a9ea43f4e008a536734ad428783fae94f9` (master HEAD on the research date).
- Install media: only **26.7** images exist (no 26.7.x respin). Install from `OPNsense-26.7-dvd-amd64.iso.bz2` (or `vga`/`serial`/`nano`), then firmware-update to 26.7.4_1.
- Support window: no written EOL policy was found. Observed practice is a 6-month major cycle; 26.7 is the maintained series until **27.1 (January 2027)**. Plan on re-targeting to 27.1 around then.
- For a read-only inspector, 26.7 is a moving API surface: interface assignments, gateway groups, wireless, and reporting settings moved to MVC/API during this series, firewall rules now default to MVC, and the official API reference in the docs has not been regenerated for 26.7. Treat the core source at the pinned tag as the API authority, not the docs.

## Findings

### 1. Current stable series and exact version

- The official image README states: "The latest stable release image for OPNsense is 26.7 (July 15, 2026). The next scheduled release image for OPNsense is 27.1 (January, 2027)."
  Source: https://pkg.opnsense.org/releases/26.7/README
- The 26.7 release notes are dated July 15, 2026 and name the release "Xenial Xenops".
  Source: https://github.com/opnsense/changelog/blob/e38c5c2f6d517267f4b6efb8fc7e742521fdf485/community/26.7/26.7
- The Community changelog directory for 26.7 contains `26.7.r1`, `26.7.r2`, `26.7`, `26.7.1`, `26.7.2`, `26.7.3`, `26.7.4`. Nothing newer.
  Source: https://github.com/opnsense/changelog/tree/e38c5c2f6d517267f4b6efb8fc7e742521fdf485/community/26.7
- Point release dates from the changelog files (same pinned commit): 26.7.1 = July 21, 2026; 26.7.2 = August 12, 2026; 26.7.3 = August 27, 2026; 26.7.4 = September 15, 2026.
- 26.7.4 notes: "A hotfix release was issued as 26.7.4_1" (grid UI fix, suricata 8.0.7, unbound 1.26.1). The changelog repo commit "community: annotate hotfix" is dated 2026-09-16.
  Source: https://github.com/opnsense/changelog/blob/e38c5c2f6d517267f4b6efb8fc7e742521fdf485/community/26.7/26.7.4
- The forum announcements board lists "OPNsense 26.7.4 released" by franco (first post September 15, 2026; hotfix follow-up September 16, 2026) as the newest Community announcement.
  Sources: https://forum.opnsense.org/index.php?board=11.0 and https://forum.opnsense.org/index.php?topic=52967.0
- The docs site lags: `CE_releases.rst` at docs commit `2c85e8a` still says the latest version is 26.7.3.
  Source: https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/source/CE_releases.rst

### 2. Official amd64 installer images

- Directory (official mirror, The Netherlands): https://pkg.opnsense.org/releases/26.7/ (identical content at https://pkg.opnsense.org/releases/mirror/, which always tracks the latest image). Files are dated 2026-07-13. The `/releases/` index has no `26.7.x` directory, so **26.7 is the only 26.7-series image**.
- URL pattern: `https://<mirror>/releases/<image-version>/OPNsense-<image-version>-<type>-amd64.<ext>.bz2`, e.g. `https://pkg.opnsense.org/releases/26.7/OPNsense-26.7-dvd-amd64.iso.bz2`. The full mirror list is at https://opnsense.org/download/ (which offers 26.7, amd64 only).
- Image types (README wording):
  - `dvd`: "ISO installer UEFI hybrid image with live system capabilities running in VGA mode" (`.iso.bz2`, 471M)
  - `vga`: "USB installer UEFI hybrid image ... VGA mode" (`.img.bz2`, 471M)
  - `serial`: "USB installer UEFI hybrid image ... serial console (115200) mode" (`.img.bz2`, 471M)
  - `nano`: "A preinstalled serial image for USB sticks, SD/CF cards, SSD with secondary VGA console enabled. These images are 3G in size and automatically adapt to the installed media size after first boot." (`.img.bz2`, 468M)
  Source: https://pkg.opnsense.org/releases/26.7/README
- Published SHA-256 checksums (of the **compressed** `.bz2` files). Fetched from the mirror's `OPNsense-26.7-checksums-amd64.sha256` and cross-checked, byte-identical, against the footer of the 26.7 changelog file on GitHub:

  ```
  SHA256 (OPNsense-26.7-dvd-amd64.iso.bz2) = 95cafedda6d5b22ce832e249dc2309110fbee19f813ad78cf28bb3d387186bfb
  SHA256 (OPNsense-26.7-nano-amd64.img.bz2) = 28d5e2f37e40d87468a924e3006ef10e2ddc6de485b85333d9e3958c84d0cb9d
  SHA256 (OPNsense-26.7-serial-amd64.img.bz2) = 259b441646f1b0d77075a7281e368fe7f4c980360498ed6bc23740bd83c67e32
  SHA256 (OPNsense-26.7-vga-amd64.img.bz2) = d975ed876e0650f6a5bf30b2e97218c5eaa370bef6597b19f43e22c1b950d3fc
  ```

  Sources: https://pkg.opnsense.org/releases/26.7/OPNsense-26.7-checksums-amd64.sha256 and https://github.com/opnsense/changelog/blob/e38c5c2f6d517267f4b6efb8fc7e742521fdf485/community/26.7/26.7
- Upstream warns that a checksum file sitting next to an image on a mirror does not prove authenticity, and tells users to double-check against the forum announcement, GitHub changelog, or blog. Source: README above.
- Signature procedure (from the install manual). Needed files: the `.sha256` file, the `.bz2` image, the `.sig` for the **uncompressed** image, and the `.pub` key. "Make sure to unpack the image using `bunzip2` before verifying. Our signatures are generated before compressing them (as of OPNsense version 24.1)".

  ```
  openssl sha256 OPNsense-<filename>.bz2
  openssl base64 -d -in OPNsense-<filename>.<image>.sig -out /tmp/image.sig
  openssl dgst -sha256 -verify OPNsense-<filename>.pub -signature /tmp/image.sig OPNsense-<filename>.<image>
  ```

  Success prints `Verified OK`. Source: https://docs.opnsense.org/manual/install.html
- The 26.7 public key (`OPNsense-26.7.pub`) is published on the mirror, in the README, and in the 26.7 changelog file on GitHub; the three copies fetched were identical. Take the key from GitHub, not from the same mirror as the image.
  Sources: https://pkg.opnsense.org/releases/26.7/OPNsense-26.7.pub and the changelog URL above.
- Not done here: the images were not downloaded, so neither the checksums nor the signatures were actually exercised. That belongs to the probe-VM ticket.

### 3. Matching source refs

Fetched with `gh api repos/opnsense/<repo>/tags`, `.../git/refs/tags/26.7.4`, and `.../commits/26.7.4`.

| Repo | Ref | Commit | Notes |
| --- | --- | --- | --- |
| `opnsense/core` | tag `26.7.4` (annotated, tag object `4b70db4090faca26f2854752535e5958410cff32`, tagged 2026-09-15T08:13:13Z, message "stable release") | `ace3b5b5f856261f77b71bd54f3fe63fa2447a12` | Branch `stable/26.7` |
| `opnsense/plugins` | tag `26.7.4` | `6cb23d364671d7d409f2e9e9a14987efcc8ccc7e` | `stable/26.7` was 0 ahead / 0 behind the tag |
| `opnsense/src` | tag `26.7.4` | `083dc7025377cba0776aa2686f4720d1df27e693` | FreeBSD base/kernel source. No `26.7.1` tag in src |
| `opnsense/tools` | tag `26.7.4` | `22383fde00ba525faaf31dacc1f15a31674e01ab` | Build tooling |
| `opnsense/changelog` | none (pin by commit) | `e38c5c2f6d517267f4b6efb8fc7e742521fdf485` | master HEAD, 2026-09-18 |
| `opnsense/docs` | **no tags; branches are only `master`, `ipsec-auth`, `ipsec-old-manuals`** | `2c85e8a9ea43f4e008a536734ad428783fae94f9` | master HEAD, 2026-09-11 |

- Tag lists: https://github.com/opnsense/core/tags, https://github.com/opnsense/plugins/tags
- **Hotfixes are not tagged.** `stable/26.7` in core was 7 commits ahead of tag `26.7.4` on the research date. The first of them, `4fd8ebfb13d552329a22aa56427b855e30770488` (2026-09-16, "bootgrid: only schedule dimension changes after data processing, window resizing and table visibility changes"), matches the 26.7.4_1 hotfix note. The other six are dated 2026-09-19 and are unreleased work headed for a later point release. That `4fd8ebf` is exactly what shipped as `_1` is an inference from the matching message, not something upstream states.
  Source: https://github.com/opnsense/core/compare/26.7.4...stable/26.7
- The docs version string is just `git describe --always` of the docs repo (`source/conf.py`), so docs.opnsense.org always reflects docs master, not a release.
  Source: https://github.com/opnsense/docs/blob/2c85e8a9ea43f4e008a536734ad428783fae94f9/source/conf.py

### 4. FreeBSD base

- 26.7 shipped "FreeBSD 15.1-RELEASE-p1 plus assorted stable/15 networking commits" (26.7 notes).
- 26.7.3 "bundles the recent FreeBSD 15.1-RELEASE-p3" (26.7.3 notes). 26.7.4 lists further `src:` backports from stable/15 but names no new patch level.
- Package ABI on the mirror is `FreeBSD:15:amd64`: https://pkg.opnsense.org/FreeBSD:15:amd64/26.7/
- Other runtime versions named in the 26.7 notes: OpenSSL 3.5, OpenVPN 2.7, PHP 8.5, Python 3.13. By 26.7.4: PHP 8.5.10, phalcon 5.20.3 (26.7.3), python 3.13.15 (26.7.2).
- This is a major OS jump from the 26.1 series (26.7 notes: "Since this is a major OS upgrade and OpenSSL changes from 3.0 to 3.5 ...").

### 5. Support window and next major

- Roadmap page: "We use a 6 months major release cycle with firm release dates." 27.1 is listed for **January 2027**; no day is given. Source: https://opnsense.org/about/road-map/
- Image README agrees: "The next scheduled release image for OPNsense is 27.1 (January, 2027)."
- **No explicit Community support/EOL policy was found** on opnsense.org, docs.opnsense.org, or in the docs repo. What upstream practice shows:
  - The last 26.1 point release is 26.1.11, dated July 1, 2026, two weeks before 26.7. No later 26.1.x tag or changelog exists.
  - 26.7.3 includes "firmware: revoke 26.1 fingerprint", i.e. the previous series' repository signing fingerprint was revoked about six weeks after the new major.
  - Inference: a Community series gets updates for roughly six months, until its successor ships, and the predecessor is cut off quickly. 26.7 should be treated as maintained until about January 2027.
- Point-release cadence in 26.7 so far is roughly biweekly (the 26.7.3 notes call it "your biweekly dose"), with untagged `_N` hotfixes in between.

### 6. Release-note items that matter to a read-only API inspector

Moved to MVC/API during 26.7 (new endpoints, new config.xml model locations, so inspector coverage differs between 26.1 and 26.7 and even between 26.7.x points):

- 26.7: "system: migrate gateway groups to MVC/API"; "interfaces: migrate interface assignments to MVC/API"; "reporting: migrate several settings pages to MVC/API"; "firewall: move config.xml default LAN allow rules to new rules GUI"; headline "firewall rules now defaulting to MVC/API".
- 26.7.4: "interfaces: migrate wireless configuration to MVC/API".
- 26.7.3 says work is in progress on "adding interface settings to the new MVC assignments page"; the 27.1 roadmap lists "Assignments - add interface configuration settings" and "Migrate scrub rules to MVC and integrate with rules". Interface settings and scrub/normalization are therefore still legacy (non-MVC) in 26.7.4.

Legacy/dual representations an inspector must handle:

- "firewall: legacy rules pages move to plugin" (`os-firewall-legacy` 1.0). Migration note: "All rules will continue to work regardless of the plugin being installed or not and are easily migrated using the given assistant." So a 26.7 box can carry legacy `<filter>` rules, MVC rules, or both, and the legacy GUI may be absent.
- Outbound NAT vs. source NAT: the 26.1.11 notes say "outbound NAT will stay in 26.7"; 26.7 adds an "outbound NAT to source NAT migration assistant"; 26.7.4 adds a "source NAT migration banner to outbound NAT" and makes "source and destination NAT automatic rules visible in GUI". Both NAT representations coexist in 26.7.
- 26.7.4: "openvpn: moved legacy CARP hook to os-openvpn-legacy plugin".

API and ACL changes:

- 26.7: "firewall: remove unused "safepoint" actions" (the docs API reference dropped savepoint/rollback in docs commit `f9807ac`, 2026-07-22). Write-path only, but it shows endpoints do get removed at a major.
- 26.7: "captive portal: move template actions out of the ServiceController into its own TemplateController" (endpoint path change).
- 26.7: "acl: merge user management ACLs into one single privilege": `page-system-usermanager-addprivs` no longer exists separately. Relevant when defining the least-privilege API user.
- 26.7: "firewall: constraint source NAT getAction() to only general page"; 26.7.2: "firewall: scope get action to general settings in source NAT".
- 26.7: "mvc: BaseField: emit descriptions in getNodes() when they are not the same as the value to match getNodeContent()" (can change the shape of `get` responses).
- 26.7.1: "mvc: safeguard some write operations with missing throwReadOnly() actions for custom action" (GHSA-vw8q-pqq7-2q7v). A read-only user could previously reach some write actions; an argument for targeting at least 26.7.1.
- 26.7.2: "backend: further restrict actions to root and wwwonly for more sensitive actions"; "system: improve "user-config-readonly" in static pages".
- 26.7.3: "firewall: deprecate old rule register function names due to functional overlaps" (PHP plugin hook level, not REST); "firewall: use new "rlabel" from pfctl for persistent rule identification across reloads"; "system: handle missing objects during deletion in API".
- 26.7.4: "firewall: implement JsonAuditField in all MVC components" and "mvc: JsonAduditField: shared implementation for configuration revision tracking" (new per-record revision metadata; potentially useful to an inspector); "acl: fix API patters for GIF/GRE device settings"; "acl: add missing and fix some issues"; "system: change diag.disk ..." is only on `stable/26.7` after the tag, not released.
- Removed: "system: remove periodic backups settings and backend code"; "plugins: os-ndproxy has been removed, use os-ndp-proxy-go instead".

Announced for 27.1 (roadmap): "IPSec: Deprecate IKEv1"; ddclient plugin split in two; native NAT64; scrub rules to MVC. Several roadmap items (menu favourites, grid maximize, VLANs on bridges, max-pkt-rate, endpoint-independent NAT, received-on) already landed in 26.7.2 and 26.7.3, which shows that feature work is backported into the stable series rather than held for the major.

Docs API reference is stale for 26.7: the last commits under `source/development/api` in `opnsense/docs` are "api: update core (stable/26.1)" (2026-01-28), a collection-script run (2026-05-13), and the manual savepoint removal (2026-07-22). No "stable/26.7" regeneration exists as of docs commit `2c85e8a`.
Source: https://github.com/opnsense/docs/commits/master/source/development/api

Security posture: 26.7.1 and 26.7.2 each fixed 4 core advisories, 26.7.3 and 26.7.4 one each (GHSA ids in the changelog files). Do not target bare 26.7.

### 7. Reproducibility of the exact point release

- The official package repo for the series is a single moving directory: https://pkg.opnsense.org/FreeBSD:15:amd64/26.7/latest/ (last modified 2026-09-17).
- The `sets/` directory keeps versioned base and kernel sets (`base-26.7.4-amd64.txz`, `kernel-26.7.4-amd64.txz`, each with `.sig`) but only two packages sets: `packages-26.7-amd64.tar` and `packages-26.7.1-amd64.tar`.
  Source: https://pkg.opnsense.org/FreeBSD:15:amd64/26.7/sets/
- Consequence: a fresh 26.7 install that runs a firmware update gets whatever is newest at that moment, not 26.7.4_1. Once 26.7.5 ships, reproducing 26.7.4_1 exactly from the official mirror does not look possible. Whether a third-party mirror or a self-hosted snapshot is the answer is for the lab tickets.

## Recommendation

1. Declare the v1 compatibility target as **OPNsense Community 26.7.4 (26.7.4_1), amd64, FreeBSD 15.1**, and record the version string the box itself reports at probe time as the ground truth.
2. Read API truth from `opnsense/core@ace3b5b5f856261f77b71bd54f3fe63fa2447a12` and `opnsense/plugins@6cb23d364671d7d409f2e9e9a14987efcc8ccc7e`. Use `opnsense/docs@2c85e8a9ea43f4e008a536734ad428783fae94f9` for prose only.
3. Build the probe VM from `OPNsense-26.7-dvd-amd64.iso.bz2` (SHA-256 `95cafedd...186bfb`, verified against the GitHub changelog copy and the `.sig`), then update. If the update lands on something newer than 26.7.4_1, either accept the newer 26.7.x and re-pin, or snapshot the disk image. Phrase the compatibility claim as "26.7 series, verified at 26.7.N".
4. Expect to re-target to 27.1 in or after January 2027. 26.7 will most likely stop receiving updates around then.

## Open uncertainties

- **No written Community EOL policy found.** The support window above is inferred from release history, not stated by upstream.
- **27.1 has no exact date yet**, only "January 2027". The 26.7.2 notes promised a 27.1 road map "in the next weeks"; the roadmap page already has a 27.1 list, but whether that is the promised update is unknown.
- **Hotfix commit mapping is inferred.** Upstream does not tag `_N` hotfixes; `4fd8ebf` matching 26.7.4_1 rests on the commit message. The hotfix's suricata/unbound changes are ports, not core.
- **Exact FreeBSD patch level at 26.7.4 is not stated** in the notes (last named: 15.1-RELEASE-p3 at 26.7.3). Read `freebsd-version -ku` on the probe VM.
- **Images were not downloaded or verified** in this research; checksums were only compared between two published copies.
- **Pinning to an exact point release may not be reproducible** from official infrastructure once the series moves on (finding 7). Whether other mirrors keep older packages sets was not checked.
- **Forum content was read through a fetch-and-summarize tool**, so forum dates are lower confidence than the GitHub and mirror facts, which were read raw. The board index appears to show last-post times rather than first-post times (26.7.3 is listed there under September 3, while its changelog date is August 27).
- A 26.7.5 could ship at any time given the biweekly cadence; six unreleased commits were already on `stable/26.7` on the research date. Re-check tags before the probe VM is built.
