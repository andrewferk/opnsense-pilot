---
status: accepted
---

# Retrieval is lexical-first; embeddings are opt-in and remote egress is explicit

OPNsense Pilot's knowledge retrieval works with exact-identifier and PostgreSQL full-text search alone, and that is the default: a fresh install configures no embedding provider, downloads no model weights, and opens no outbound socket for embeddings. Vector retrieval exists behind a provider-neutral interface and turns on only when configuration names a provider. A **local provider** runs on the service host or its Compose network with no outbound route; the v1 reference is an in-process ONNX model shipped as an optional extra (`opnsense-pilot[embeddings]`), so the base install stays light. A **remote provider** is any embedding endpoint beyond that boundary, including a trusted LAN host, and it requires two separate settings to agree: the provider configuration and an entry in the service's single **egress allowlist**. A remote host missing from the allowlist fails closed at startup. Remote embedding necessarily sends query text off the machine, and users type firewall facts into queries, so that egress is documented as such rather than papered over with redaction. **Private observations** (anything captured from a registered firewall) are structured records queried by firewall id and field; v1 builds no full-text index and no vectors over them, and they are never mixed into the public corpus.

We chose lexical-first over embed-by-default, the usual shape of a retrieval-augmented system, because the corpus is source code and reference documentation where exact symbols, paths, and config keys dominate, and because the handoff's goals of reproducibility without a hosted service and restricted egress outweigh the recall an embedding adds. The trade-off is weaker semantic recall out of the box; the provider interface keeps that recoverable per install without changing the default.

## Consequences

- The v1 release gate runs in lexical-only mode. One deterministic retrieval regression runs with the local provider against a small fixed corpus and asserts that the expected top-k results appear (order within k not asserted), so the fusion path is exercised without pinning float behaviour across CPUs.
- The remote adapter speaks the OpenAI-compatible embeddings API, which covers hosted vendors and self-hosted servers (Ollama, llama.cpp) with one thin HTTP client. CI tests it against a stub server, never a real vendor.
- The egress allowlist is one mechanism for every outbound host, ingestion included. Upstream sources (GitHub, docs.opnsense.org, the package mirror) are in the default list; embedding hosts never are.
- Provider, model, and revision are part of a corpus generation's identity. Changing any of them forces a full re-embed into a new generation; the previous generation stays queryable until the new one is promoted, matching the atomic-promotion rule for ingestion. Vectors from different models are never mixed.
- Release artifacts ship chunks and provenance, not precomputed vectors; each install builds its own generation with the provider it configured. Revisit only if ingestion time on the lab machine proves painful.
- Provider choice and endpoint live in the settings file with environment overrides; any secret comes from the environment or a secret file, never the settings file. The corpus generation records what was actually used, so the database holds the audit copy.
- Searching a user's own firewall data ("search my firewall") is a separate future decision, not a gap in this one.
- Decided on map ticket [#18](https://github.com/andrewferk/opnsense-pilot/issues/18).
