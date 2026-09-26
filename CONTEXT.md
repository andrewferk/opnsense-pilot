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

**Coverage**:
What a snapshot says about each inventory category: collected, partial, or not collected, and when not collected, why (no API, privilege denied, export not enabled, plugin absent, outside v1 inventory, unsupported release). An uncollected category is never shown as an empty one.
_Avoid_: Completeness, availability, "empty"

**Evidence source**:
Where a category or a detector's evidence came from: the API, a live config export, or an imported config export, each with its own time. One snapshot may mix sources; the labels say which.
_Avoid_: Data source, origin, channel

**Config export**:
The firewall's whole `config.xml`, fetched live through the backup API or supplied by the administrator as a file. It contains every secret on the firewall and is a private observation. The raw export is parsed and redacted in memory and never stored.
_Avoid_: Backup (also an OPNsense revert target), dump, config file (ambiguous with Pilot's own configuration)

**Redacted export**:
The stored form of a config export: every secret value replaced by a marker that says a value was present, checked by a final scan before anything is kept.
_Avoid_: Sanitized export (the lab's fixture term), cleaned config

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

**Connector**:
The typed httpx adapter that talks to one firewall's native API and can only issue operations that appear in the operation registry.
_Avoid_: Client (implies a general-purpose API client), adapter (any port implementation)

**Operation**:
One reviewed native OPNsense call: a pinned verb and path, a fixed payload shape, the release range it is verified for, the privileges it needs, its side-effect class, the fields to redact, and the source and lab evidence behind it.
_Avoid_: Endpoint (a path can host several operations), call, request

**Candidate operation**:
An operation proposed by source extraction or imported from a third-party map that has not yet been reviewed; never issued by the connector.
_Avoid_: Draft entry, unverified endpoint

**Operation registry**:
The reviewed set of operations the connector may issue, which is the control that makes v1 read-only. An operation outside it cannot be called.
_Avoid_: Endpoint registry, allowlist (the registry is the allowlist), catalog (that is generated corpus material)

**Client token**:
A named static bearer credential that identifies one MCP or REST client to OPNsense Pilot; revocable on its own. Never the OPNsense credential, which is a separate server-side secret.
_Avoid_: API key (collides with the OPNsense API key), access token (implies OAuth issuance)

**Principal**:
The identity a request resolves to and that every authorization decision is scoped to. In v1 a principal is a client token; later it may be an OAuth subject.
_Avoid_: User (v1 has no user accounts), actor (ambiguous with the reference agent), tenant

**Lab controller**:
The Inspect-free library that owns the lab's virtual machines, their network segments, snapshots, and cleanup; pytest, a CLI, and the Inspect provider all drive the same controller.
_Avoid_: Sandbox (that is the Inspect-side adapter), hypervisor driver

**Target environment**:
An Inspect environment a sample can name and read, such as the firewall, that is never the default environment and offers no shell.
_Avoid_: Sandbox (implies executable), guest

**Firewall slot**:
One running OPNsense virtual machine the lab controller lends to a sample and reclaims afterwards; the slot count bounds concurrency.
_Avoid_: Instance, worker, VM pool entry

**Scenario baseline**:
The warm snapshot of a firewall slot taken after scenario configuration is injected; every sample of that scenario starts from it.
_Avoid_: Golden image (the installed image before any scenario), fixture, checkpoint (an Inspect resume artifact)

**Mutation path**:
Any channel by which something inside a sample (agent, tools, scorers) could change firewall state. The lab's invariant is that a sample holds none.
_Avoid_: Write access, escape hatch, side channel

**Support tier**:
Where a registered firewall's release stands against the compatibility target: verified (the read-only suite passed on that build in the lab), assumed (inside the declared range, not yet run), or unsupported (everything else; only the version is read and every category is not collected).
_Avoid_: Compatibility level, supported (ambiguous between verified and assumed), version confidence (that is how well the release is known, not whether it is supported)

**Capability observation**:
What one firewall actually answered for one registered operation: available, privilege denied, absent, or unsupported release. Coverage on a snapshot is derived from observations, so a permission error is never read as a feature being absent.
_Avoid_: Capability (bare; the handoff used it for three different things), probe result, endpoint check
