# OPNsense Pilot

A self-hosted, read-only-first intelligence and operations platform for OPNsense firewalls: version-aware diagnosis and modernization advice backed by evidence.

## Language

**OPNsense Pilot**:
The project and its deliverable; the Python package is `opnsense_pilot` and the CLI is `opnsense-pilot`.
_Avoid_: OPNsense Operator, `opnsense_operator`, operator (reads as a Kubernetes operator)

**Corpus**:
The knowledge base OPNsense Pilot ships: excerpts, citations, and generated catalogs ingested from pinned upstream OPNsense repositories, each keeping its upstream license.
_Avoid_: knowledge base, dataset

**Third-party notices**:
The shipped record of every upstream repository the corpus draws from, the exact commit ingested, and that repository's license text.
_Avoid_: attributions, credits

**Production trial**:
The narrow, opt-in use of explicitly supported low-risk operations against a real firewall (milestone M5).
_Avoid_: Production pilot, pilot (reserved for the project name)
