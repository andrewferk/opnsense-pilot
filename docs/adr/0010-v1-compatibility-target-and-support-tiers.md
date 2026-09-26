---
status: accepted
---

# v1 targets Community 26.7 on amd64 with no plugins, declares support in three tiers from one verified release, and refuses to collect outside them

The handoff asks v1 to name a "tested compatibility target" and to ship a compatibility matrix. [The release research](https://github.com/andrewferk/opnsense-pilot/issues/3) recommended Community 26.7 pinned at 26.7.4, [the version-mapping research](https://github.com/andrewferk/opnsense-pilot/issues/4) showed that only the core build hash maps to one upstream commit, and the [allowlist lab run](https://github.com/andrewferk/opnsense-pilot/issues/13) produced evidence for exactly one build, 26.7.4_1, on a probe VM with no plugins. [ADR 0005](0005-build-the-connector-and-operation-registry.md) already fixes the operation registry's first range as `26.7.x` and [ADR 0008](0008-config-export-is-the-only-gap-path-in-v1.md) fixes the coverage vocabulary. What remained was how far one release's evidence may be stretched, what Pilot does off the map, and which privileges the declaration rests on.

We decided that v1 declares **OPNsense Community 26.7, amd64, range `26.7.x` with a floor of `26.7.4`, verified on `26.7.4_1`, requiring no plugins**, and that every firewall lands in one of three **support tiers**: **verified** (a release the full read-only suite passed on in the lab), **assumed** (in range and at or above the floor, not yet run; collected with a snapshot warning), and **unsupported** (everything else, including 26.7.0 to 26.7.3, Business edition, non-amd64 builds, and `-devel` packages). **On an unsupported firewall Pilot registers it, reads only the network-free system-information operation, marks every category `not collected` with reason `unsupported release`, and every detector abstains.** The **Pilot account holds 26 base privileges**, withholds interface assignments (it opens a configuration write on 26.7.4_1) and all log scopes (not in the inventory, and the privilege also clears logs), holds no plugin privilege, and gains "Diagnostics: Configuration History" only when live export is opted in. The declaration lives in [`docs/compatibility.md`](../compatibility.md), which lists only verified paths; unexercised areas go to the risk register rather than an "unknown" column.

We rejected a single "supported" tier for all of `26.7.x` because it would attribute lab evidence to builds that never received it, and a point release has already changed two paths (gateway groups, interface assignments). We rejected "only exact verified builds are supported" because it would make every hotfix a breaking change for users and hide the fact that the operation set is stable within a release line. We rejected refusing to register unsupported firewalls because a truthful "here is what you run and why Pilot will not read it" is more useful than a refusal, and the network-free version read is safe on any edition. We rejected best-effort collection on unsupported releases because it turns the registry's verified ranges into a suggestion. We rejected plugin-conditional entries and privileges because the plugins repository has no read-only guard on 69 direct saves, so a single plugin page privilege voids the read-only claim. We rejected an "explicitly unknown" column in the public document because it reads as a promise to investigate; the risk register carries that with an owner.

## Considered options

- **Support tiers**: one tier for the range; verified/assumed/unsupported (chosen); exact-build-only.
- **Off the map**: refuse registration; register and collect nothing but the version (chosen); best-effort with a warning.
- **Plugins**: none (chosen); ISC leases as a plugin-conditional entry; declare `os-firewall-legacy` for the detector.
- **Privileges**: the 29-entry lab set as run; drop assignments and logs (chosen); add per-scope log privileges.
- **Capability**: fold into category coverage; keep as an observed availability per firewall (chosen); the handoff's three-entity model.
- **Record**: ticket comment only; document plus this ADR (chosen); document without an ADR.

## Consequences

- **Support tier is orthogonal to version confidence.** Tier says whether Pilot reads the firewall; confidence (`exact` from the build hash, `degraded` from a version string or a user-declared import release) says how well the release is known. An imported export is placed in a tier from the declared release at degraded confidence.
- **Promotion is a lab rerun.** A new `26.7.x` build becomes verified only after the read-only suite is rerun on the probe VM upgraded to it and the registry's per-release paths are updated (gateway groups to API once [core#10909](https://github.com/opnsense/core/pull/10909) ships, interface assignments back to API once [core#10915](https://github.com/opnsense/core/pull/10915) ships). This is a standing v1 maintenance item with its own issue in the plan.
- **A second release line is a fresh declaration**: new registry entries with their own ranges, a new verified build, and a new section in the compatibility document; never an extension of `26.7.x`.
- **Capability observation** enters the glossary: what one firewall actually answered for one operation (available, privilege denied, absent, unsupported release). The registry says what may be called; the observation says what this firewall did; coverage on the snapshot is derived from observations, so `privilege denied` and `no API` stay distinguishable. The handoff's `UNSUPPORTED_CAPABILITY` error means no registered operation for that request on that release.
- **The compatibility document is release-gated content**: every claim in it must trace to a lab run or a pinned source citation, and it changes only through a reviewed pull request alongside the registry change that motivates it.
- **The `plugin absent` coverage reason stays defined but unused in v1**, so a later plugin-aware entry has a home without a vocabulary change.

Decided on [map ticket #21](https://github.com/andrewferk/opnsense-pilot/issues/21) on 2026-09-25.
