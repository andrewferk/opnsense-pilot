# OPNsense Operator — Coding-Agent Handoff

**Status:** implementation brief; architecture baseline agreed, compatibility details require verification.  
**Prepared:** 2026-09-19.  
**First release:** read-only, version-aware diagnosis and modernization advice.  
**Working name:** OPNsense Operator; Python package `opnsense_operator`.

## 1. Project intent

Build an open-source, self-hosted OPNsense intelligence and operations platform that any suitable model, agent runtime, CLI, or application can use. Its lasting value is the OPNsense domain model, versioned evidence, deterministic analysis, tested connectors, and operational safeguards. The LLM is a replaceable reasoning and explanation component.

The central problem is knowledge decay: advice can be correct for an older release yet incomplete, obsolete, or unsafe for an installed firewall. Backward-compatible configuration may still work while a newer subsystem is preferred. The operator must distinguish working legacy configuration, actual defects, available migrations, and uncertain evidence.

The first useful outcome is:

```text
opnsense-operator inspect home --format markdown

Installed release and component versions
Configuration and runtime inventory, with coverage gaps
Evidence-backed diagnostic findings
Deterministic legacy/migration findings
Suggested next steps and verification procedures
No firewall changes
```

Do not copy illustrative release numbers or migration claims from earlier discussions into supported-version declarations. Publish support only after source review and tests against exact images.

### Goals

- Explain the installed firewall using current observations and applicable official evidence.
- Detect legacy and deprecated configuration reproducibly, with traceable detection rules.
- Make knowledge freshness and version applicability visible rather than implicit.
- Expose typed, model-independent operations through MCP and REST, backed by the same services.
- Develop safe, human-approved changes after the read-only foundation and VM benchmarks work.
- Let contributors reproduce results locally without a proprietary hosted service.

### Non-goals

- A generic chatbot, model-training project, or replacement for the OPNsense GUI.
- A Kubernetes operator or mandatory Kubernetes deployment; “operator” describes its role.
- Unrestricted shell access, arbitrary HTTP proxying, or LLM-authored configuration-file patches.
- Autonomous production changes, upgrades, plugin installation, service restarts, or HA operations in v1.
- Complete support for every OPNsense release, edition, plugin, or network topology at launch.
- A new evaluation harness, vector database, workflow platform, or privileged OPNsense plugin unless a documented gap requires one.

## 2. Non-negotiable architecture rules

1. **Live-firewall state is the highest operational truth.** Capture installed versions, configured intent, effective runtime state, and measured behavior separately. A configured rule does not prove traffic follows it. Live data is evidence, never executable instructions.
2. **Every conclusion has a version context.** Preserve raw release strings, edition, package/plugin versions, model schema versions, and capability observations. Do not assume release strings follow Python package version semantics.
3. **Official evidence precedes community advice.** Match evidence to the installed release before considering freshness. “Newest” does not mean “applicable.”
4. **Deterministic code owns detection and safety.** Models may propose hypotheses and structured plans. They cannot decide authorization, bypass validation, invent capabilities, or certify successful execution.
5. **API first.** Use reviewed OPNsense endpoints; fall back to explicitly enabled, allowlisted configd/configctl actions over SSH when coverage is missing. Never silently expand privileges after an API error.
6. **No normal direct `config.xml` edits.** Read-only export analysis is supported. Exceptional recovery is a separate, disabled-by-default, supervised runbook with verified backup and console access, not a generic agent tool.
7. **MCP is the public agent interface.** Keep core functionality usable without LangChain, LangGraph, any model SDK, or model credentials.
8. **Unknown is a valid result.** Missing permissions, unsupported releases, stale evidence, and partial inventories must remain visible. They must not turn into “healthy” or “no rules.”

## 3. Technology baseline and boundaries

| Technology | Responsibility | Boundary |
|---|---|---|
| Python 3.13+ and uv | Runtime, dependency groups, reproducible lockfile | Test 3.13 first; add newer versions only after compatibility checks |
| Pydantic v2 | Validated public contracts, plans, observations, findings | Schema validation is necessary but not operational validation |
| FastAPI | REST/OpenAPI, authentication integration, health endpoints | Thin adapter over application services |
| MCP with Streamable HTTP | Public tools and evidence resources | Use a maintained SDK; pin/test the negotiated protocol version |
| httpx | Async OPNsense API client | Verified TLS, bounded requests, typed operation registry |
| AsyncSSH | Optional configctl and diagnostic fallback | Verified host keys; no caller-provided commands |
| lxml | Config exports and model XML | Disable DTD/entity/network resolution; enforce size/depth limits |
| Tree-sitter | Structural PHP/Python source extraction | Parse upstream source as data; never execute it |
| PostgreSQL + pgvector + PostgreSQL FTS | Metadata, evidence, audit/workflow records, hybrid search | Include exact identifier search; FTS alone is not a code-symbol index |
| LangChain + LangGraph | Optional model/tool adapters and reference-agent orchestration | No domain rules or authorization exclusively in prompts or graph nodes |
| Inspect AI | Primary agent/system evaluation harness | Custom OPNsense datasets, environments, and scorers; reuse the runner |
| pytest + Hypothesis | Deterministic unit, property, contract, integration tests | Core tests require no model API |
| Promptfoo | Adversarial inputs, injection, tool abuse, security regression | Complement Inspect; pin its separate runtime/toolchain |
| OpenTelemetry | Vendor-neutral traces, metrics, correlation | Redact before export; capture no hidden reasoning |
| Optional LangSmith | Opt-in agent/retrieval debugging | Disabled by default; never required for operation or evaluation |
| Docker/Compose | Self-hosted services and reproducible development | OPNsense itself runs in a VM, not a Linux container |
| GitHub Actions | CI, ingestion checks, release artifacts | Privileged VM jobs require isolated, trusted runners |
| Proxmox / QEMU / Packer | Disposable OPNsense lab and image builds | Hypervisor credentials stay outside the agent boundary |

Use one Python distribution initially with optional `agent`, `ssh`, and `eval` extras and development dependency groups. Choose the PostgreSQL driver and migration library through a short ADR; do not create a monorepo of separately published packages prematurely.

LangGraph supplies orchestration primitives, but durable graph state does not make remote firewall operations transactional. The application must persist operation records and reconcile uncertain outcomes. See the [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview).

### Logical architecture

```text
External MCP clients       REST / CLI        Optional reference agent
          |                     |           LangChain + LangGraph
          +---------------------+---------------------+
                                |
                   Authenticated transport adapters
                                |
                     Application/domain services
                +---------------+----------------+
                |               |                |
          Observation      Analysis / policy    Knowledge
          and connectors   planning / workflow  and retrieval
                |               |                |
           httpx / SSH     Operation journal    PostgreSQL
                |                            pgvector + FTS
             OPNsense                           |
                                          Official sources

Inspect + lab controller -> isolated topology -> independent scorers
OpenTelemetry spans cross all service boundaries, with redacted attributes.
```

### Domain ownership

| Domain | Owns | Must not own |
|---|---|---|
| Inventory/observation | Capabilities, snapshots, freshness, configured/runtime distinction | Diagnosis inferred from absent data |
| Connectors | Version-specific requests, response decoding, transport failure classification | Model prompts or generic command execution |
| Configuration | Safe parsing, normalized entities, stable identity, semantic diffs | Applying rewritten XML |
| Knowledge | Source provenance, version mapping, structural chunks, retrieval | Credentials or raw private firewall exports |
| Analysis | Deterministic predicates, evidence-backed findings, migration applicability | Automatic migration execution |
| Planning/policy | Typed actions, preconditions, invariants, risk and permission checks | Reliance on an LLM to enforce policy |
| Execution | Backups, approved operations, verification, rollback journal | Generating new actions during apply |
| Orchestration | Question interpretation, tool selection, explanation, workflow presentation | Direct access to secrets, SSH, database bypasses |
| Evaluation/lab | Scenario setup, independent ground truth, packet behavior scoring | Letting the agent access scorer credentials |

Dependency direction: adapters and orchestration depend on application services; services depend on domain types and ports; infrastructure implements those ports. Enforce import boundaries in CI.

## 4. Initial repository structure

```text
PROJECT_HANDOFF.md
README.md
AGENTS.md
CONTEXT.md                       # shared domain vocabulary
LICENSE
CONTRIBUTING.md
SECURITY.md
pyproject.toml
uv.lock
compose.yaml
.env.example                     # placeholders only
src/opnsense_operator/
  domain/                        # contracts, identities, errors, invariants
  application/                   # use cases and ports
  connectors/                    # httpx, endpoint registry, optional AsyncSSH
  configuration/                 # XML parsing, normalization, semantic diff
  knowledge/                     # ingestion, provenance, version applicability
  retrieval/                     # exact, FTS, vector, ranked evidence
  analysis/                      # diagnostics and deterministic migration rules
  planning/                      # proposed actions, policy, validation
  execution/                     # reserved for later gated write milestones
  persistence/                   # repositories and transaction boundaries
  api/                           # FastAPI routes
  mcp/                           # tools, resources, transport wiring
  cli/
  observability/
agents/reference/                # optional LangChain/LangGraph client
migrations/                      # operator database migrations
rules/                           # reviewed OPNsense detection rule definitions
ingestion/sources.yaml           # allowlisted sources and pinned refs
tests/
  unit/
  property/
  contract/
  integration/
  fixtures/                      # synthetic or reviewed, sanitized captures
evals/
  inspect/                       # tasks, agent adapters, scorers
  datasets/
  promptfoo/
lab/
  packer/
  proxmox/
  qemu/
  topologies/
  scenarios/
  manifests/                     # image checksum, release, packages, provenance
docker/
docs/
  adr/
  research/
  compatibility.md
  threat-model.md
  runbooks/
.github/workflows/
```

Keep upstream source clones, database files, secrets, VM images, and eval logs out of Git. Preserve links and reproducibility manifests instead. Do not fill future directories with speculative frameworks.

## 5. Version-aware evidence and knowledge ingestion

### Evidence hierarchy

Use two related questions: **what is happening here?** and **what does this release support or recommend?**

1. **Current local observations:** installed packages, available APIs, configured values, loaded runtime state, logs, and scoped measurements. Record capture times and permissions. Distinguish a hypothesis from a measured fact.
2. **Exact-version official implementation:** tagged/pinned core and plugin source, controllers, model XML, migrations, templates, configd actions. This establishes actual implementation semantics.
3. **Applicable official release notes and upgrade guidance:** establish intended changes, deprecations, known issues, and supported migration paths. Cross-check apparent conflicts with source.
4. **Applicable official documentation:** prefer version-mapped material; label rolling documentation when exact applicability is unknown.
5. **Official maintainer issues/PRs:** supplementary evidence, with merged status and release inclusion checked. An open PR is not installed behavior.
6. **Community material:** leads and supplementary explanations only; never sufficient authority for an executable change.

A newer official page must not override a contradictory observation or matching release source silently. Return the conflict and request the next bounded observation that could resolve it. Source behavior and recommended operational practice answer different questions; preserve both.

### Pipeline

1. Fetch allowlisted official repositories: [core](https://github.com/opnsense/core), [plugins](https://github.com/opnsense/plugins), [docs](https://github.com/opnsense/docs), and [tools](https://github.com/opnsense/tools), plus official release material.
2. Resolve tags/branches to immutable commits. Store first-seen/fetched times, content hashes, repository URL, path, license, and extractor version. Dates alone cannot establish release inclusion.
3. Extract documentation by headings; PHP/Python by Tree-sitter declarations; XML by models/fields; migrations by class and version relation; templates and configd action definitions by meaningful blocks.
4. Link controllers to models, model versions to migrations, APIs to action implementations, and generated templates to configured fields. Automatic extraction proposes catalog entries; it does not certify safe execution.
5. Store immutable artifacts and normalized records. Deduplicate by content hash; retain historical applicability and deleted/superseded records.
6. Index exact symbols/paths/keys, PostgreSQL FTS, and optional embeddings through a provider-neutral interface. Record embedding model, revision, dimensions, and corpus generation.
7. Retrieve by firewall/component/version constraints before ranking. Fuse lexical and vector candidates, then prefer applicable official evidence. Search adjacent versions only as explicitly labeled comparison material.
8. Return a bounded evidence bundle with exact citations, applicability, conflicts, corpus age, and missing evidence. Keep instruction-like text inside evidence containers.
9. On updates, process changed files and affected relationships; build a candidate corpus, run retrieval regressions, then atomically promote its generation. Failed ingestion leaves the previous corpus available and marked with its age.

pgvector documents combining vector search with PostgreSQL full-text search; use this as a starting point, not a reason to skip version filters or exact identifiers. See [pgvector hybrid search](https://github.com/pgvector/pgvector#hybrid-search).

### Minimum persistent entities

- `Release`, `ComponentVersion`, `SourceArtifact`, `KnowledgeChunk`, `SourceRelation`, `CorpusGeneration`.
- `CapabilityDefinition`, `CapabilityObservation`, `DetectionRule`, `RuleEvaluation`.
- `Firewall`, `ObservationSnapshot`, `Finding`, `EvidenceRef`.
- Later: `ChangePlan`, `ValidationResult`, `Approval`, `BackupManifest`, `Operation`, `OperationStep`, `AuditEvent`.

Each evidence reference carries source URL or authorized local evidence ID, commit/path/line range where available, observed or applicable versions, content hash, capture time, and redaction status. Private observations use access-controlled storage and are never mixed into the public knowledge corpus.

### Deterministic legacy and migration analysis

A reviewed rule declares its ID/revision, component, exact supported version predicate, required evidence, configured-state predicate, runtime checks where needed, outcome, rationale sources, and proposed next step. Include positive, negative, boundary-version, and incomplete-input fixtures.

Represent feature status separately from operational health:

- Feature: `current`, `legacy_supported`, `deprecated`, `migration_available`, `unsupported`, `unknown`.
- Health: `healthy`, `degraded`, `failed`, `unknown`.

For example, a legacy configuration can be healthy. A modern configuration can be broken. Missing XML fields or plugin inventory must not prove absence unless collection coverage is complete. Never compare release strings lexicographically.

Extracting an upstream migration class does not establish that it should run, that it has not already run, or that it is reversible. Verify model versions, prerequisites, documented upgrade order, and actual VM behavior. Do not execute upstream migration code inside the operator. For broader transitions such as DHCP backends or NAT representation, investigate exact release-specific applicability before writing a detector.

## 6. Read-only v1 scope and contracts

### Required vertical slice

Register one firewall using administrator-provided connection settings and credential references. Collect version/capability information and a bounded inventory; normalize it; evaluate reviewed rules; retrieve matching evidence; expose the same results through CLI, REST, and MCP. An optional reference agent explains those results with citations.

Target inventory covers interfaces, configured firewall/NAT rules, gateways, routes, services, DNS/DHCP, and WireGuard status where reviewed capabilities permit. Every category reports its coverage. For API blind spots, accept a locally supplied export or separately enabled read-only SSH adapter. Do not require unrestricted root SSH to finish v1.

V1 excludes all firewall mutations, including restart/reload, diagnostics that change state, and update checks that trigger jobs. “Read-only” means no administrative configuration/service mutation; access logs and normal counters may still change. Explicit network probes are deferred or require separate bounded authorization because they generate traffic.

### Core types

| Type | Required fields |
|---|---|
| `FirewallContext` | Firewall ID, raw release, edition, component versions, capability profile, observation time |
| `ObservationSnapshot` | ID, firewall ID, context, configured/runtime data, per-section collection times, coverage, errors, evidence IDs, fingerprint |
| `Finding` | Rule ID/revision, feature status, health, severity, affected entities, evidence IDs, uncertainty, recommended next step |
| `EvidenceBundle` | Query, version filters, corpus generation, sources, conflicts, freshness |
| `ChangePlan` (later) | ID/revision/hash, target, base fingerprint, typed actions, preconditions, expected effects, risks, invariants, backup/rollback/verification specifications |

All operations return a typed envelope with `request_id`, `firewall_id` when relevant, `observed_at`, `data`, `coverage`, `warnings`, `evidence_refs`, and structured errors. Collection across endpoints is not atomic: report start/end times and detect intervening configuration drift where possible.

Error codes include `UNAUTHORIZED`, `UNSUPPORTED_CAPABILITY`, `UNSUPPORTED_VERSION`, `STALE_OBSERVATION`, `PARTIAL_OBSERVATION`, `UPSTREAM_TIMEOUT`, `UPSTREAM_SCHEMA_CHANGED`, and `POLICY_DENIED`. Later add `APPROVAL_INVALID`, `PRECONDITION_FAILED`, `OUTCOME_UNKNOWN`, and `ROLLBACK_FAILED`.

### Proposed public tools and REST routes

These names are **operator contracts**, not claims about native OPNsense endpoint names. Prefix REST routes with `/v1`. Authenticate and authorize every target-specific request.

| MCP tool | REST equivalent | Inputs/result |
|---|---|---|
| `opnsense_get_system_info` | `GET /firewalls/{id}/system` | Context, capabilities, freshness |
| `opnsense_get_interfaces` | `GET /firewalls/{id}/interfaces` | Configured and observed interface state |
| `opnsense_get_firewall_rules` | `GET /firewalls/{id}/rules` | Ordered rules, aliases, NAT relations, coverage |
| `opnsense_get_gateways` | `GET /firewalls/{id}/gateways` | Configuration and observed health |
| `opnsense_get_routes` | `GET /firewalls/{id}/routes` | Configured routes versus runtime table |
| `opnsense_get_services` | `GET /firewalls/{id}/services` | Bounded status inventory |
| `opnsense_get_wireguard_status` | `GET /firewalls/{id}/wireguard` | Redacted configuration and status |
| `opnsense_get_logs` | `GET /firewalls/{id}/logs` | Enumerated source, time window, cursor, capped limit |
| `opnsense_collect_snapshot` | `POST /firewalls/{id}/snapshots` | Allowlisted scope; immutable observation ID |
| `opnsense_analyze_configuration` | `POST /analyses` | Authorized snapshot ID; findings and evidence |
| `opnsense_check_legacy_configuration` | `POST /analyses/legacy` | Snapshot ID; deterministic rule results |
| `opnsense_search_knowledge` | `POST /knowledge/search` | Query and version context; cited evidence bundle |
| `opnsense_recommend_migrations` | `POST /analyses/migrations` | Snapshot ID; applicability, prerequisites, uncertainty |

POST on the operator may persist an analysis without changing the firewall. Expose evidence as access-controlled MCP resources such as `opnsense://snapshots/{id}` and `opnsense://evidence/{id}`. Resource IDs are not bearer credentials. Never return full secret-bearing exports to an agent.

Future contracts: `opnsense_create_change_plan`, `opnsense_validate_change_plan`, `opnsense_apply_change_plan`, `opnsense_get_operation`, and `opnsense_rollback_change`. REST equivalents are `/firewalls/{id}/plans`, `/plans/{id}/validate`, `/plans/{id}/apply`, `/operations/{id}`, and `/operations/{id}/rollback`. Approval uses a separate authenticated human channel, `POST /plans/{id}/approvals`; the model cannot approve its own proposal. Apply returns an operation ID, not immediate success.

### Native OPNsense adapter requirements

The official API uses `/api/<module>/<controller>/<command>`. Its documentation includes `POST /api/core/service/search` as a read/search example; HTTP verb alone therefore cannot enforce read-only behavior. Review and allowlist operation semantics and fixed payload shapes. See the [OPNsense API reference](https://docs.opnsense.org/development/api.html).

Investigate `GET /api/core/firmware/status` as an initial version/status candidate, validating its response and side effects for each supported release. Do not mistake upgrade metadata for installed version. See the [firmware API documentation](https://docs.opnsense.org/development/api/core/firmware.html).

Every native mapping records release/component applicability, method/path, input/output schema, privilege needs, side effects, timeout, retry policy, source evidence, and passing lab tests. Capability discovery must use safe probes, not arbitrary endpoint enumeration. A permission error is not evidence that a feature is absent.

Read retry policy: bounded backoff and deadlines. Mutation retry policy, later: reconcile current state before any retry when outcome is uncertain. Do not assume a remote API honors an operator-generated idempotency key.

For SSH fallback, map typed operations to reviewed configctl actions or fixed diagnostic commands, with validated argument construction and bounded output. Configd actions can mutate state; classify each action independently. See [Using configd](https://docs.opnsense.org/development/backend/configd.html).

## 7. Safe change lifecycle — later milestones

```text
observe -> diagnose -> plan -> validate -> approve -> backup -> apply -> verify
                                                                     |
                                       failed verification/apply ----+-> rollback
                                                                          |
                                                               verify restoration
```

Rollback is a conditional recovery branch, not a mandatory final step after success. Any failed prerequisite stops before apply. Rollback failure or loss of observability produces an explicit recovery-required state.

| Stage | Required behavior |
|---|---|
| Observe | Fresh, authorized snapshot; identify target, release, capabilities, management path |
| Diagnose | Separate observations, deterministic findings, and model hypotheses |
| Plan | Typed allowlisted actions; affected objects; expected diff; dependencies; verification and recovery procedure |
| Validate | Schema, authorization, version, capability, topology, rule order, references, policy, management reachability, rollback feasibility |
| Approve | Human reviews exact plan and risks; approval binds actor, target, plan hash, base state, scope, and expiry |
| Backup | Capture encrypted pre-change backup; verify integrity, version context, restore procedure, and accessibility outside the firewall |
| Apply | Acquire target lock; recheck approval/preconditions; persist step intent before dispatch; reconcile responses; perform only approved actions |
| Verify | Check configured and effective state plus independent network invariants; produce evidence rather than a success narrative |
| Rollback | Run prevalidated recovery steps; verify restoration and management access; escalate through the documented console procedure if recovery fails |

Revalidate after approval and immediately before dispatch. State drift, changed plan content, or a different package version invalidates approval. Operator locks prevent competing operator writes but do not stop manual GUI changes; use upstream concurrency controls where available and document residual race windows. Refuse high-risk execution if state cannot be checked adequately.

Persist an operation journal in PostgreSQL with step IDs, request hashes, expected effects, observed results, approval and backup references, and terminal status. After a crash, reconcile actual firewall state before continuing. Never replay an entire graph blindly. Compensation and configuration restore are not universally equivalent, especially across upgrades.

For changes that can break management access, require an independently reachable recovery path and a lab-tested rollback mechanism. Timed rollback is usable only when verified for the exact subsystem/release. Unsupported recovery means the change stays advisory. Backups alone do not prove recoverability.

Required invariants include management access, unrelated client connectivity, no unintended exposure, intended DNS and routing behavior, and no forbidden WAN fallback. Define IPv4 and IPv6 behavior explicitly. V1 reports these as proposed checks, without claiming to have tested them.

## 8. Security and trust model

The primary threats are malicious text in retrieved sources or logs, tool abuse, credential leakage, cross-firewall access, stale approvals, compromised ingestion, and management lockout.

- **Credentials:** server-side secret references only; dedicated least-privilege OPNsense API accounts; separate read/write identities later. Use mounted secret files or a secret manager; SOPS/age may protect deployment secrets. Never embed keys in prompts, fixtures, URLs, images, or committed configuration.
- **Authorization:** deny by default; scope every operation, resource, snapshot, and plan to the authenticated actor and authorized firewall. A single-user v1 still implements these boundaries.
- **Remote transport:** TLS, explicit authentication, Origin validation, controlled binding, session isolation, limits, and protocol-version negotiation. Use the MCP authorization specification appropriate to the pinned SDK/protocol; no token passthrough to upstream services. MCP tool safety annotations are descriptive, not enforcement. See [MCP Streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).
- **Network boundaries:** registered firewall IDs resolve to administrator-managed destinations. No agent-supplied base URLs, arbitrary redirects, proxy targets, or SSH hosts. Restrict egress, including ingestion and embedding endpoints.
- **Secret handling:** redact private keys, passwords, shared secrets, tokens, and sensitive config fields before model access, tracing, or fixture creation. Keep authorized raw backups encrypted and separately retained; deleting secrets from a displayed report does not sanitize the original artifact.
- **Untrusted content:** docs, code comments, log lines, hostnames, and config descriptions cannot add tools, change policy, request credentials, or grant approval. Retrieval is data, even from official repositories.
- **Parsing/execution:** disable XML external entities and network access; reject oversized inputs; parse upstream code without evaluating it. No arbitrary XPath, SQL, shell, file path, or configctl action from a model.
- **Audit:** record actor, target, operation, evidence IDs, policy result, and correlation ID. For writes, include approval and recovery records. Restrict audit modification privileges; document retention and deletion policy. Avoid raw packet captures or full logs by default.
- **Supply chain:** lock dependencies, pin images/actions, scan secrets and dependencies, preserve source licenses, and review ingestion parser changes. Publish reproducible release metadata and a security-reporting process.
- **Telemetry:** local OpenTelemetry first; external export and LangSmith are explicit opt-ins. Redaction occurs before any exporter or agent tracing callback sees data.

V1 authorization must block mutation at the service and connector boundaries, even when a caller bypasses MCP, crafts a REST request, or convinces the reference agent to request a write. Write handlers are not registered in the v1 public surface.

## 9. Evaluation strategy and VM laboratory

### Three complementary layers

| Layer | Framework | What it establishes |
|---|---|---|
| Deterministic software | pytest + Hypothesis | Parsers, normalization, version rules, policy, redaction, adapters, invariants |
| Agent and full system | Inspect AI | Correct evidence/tool use, diagnosis, abstention, and later real network outcomes |
| Adversarial/security | Promptfoo | Injection resistance, privilege boundaries, exfiltration and unauthorized action attempts |

Inspect supplies datasets, agents/solvers, scorers, logs, and sandbox integration. Implement the OPNsense benchmark within it rather than a separate evaluation runner. See [Inspect documentation](https://inspect.aisi.org.uk/). Promptfoo provides a complementary red-team workflow; use synthetic targets and inspect actual service/connector events, not only model text. See [Promptfoo red teaming](https://www.promptfoo.dev/docs/red-team/).

### Lab topology and lifecycle

```text
Isolated management network: runner -> OPNsense management + console control

LAN test client ----+
Unrelated client ---+---- OPNsense VM ---- WAN simulator / DNS / test web server
VLAN client --------+          |
                         WireGuard peer / VPN egress simulator
```

Use Proxmox for repeatable shared lab runs and QEMU for an alternative local path. Packer builds pinned images from verified installation media. Keep operator/API/DB/collector services in Compose. Maintain separate clean-install and upgraded-system images; an old configuration imported into a clean image is not a substitute for testing the real upgrade path.

Reuse the existing [Inspect Proxmox sandbox project](https://github.com/UKGovernmentBEIS/inspect_proxmox_sandbox) where feasible. First prove its suitability for a multi-VM FreeBSD firewall topology, network isolation, readiness checks, snapshots, and cleanup. Do not assume generic guest execution or a guest agent works on OPNsense. If necessary, add a small Inspect environment adapter around the existing lab controller; keep Inspect as the harness.

Per run: allocate unique network/VM IDs, clone known images, inject scenario configuration, confirm baseline invariants, execute the agent, score independently, collect sanitized artifacts, then destroy/reset everything in a guaranteed cleanup path. Enforce TTL cleanup after worker crashes. Hypervisor access belongs to the trusted runner, never the agent.

Use local WAN/VPN/DNS simulators for deterministic CI. Real commercial VPN connectivity is an optional manually enabled test, not a baseline dependency. Never bridge disposable WAN/LAN segments into production. Preserve management/console access outside the path being tested.

### Initial scenario catalog

| Scenario | V1 expected result | Later execution/packet-level criterion |
|---|---|---|
| Healthy clean install | Correct inventory; no false legacy finding | No regression in baseline connectivity |
| Upgraded legacy configuration | Detect only reviewed applicable legacy rules; cite versioned sources | Supported migration preserves semantic behavior |
| Wrong-release documentation | Prefer matching implementation; label comparisons | Inapplicable plan cannot execute |
| Missing plugin / denied API / partial snapshot | Distinguish absence, denial, and unknown | No unsafe fallback or scope expansion |
| WireGuard route or gateway failure | Identify evidence-supported cause and missing observations | Intended client exits via VPN; unrelated client remains unchanged |
| VPN kill switch | Explain routing, DNS, NAT, state, IPv4/IPv6 checks | VPN up: expected egress; down: no WAN/DNS leak; restored: recovery |
| DNS/DHCP backend transition | Detect supported/deprecated/unknown correctly for exact versions | Leases, resolution, reservations, and service health preserved |
| Multi-WAN and VLAN isolation | Identify gateway policies and isolation concerns without overclaiming | Allowed flows pass; forbidden cross-segment flows fail |
| Hostile log/config/doc text | Ignore injected instructions; preserve evidence as data | No secret access or unauthorized connector event |
| Forged approval / state drift | Deny write requests in v1 | Reject wrong actor, expired approval, changed hash, or stale base state |
| Apply timeout / process crash | Out of v1 execution scope | Reconcile without duplicate mutations; verified rollback if required |
| Rollback / reboot persistence | Offer scoped verification procedure | Restore connectivity and expected config; intended changes survive reboot |

Kill-switch scoring must check new and existing flows, IPv6 if enabled, DNS paths, and packet counters/captures at the test boundary. A failed ping alone does not prove no leakage. Use independent scorer credentials and expected invariants that the agent cannot edit.

### Metrics and gates

Track task success, per-invariant pass rate, legacy-detection precision/recall, correct abstention, citation applicability, retrieval relevance, forbidden tool attempts versus actual executed violations, secret leaks, latency, and model cost. Report sample count, seeds, topology/image manifests, model settings, corpus generation, and failures; never hide failures behind a single average.

V1 release gates: all deterministic tests pass; zero executed firewall mutations; zero known secret leaks or cross-firewall authorization failures in the fixed regression suite; all curated version-boundary fixtures behave as expected. Establish an Inspect baseline and publish observed results before setting broader diagnostic accuracy targets. Later write releases require every safety invariant to pass across the declared scenario/version matrix; a high average cannot compensate for management lockout or leakage.

Core CI runs without models or a hypervisor. Model evaluations and isolated VM runs are additional named jobs; unavailable infrastructure produces an explicit skip, never a fabricated pass. Compare at least two model/provider configurations before claiming reference-agent portability. Do not require every contributor to have paid model access.

## 10. Milestones and definition of done

| Milestone | Deliverable | Exit condition |
|---|---|---|
| M0 — Resolve key unknowns | ADRs, source/endpoint sample, compatibility target, thin lab proof | Exact initial release/edition and tested capabilities selected; risk register has owners and next evidence |
| M1 — Deterministic observer | Safe connector, normalized snapshot, CLI, synthetic fixtures | One real lab firewall inspected; partial coverage and version/schema errors handled; no mutation path |
| M2 — Read-only v1 | Versioned ingestion, hybrid retrieval, reviewed detectors, REST/MCP, optional reference agent | V1 gates pass; cited report works through CLI and MCP; documented Compose setup reproducible |
| M3 — Advisory planning | Typed plans, semantic diffs, policy validator, durable records | Invalid/unsupported/drifted plans rejected; no execution tool exposed |
| M4 — Approved lab changes | Human approval, backup, apply journal, independent verification, rollback | Crash/timeout/drift/lockout scenarios pass in disposable lab; recovery verified |
| M5 — Narrow production pilot | Explicitly supported low-risk operations and operator runbooks | Compatibility matrix, security review, opt-in pilot evidence, and rollback rehearsal complete |

Bounded autonomous remediation is a future decision, not an implied M5 feature. HA, upgrades, and broad migration execution need separate milestones and evidence.

### V1 definition of done

- [ ] Fresh checkout installs with uv and the documented locked environment; Compose starts the service and PostgreSQL with pgvector.
- [ ] Core inspection and deterministic analysis work with no LLM credentials; optional agent dependencies are separable.
- [ ] At least one exact supported release/edition is lab-tested, with one older or upgraded fixture set demonstrating version-aware behavior; limitations are published.
- [ ] Inventory, snapshots, errors, redaction, and analysis contracts are consistent across CLI, REST, and MCP.
- [ ] At least one real, source-verified legacy/migration detector includes positive, negative, boundary-version, and incomplete-data tests.
- [ ] Knowledge retrieval returns immutable citations and corpus/version context; conflicts and stale coverage are visible.
- [ ] Read-only constraints are verified at service and connector boundaries, including adversarial requests.
- [ ] Tests, Inspect baseline, Promptfoo security cases, and a reproducible VM smoke scenario are present with honest run/skip status.
- [ ] OpenTelemetry traces identify observation/retrieval/analysis failures without credentials or raw sensitive payloads.
- [ ] README, compatibility matrix, threat model, contribution guide, security policy, and an owner-selected open-source license are ready for publication.

### Definition of done for each change

Keep a reviewable scope; cite evidence behind OPNsense behavior; add meaningful tests at the changed boundary; update public contracts and compatibility records when needed; document limitations. A change touching execution additionally needs failure, recovery, and approval-bypass tests. Passing mocked API tests does not establish actual network correctness.

## 11. Coding and operational conventions

- Use typed Python with Ruff formatting/linting and one strict type checker selected in M0. Validate untrusted inputs and external responses with Pydantic v2.
- Use async I/O for network work, explicit deadlines, cancellation handling, bounded concurrency, and response limits. Keep domain predicates pure where practical.
- Prefer composition and narrow ports over framework inheritance. Do not import LangChain/LangGraph into domain, policy, parsing, or connector modules.
- Preserve rule ordering, UUIDs, disabled flags, interface identity, address family, gateway selection, direction, logging, and effective defaults in normalization. Unknown fields must not silently disappear from semantic comparisons.
- Use UTC timestamps and explicit freshness windows. Keep configured-state fingerprints separate from volatile counters and secret-redacted display hashes.
- Use stable error codes and explicit partial results. Never turn a transport exception into an empty successful inventory.
- Keep retries operation-specific. Add idempotency and reconciliation before enabling writes, not after a timeout incident.
- Tests should exercise behavior: malformed XML, schema drift, version boundaries, rule precedence, denied permissions, redaction, stale approvals, and recovery. Hypothesis checks invariants over constrained domains; it is not a proof of arbitrary network safety.
- Manage database schema changes as reviewed migrations. Keep persistence models distinct from public tool contracts.
- GitHub Actions runs locked install, lint/types, deterministic tests, contract tests, dependency/secret checks, and container build. Trusted scheduled/manual jobs run ingestion regressions, model evals, and VM suites.
- Fork PRs never receive firewall, model, or hypervisor secrets or access to privileged self-hosted runners. Publish sanitized artifacts with retention limits.
- Scheduled source refresh discovers candidate changes; it never automatically expands production endpoint allowlists, migration rules, or supported-release declarations.
- Choose and document the project license before public release; retain upstream notices and review redistribution of source excerpts, fixtures, and VM media.

## 12. Use `/wayfinder` before committing to uncertain details

The user intends to use [Matt Pocock’s `/wayfinder`](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md). Read its installed, pinned instructions when invoked. It organizes large planning work as a map of decision tickets and is planning-first; distinguish decision resolution from implementation tasks. This handoff does not install or invoke it. Follow its tracker setup, using its documented local-Markdown fallback when appropriate.

Set the destination to **a validated read-only v1 implementation plan with a tested compatibility target**. Seed decisions from this brief; capture evidence and decisions in linked tickets/ADRs. Do not reopen agreed technology choices without a concrete incompatibility. Use research tickets to compare existing OPNsense clients/MCP projects, official API-documentation generators, MCP Python SDKs, and the Inspect Proxmox extension. Evaluate maintenance, license, async support, TLS/ACL defaults, version coverage, tests, and extension cost before reuse or replacement.

Resolve these project-specific unknowns first:

| Decision | Evidence needed | Blocking consequence |
|---|---|---|
| Initial supported release/edition/plugins | Exact image, source refs, API responses, ACL tests | Defines connector and fixture scope |
| Read-only collection coverage | Endpoint side-effect review and limited-account lab run | Determines export/SSH gaps |
| First legacy detector | Actual upstream migration/deprecation evidence and paired fixtures | Prevents invented modernization advice |
| MCP implementation/auth deployment | SDK compatibility and two-client transport test | Defines public service boundary |
| Proxmox/Inspect guest integration | Multi-VM setup/reset/score proof | Determines lab adapter work |
| Release/source mapping | Package-to-source correspondence, branch/tag checks | Determines confidence in citations |
| Reusable client/project versus new adapter | Cited comparison and thin prototype | Prevents unnecessary reimplementation |
| Embeddings/privacy and source licensing | Local/remote configuration and redistribution review | Defines safe knowledge distribution |

Record unresolved questions with an owner, next experiment, and blocking milestone. Keep later write durability, recoverability, and HA questions visible without allowing them to block a useful read-only slice.

## 13. First 10 tasks

Execute in dependency order. Each task should produce a small reviewable change or decision artifact; do not scaffold every future subsystem before obtaining one real observation.

1. **Create the decision baseline.** Read this handoff, create `CONTEXT.md` and initial ADRs, and use `/wayfinder` when invoked to resolve the initial compatibility target and reuse questions. **Done:** exact v1 scope, release/edition, uncertainties, and repository/license decisions recorded.
2. **Bootstrap the Python project and CI.** Add Python 3.13 configuration, uv lockfile, dependency groups/extras, Ruff, the selected type checker, pytest/Hypothesis, and a minimal GitHub Actions workflow. **Done:** a fresh locked install and deterministic CI pass without secrets or model access.
3. **Define contracts and safety ports.** Implement firewall context, capabilities, observations, coverage, evidence, findings, and typed errors; define connector and repository interfaces. **Done:** serialization/error examples and import-boundary tests establish a model-free core.
4. **Prove one isolated VM lab path.** Build or reproducibly prepare the selected OPNsense image using Packer with Proxmox or QEMU, a test client, and isolated management/WAN networks. **Done:** baseline connectivity, console access, reset, and cleanup work; image/source/checksum manifest saved.
5. **Implement the first reviewed HTTP reads.** Verify exact native version/status and service/interface mappings in source and lab; add httpx TLS, limits, redaction, ACL handling, and semantic read-only allowlists. **Done:** the limited account collects real data and mutation/unknown-operation requests fail closed.
6. **Build snapshot normalization and the inspection CLI.** Combine reviewed reads; add safe local XML import for gaps, explicit configured/runtime separation, and coverage/freshness reporting. **Done:** `opnsense-operator inspect <registered-id>` emits useful JSON/Markdown and exposes denied or unsupported sections honestly.
7. **Ingest a narrow official corpus.** Add PostgreSQL migrations and Compose, pin source refs for one subsystem/release pair, extract structural chunks, and implement exact/FTS/vector retrieval with provenance. **Done:** version-conflicting queries return applicable cited evidence, including a lexical-only mode without embedding credentials.
8. **Implement one verified detector end to end.** Select a real legacy/migration case established in task 1/7; add deterministic predicates, evidence requirements, and a human-readable explanation. **Done:** positive, negative, version-boundary, healthy-legacy, and incomplete-input fixtures pass.
9. **Expose REST and MCP, then add the optional agent.** Wire the same services into FastAPI and Streamable HTTP MCP with authentication and target/resource authorization. Add OpenTelemetry redaction and a minimal LangChain/LangGraph reference client. **Done:** CLI and MCP yield equivalent findings; core runs without a model; crafted writes and cross-target requests are denied.
10. **Establish the release benchmark and publish the v1 evidence.** Add Inspect scenarios for healthy, legacy, wrong-version, partial-data, and injection cases; Promptfoo attacks; and an independent VM no-mutation check. Finish the quickstart and compatibility report. **Done:** deterministic gates pass, an actual lab run is recorded, model evals have explicit results or skips, and every v1 checklist item is satisfied before tagging the release.
