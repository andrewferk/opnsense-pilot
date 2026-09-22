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

**Detector**:
A reviewed, deterministic rule that reads collected evidence about one firewall and yields findings, valid only for the releases it has been source-verified against.
_Avoid_: Check, scanner, lint, heuristic

**Finding**:
One detector's result about one firewall: a feature status, a health, the evidence behind them, and a recommended next step.
_Avoid_: Alert, issue, warning, violation

**Feature status**:
Where a configured feature stands in upstream's lifecycle for the installed release (current, legacy but supported, migration available, deprecated, unsupported, unknown). Says nothing about whether it works.
_Avoid_: Legacy status, deprecation level

**Health**:
Whether a configured feature is operating correctly right now. Independent of feature status: a legacy configuration can be healthy and a current one broken. A detector that does not assess health reports it as unknown, never as healthy.
_Avoid_: Status (ambiguous with feature status)

**Abstain**:
A detector returning unknown because the release is outside what it was verified against or required evidence was not collected, naming what is missing. Missing evidence never counts as absence.
_Avoid_: Skip, pass, not applicable

**Embedding provider**:
The configured source of vectors for knowledge retrieval: none (the default), a local provider, or a remote provider.
_Avoid_: Embedding model (that is what a provider serves), vector backend

**Local provider**:
An embedding provider that runs on the service host or its Compose network and has no outbound route. A LAN host is not local; it is a remote provider the administrator trusts.
_Avoid_: On-prem, self-hosted (both include LAN hosts)

**Egress allowlist**:
The single list of hosts the service may reach for any outbound purpose, ingestion and embeddings alike. Anything not on it is unreachable.
_Avoid_: Firewall rules (collides with the OPNsense domain), proxy config

**Private observation**:
Any data captured from a registered firewall (snapshots, inventory, config exports, logs). Never indexed for search, never embedded, never mixed into the corpus, never leaves the service.
_Avoid_: Telemetry, customer data, firewall export (one kind of private observation)

**Public contract**:
A Pydantic model at the MCP, REST, or CLI boundary: the shape a caller sees and the project promises to keep.
_Avoid_: API model, schema (ambiguous with the database schema), DTO

**Domain type**:
A typed Python value that services, detectors, and policy predicates operate on; owes nothing to how it is stored or served.
_Avoid_: Entity (ambiguous with persistence), business object

**Persistence model**:
A SQLAlchemy mapped class describing how a domain type is stored. Lives only inside infrastructure; repositories accept and return domain types, never persistence models.
_Avoid_: Table model, ORM model, database entity
