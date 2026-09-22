---
status: accepted
---

# Code ships under BSD-2-Clause; upstream material keeps its own license

OPNsense Pilot's code and documentation are licensed under BSD-2-Clause, the same license as `opnsense/core`, `opnsense/plugins`, `opnsense/docs`, and `opnsense/tools`. Ingested upstream material (source excerpts, documentation excerpts, generated API catalogs, evidence citations, sanitized fixtures derived from upstream shapes) is not relicensed: it keeps its original terms and travels with a `THIRD-PARTY-NOTICES.md` that reproduces each upstream `LICENSE` at the exact commit ingested. Contributions are accepted under the same license as the project (inbound = outbound); there is no CLA.

We chose a permissive license for a self-hosted network service, where AGPL is the usual instinct, because contributing back to `opnsense/*` matters more than preventing closed hosted forks, and the patent exposure of a read-only inspection tool written by an individual is low. Apache-2.0's patent grant and trademark clause were not worth losing frictionless upstream contribution. The GPL family was ruled out because it would force the license on anyone embedding the Python package and would not permit upstream contribution without relicensing.

## Consequences

- The reuse decision may only adopt permissively licensed clients or MCP code. GPL or AGPL candidates (for example `mtreinish/pyopnsense`, GPL-3.0-or-later) are excluded; adopting one would mean reopening this decision explicitly.
- The knowledge corpus and fixtures are shipped inside release artifacts (repository, wheel, container), not rebuilt by every user from upstream. Shipping obliges us only to retain notices, so every corpus artifact carries an SPDX identifier and copyright line, and every release includes `THIRD-PARTY-NOTICES.md`. The rebuild path stays reproducible from the pinned refs recorded in corpus metadata.
- Exclusions from the corpus and from any artifact: OPNsense installation media and derived VM images (lab tooling ships recipes that fetch and checksum the official image), upstream logos and documentation images, and `security/intrusion-detection-content-pt-open` (custom no-modification license).
- Relicensing later is possible only while every contribution is under inbound = outbound terms from identifiable contributors; the option narrows as contributors arrive.
- The copyright line names the author, not the project, because the trademark question over the name "OPNsense Pilot" is still open (map ticket [#23](https://github.com/andrewferk/opnsense-pilot/issues/23)). The notices file carries a non-affiliation disclaimer until that is settled.
- This is an engineering reading of the licenses, not legal advice. Evidence: [upstream licensing research](https://github.com/andrewferk/opnsense-pilot/blob/research/upstream-licenses-and-redistribution/docs/research/upstream-licenses-and-redistribution.md).
