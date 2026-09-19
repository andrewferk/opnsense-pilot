# MCP Python SDK, protocol revision, and auth deployment for a Streamable HTTP service

Research for [#7](https://github.com/andrewferk/opnsense-pilot/issues/7). State of the world verified on **2026-09-19** against primary sources (spec repo at tag `2026-07-28`, SDK source tarballs at pinned release tags, first-party client docs and source). Nothing here is from memory; where something could not be verified it says so.

## Recommendation

1. **SDK: the official `mcp` package, 2.x line, pinned `mcp>=2.2,<3`** (latest is v2.2.0, 2026-09-07). Use `MCPServer` (the renamed v1 `FastMCP` class) and `streamable_http_app()`. It needs Python >=3.10 and `pydantic>=2.12`, so Python 3.13 + Pydantic v2 fit. Do **not** start on 1.x: it is in maintenance mode (security and critical fixes only) and tops out at protocol `2025-11-25`.
2. **Not FastMCP (PrefectHQ) 4.x for v1.** It is actively maintained and is itself built on `mcp>=2,<3`, so it adds a second dependency layer (authlib, cyclopts, py-key-value-aio, OpenTelemetry, etc.) for features v1 does not need (OAuth proxies, composition, tasks, OpenAPI generation). Its one ergonomic win for us, FastAPI lifespan helpers, is about ten lines by hand. Revisit only if we later want its OAuth providers.
3. **Protocol: serve both eras, which is the SDK's only mode.** One `streamable_http_app()` serves the current revision `2026-07-28` (stateless, no `initialize`, no sessions) and every handshake-era revision (`2024-11-05` .. `2025-11-25`), routed per request by the `MCP-Protocol-Version` header. There is no server-side knob to disable an era, so "pinning" means pinning the SDK version and **asserting the negotiated version in tests**, not configuring the server. Set `stateless_http=True`: v1 tools never call back into the client, so the legacy leg loses nothing and we hold no session state at all.
4. **Auth: a static, high-entropy bearer token checked by our own ASGI middleware in front of the mounted MCP app, served over TLS (or loopback only).** The spec says authorization is OPTIONAL and that HTTP servers SHOULD (not MUST) follow its OAuth 2.1 profile; a static bearer is therefore *permitted* but is *not* the spec's authorization model. It is the only scheme every candidate client supports without us running an OAuth authorization server. The full OAuth resource-server path (RFC 9728 metadata + a real AS) is the spec-conformant upgrade and the SDK supports it via `TokenVerifier` + `AuthSettings`; design the middleware behind a verifier-shaped seam so that upgrade is configuration, not a rewrite. Do not use the SDK's `AuthSettings` with a static token: `issuer_url` is mandatory, so it would publish Protected Resource Metadata pointing at an authorization server that does not exist.
5. **Transport security: pass an explicit `TransportSecuritySettings(allowed_hosts=[...], allowed_origins=[...])` always; never rely on the `host=` default.** Bind uvicorn to `127.0.0.1` by default and make any wider bind an explicit operator setting.
6. **Mount in the FastAPI process** with `app.mount(...)` and enter `mcp.session_manager.run()` from the FastAPI lifespan (mounted sub-app lifespans never run).
7. **Two-client test pair: Claude Code and OpenAI Codex CLI.** Today they land on *different protocol eras and different SDK lineages* against the same server: Claude Code (TypeScript SDK 2.0 runtime) probes HTTP servers for `2026-07-28` and uses it; Codex CLI 0.155.1 (Rust `rmcp` 3.2.0) defaults to the `initialize` handshake at `2025-06-18`, with `2026-07-28` behind an under-development feature flag. Both take a static bearer header from config and both have a headless mode; tool support is documented for both, resource consumption is only partly documented for either and is something the test must establish.

## Findings

### 1. The protocol moved under us: `2026-07-28` is current and is a different shape

- Spec releases (GitHub releases of `modelcontextprotocol/modelcontextprotocol`): `2026-07-28` published 2026-07-28; previous stable `2025-11-25`. Source: <https://github.com/modelcontextprotocol/modelcontextprotocol/releases>.
- Changelog for `2026-07-28` (<https://modelcontextprotocol.io/specification/2026-07-28/changelog>): removes protocol-level sessions and `Mcp-Session-Id` (SEP-2567); removes the `initialize` handshake, every request carries version and client capabilities in `_meta` (SEP-2575); servers MUST implement `server/discover`; the HTTP GET stream and `resources/subscribe` are replaced by `subscriptions/listen`; `ping` and `logging/setLevel` removed; server-to-client requests replaced by Multi Round-Trip Requests; SSE resumability removed; `Mcp-Method` / `Mcp-Name` request headers required (SEP-2243); list/read results carry `ttlMs` and `cacheScope`; resource-not-found becomes `-32602`; Roots, Sampling, Logging and Dynamic Client Registration are deprecated.
- Versioning (<https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning>): "There is no negotiation handshake." An unsupported version MUST get `UnsupportedProtocolVersionError` (`-32022`) listing `supported`. The page defines *modern* (`2026-07-28`+), *legacy* (`2025-11-25` and earlier) and *dual-era* implementations; a dual-era server "MAY serve both eras concurrently on the same endpoint". A legacy-only client against a modern-only server fails with no fall-forward, which is why dual-era serving matters for us.
- Streamable HTTP (<https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http>): single POST endpoint; server answers with JSON or a request-scoped SSE stream; every POST MUST carry `MCP-Protocol-Version` matching the body `_meta`, else `400` + `HeaderMismatch` (`-32020`); unknown method is `404` + `-32601`.

Consequence for the map: any plan text that assumes sessions, `initialize`, or `Mcp-Session-Id` describes the legacy leg only.

### 2. Maintained Python options

| | Official SDK `mcp` 2.x | Official SDK `mcp` 1.x | FastMCP (PrefectHQ) 4.x |
|---|---|---|---|
| Latest (as of 2026-09-19) | v2.2.0, 2026-09-07 | v1.30.0, 2026-09-07 | v4.0.5, 2026-09-17 |
| Status | active: "bug fixes, security fixes, and features" | "critical bug fixes and security fixes" | active, 4.0.0 stable 2026-08-31 |
| Protocol revisions | `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25` via handshake; `2026-07-28` modern | up to `2025-11-25` | same as SDK 2.x (depends on `mcp>=2.0.0,<3.0.0`) |
| Streamable HTTP | yes, dual-era on one app | yes, legacy shape only | yes (`http_app()`), via the SDK |
| Python / Pydantic | >=3.10 (classifiers through 3.14) / `pydantic>=2.12.0` | >=3.10 / `pydantic>=2.11` | >=3.10 / `pydantic[email]>=2.12.0` |
| License | MIT | MIT | Apache-2.0 |

Sources: releases via `gh api repos/modelcontextprotocol/python-sdk/releases` and `repos/PrefectHQ/fastmcp/releases` (the old `jlowin/fastmcp` path redirects there); v2.0.0 release notes <https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0> ("v1.x is in maintenance mode and will only receive security fixes from now on"; "`FastMCP` is now `MCPServer`"); support policy <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/VERSIONING.md>; version tuples <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp-types/mcp_types/version.py>; dependencies in <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/pyproject.toml> and <https://github.com/PrefectHQ/fastmcp/blob/v4.0.5/fastmcp_slim/pyproject.toml>; FastMCP 4.0.0 notes <https://github.com/PrefectHQ/fastmcp/releases/tag/v4.0.0>.

Things worth knowing about SDK 2.x:

- It depends on **`httpx2>=2.5.0`** (PyPI: `pydantic/httpx2`, "The next generation HTTP client"), not `httpx`. If our OPNsense client uses `httpx`, both will coexist in the environment; that is a dependency-hygiene note, not a blocker.
- OpenTelemetry tracing "ships on by default" (v2.0.0 notes). We should decide whether to leave it on; with no exporter configured it should be inert, but that is **unverified**.
- `MCP_*` environment-variable settings were removed along with `pydantic-settings` (v2.0.0 notes), so all server configuration is explicit constructor/keyword arguments. Good for us: no ambient config surface.
- Known gaps per v2.2.0 notes: tasks extension (SEP-2663), DPoP (SEP-1932) and the `jwt-bearer` grant are not implemented. None matter for read-only v1.
- The SDK is young on 2.x: 2.0.0 on 2026-07-28, then 2.0.1, 2.1.0, 2.1.1, 2.2.0 within six weeks, and 2.2.0 changed defaults (idle session expiry, redirect policy). Pin an upper bound and read release notes on every bump.

### 3. Which revisions get negotiated, and how to pin and test that

- Server side: "The SDK routes every request by its `MCP-Protocol-Version` header. A request naming `2026-07-28` goes to the modern handler. A request naming a handshake-era version, or carrying no header at all ... goes to the transport those clients expect." And: "There is no `legacy=` option, no version allowlist, no way to reject or disable an era ... Both eras are always on." Source: <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/run/legacy-clients.md>.
- So the server cannot be pinned to one revision by configuration. What we can do:
  - pin the dependency (`mcp>=2.2,<3`) and lock it;
  - assert, in CI, the set the server advertises: call `server/discover` and check `supported_versions` equals the expected tuple, so an SDK bump that adds or drops a revision fails a test rather than shipping silently;
  - drive both eras from the SDK's own `Client`: `Client(url)` (mode `auto`, lands on `2026-07-28`), `Client(url, mode="legacy")` (forces `initialize`, lands on `2025-11-25`), and `mode="2026-07-28"` (pinned, sends no negotiation). `client.protocol_version` reports what was negotiated. Source: <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/protocol-versions.md>.
  - `Client(mcp)` connects in memory for unit tests, but "skips the HTTP layer, authorization included" (<https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/run/authorization.md>), so transport and auth tests must go over a real socket.
- If we ever need to *refuse* legacy clients, that is our own ASGI middleware rejecting requests whose `MCP-Protocol-Version` is absent or handshake-era. Not recommended for v1: it would lock out Codex CLI's default mode (finding 8).

### 4. What the authorization spec requires of a self-hosted single-user server

Source: <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization> and <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations>.

- "Authorization is **OPTIONAL** for MCP implementations. When supported: Implementations using an HTTP-based transport **SHOULD** conform to this specification."
- *If* we implement the spec's model, the MCP server is an OAuth 2.1 **resource server** and MUST: publish RFC 9728 Protected Resource Metadata; answer unauthenticated requests with `401` + `WWW-Authenticate: Bearer resource_metadata=...`; validate tokens per OAuth 2.1 s5.2; validate that the token's audience is this server (RFC 8707); return `401` for invalid/expired tokens and `403` + `insufficient_scope` for scope failures; never accept tokens in the query string; "MUST NOT accept or transit any other tokens". An authorization server (separate or co-hosted) MUST do OAuth 2.1 + PKCE, MUST expose RFC 8414 or OIDC discovery, SHOULD support Client ID Metadata Documents, MAY support Dynamic Client Registration (now deprecated). All AS endpoints MUST be HTTPS.
- The transport page separately says "Servers **SHOULD** implement proper authentication for all connections", and the security best-practices page says local HTTP servers SHOULD "Require an authorization token" or use restricted IPC (<https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices>, "Local MCP Server Compromise").

Reading for us:

| Deployment | Spec status | Client support (verified) | Operational cost |
|---|---|---|---|
| No auth, loopback bind only | permitted (auth is OPTIONAL) but violates the SHOULD on authenticating connections | all | none; any local process can read firewall config |
| **Static bearer token + TLS (or loopback)** | **permitted; outside the spec's OAuth profile, so "compliant" only in the sense that the profile is a SHOULD** | Claude Code `--header` / `headers` / `headersHelper`; Codex `bearer_token_env_var` / `http_headers` / `env_http_headers` | one secret to generate, store, rotate |
| OAuth 2.1 resource server + self-hosted AS (Keycloak, Authelia, etc.) | the spec's model; simplest *conformant* deployment is RS-only in our process with an external AS | Claude Code (DCR, CIMD, pre-registered client, `claude mcp login`); Codex (`codex mcp login`, CIMD, DCR, pre-registered) | run and secure an identity provider; HTTPS everywhere |
| SDK-embedded AS (`auth_server_provider=`) | works, but SDK docs say it "predates the AS/RS separation ... New servers should not reach for it" | as above | we would own login, consent, token issuance |

Recommendation stands at row two for v1, with row three as the documented upgrade. The static-bearer middleware must: compare in constant time; return `401` with `WWW-Authenticate: Bearer` (no `resource_metadata`, because there is no AS to discover); never log the token; read the token(s) from config/secret storage, not code; support more than one token so each client is individually revocable.

**No token passthrough** is satisfied structurally: the MCP bearer authenticates the *agent to Pilot*; Pilot's OPNsense API key/secret is a separate server-side credential and the inbound token is never forwarded. The spec's rule ("The MCP server **MUST NOT** pass through the token it received from the MCP client") is about exactly this boundary.

### 5. What the SDK gives us for Origin, DNS rebinding, bind, sessions, body limits

Sources: <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp/server/transport_security.py>, <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/run/deploy.md>, <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp/server/mcpserver/server.py> (around the `host in ("127.0.0.1", "localhost", "::1")` branch), <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp/server/streamable_http_manager.py>.

Provided:

- **Host + Origin validation** (`TransportSecuritySettings`): bad `Host` gives `421`, bad `Origin` gives `403` (the spec's MUST), before any MCP parsing, on both the modern and legacy handlers. An absent `Origin` passes, which is what CLI clients send.
- **Default**: with `host` left at `127.0.0.1`/`localhost`/`::1` and no `transport_security=`, protection is armed with a localhost-only allowlist.
- **Trap**: "Passing a non-localhost `host=` ... does **not** allowlist that hostname. It only stops the localhost default from arming the protection, which leaves every Host and Origin accepted." The low-level `TransportSecurityMiddleware(None)` also defaults to protection *off*. Hence recommendation 5: always pass explicit settings.
- **Content-Type check** on POST (`application/json`, else `400`) and a **4 MiB body cap** (`413`).
- **Legacy session isolation**: session IDs are bound to the credential that created them ("A session can only be used with the credential that created it. Respond exactly as if the session did not exist" -> `404`). This binding keys off the SDK's own auth middleware (`scope["user"]` as `AuthenticatedUser`); with our external bearer middleware every requestor is `None`, i.e. sessions are not credential-bound. With `stateless_http=True` there are no sessions to bind, which is another reason to set it.
- **Legacy session limits** (v2.2.0): idle expiry 30 min, max 10 000 sessions; irrelevant when stateless.
- Modern (`2026-07-28`) requests are sessionless by construction.

Not provided, we must add:

- **Bind control**: `streamable_http_app()`'s `host` "binds nothing"; the bind address belongs to uvicorn. Pilot's settings must default to `127.0.0.1` and treat `0.0.0.0` as an explicit opt-in (spec: local servers "SHOULD bind only to localhost").
- **TLS**: terminate at a reverse proxy or uvicorn; if proxied, run uvicorn with `--proxy-headers --forwarded-allow-ips=<proxy>` or redirects downgrade to `http://` and clients refuse them.
- **Authentication** for the static-bearer case (finding 4), rate limiting, audit logging.
- **Health route auth awareness**: `@mcp.custom_route()` routes are "never authenticated"; keep health on the FastAPI side.
- **State-handle binding** if we ever mint handles (pagination cursors, snapshot IDs): spec best practice is to bind them to the authenticated principal and never treat possession as authentication.

### 6. Mounting alongside FastAPI in one ASGI process

Source: <https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/run/asgi.md>.

- `mcp.streamable_http_app()` returns a Starlette app with one route (`/mcp` by default); "anything that hosts ASGI (uvicorn, Hypercorn, another Starlette, FastAPI) can host your MCP server".
- "**a mounted sub-application's lifespan never runs** ... Whichever app sits at the top of your ASGI stack must enter `mcp.session_manager.run()` in its own lifespan." Forgetting it yields `RuntimeError: Task group is not initialized` on the first request. `mcp.session_manager` exists only after `streamable_http_app()` has been called.
- `Mount("/")` swallows every path, so FastAPI's own routes must be registered first; or mount at a prefix with `streamable_http_path="/"`. A prefix mount makes Starlette redirect `/mcp` -> `/mcp/`; configure clients with the exact served URL and keep proxy headers correct (deploy.md).
- The SDK's examples use Starlette, not FastAPI, explicitly. FastAPI is a Starlette subclass so `app.mount()` and `lifespan=` behave the same, and FastMCP's docs show the identical pattern on FastAPI (<https://github.com/PrefectHQ/fastmcp/blob/v4.0.5/docs/integrations/fastapi.mdx>), but we have **not run** SDK 2.2.0 under FastAPI; the transport test should confirm it (test plan step 1).
- Our bearer middleware wraps only the mounted MCP app (pure ASGI, not `BaseHTTPMiddleware`, so SSE streaming is not buffered). The REST API can share the same verifier through a FastAPI dependency.
- Single process, single worker is the v1 shape. If that ever changes: modern requests need nothing; legacy needs sticky routing unless `stateless_http=True`; multi-round-trip tools need shared `RequestStateSecurity` keys. None apply to read-only v1 tools that never ask the client anything.

### 7. Tools and resources

- Both are first-class in `MCPServer`: `@mcp.tool()` (<https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/servers/tools.md>) and `@mcp.resource("scheme://...")` with RFC 6570 templates and default path-safety checks on extracted values (<https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/servers/resources.md>). Structured output is Pydantic-model driven.
- Tool annotations: the SDK documents them as "behavioural **hints** for the client" (`read_only_hint=True` etc.). That matches the project constraint: set `read_only_hint=True` on every v1 tool for honest description, and enforce read-only in Pilot's own adapter layer, never via annotations.
- Era differences that touch us: under `2026-07-28`, list/read results carry `ttlMs`/`cacheScope` (the SDK has `caching.py`; how it defaults these is **unverified**), resource-not-found is `-32602` instead of `-32002`, and tools SHOULD be listed in deterministic order. Resource *subscriptions* differ per era (`subscriptions/listen` vs session stream); v1 should not offer them.
- "Core must work with no model credentials": nothing in the SDK server path needs a model. Sampling is the only model-touching feature; it is deprecated in `2026-07-28` and we will not use it.

### 8. Candidate clients

**Claude Code** (required). Source: <https://code.claude.com/docs/en/mcp>.

- Remote servers: `claude mcp add --transport http <name> <url>`; static auth with `--header "Authorization: Bearer ..."` or `"headers"` in `.mcp.json` with `${VAR}` expansion; `headersHelper` for dynamic headers, re-run on `401`/`403`. SSE is documented as deprecated.
- OAuth: automatic discovery from `WWW-Authenticate`, Dynamic Client Registration, Client ID Metadata Documents, pre-configured `--client-id`/`--client-secret`/`--callback-port`, `claude mcp login`.
- Protocol: "The v2 runtime is the same code on MCP TypeScript SDK 2.0, which adds MCP protocol revision 2026-07-28." It is used on v2.1.232+ in sessions that fetch feature flags and by default on v2.1.274+ otherwise. On v2 it "Asks HTTP servers whether they support the newer revision, and uses it with those that do." Overrides: `MCP_SDK_GENERATION=v1|v2`, `MCP_PROTOCOL_NEGOTIATION=auto|legacy`. Anthropic "can keep a specific server on the earlier protocol ... with a feature flag", so the negotiated version must be *observed*, not assumed.
- Supports `list_changed`. The page refers to a server's "last fetched tools, prompts, and resources", so resources are fetched, but I could not find a current doc section describing how a resource is surfaced to the model or user (`@`-mention or otherwise). Treat resource *consumption* in Claude Code as **not doc-verified**; the test plan checks it.
- Headless runs (`claude -p`) are documented as supporting MCP servers, including reconnects.

**OpenAI Codex CLI** (proposed second client). Sources: <https://learn.chatgpt.com/docs/extend/mcp?surface=cli> (redirect target of `developers.openai.com/codex/mcp`); source at tag `rust-v0.155.1` (2026-09-18).

- Headless mode is the `codex-exec` binary / `codex exec` subcommand (<https://github.com/openai/codex/tree/rust-v0.155.1/codex-rs/exec>); the MCP doc page itself does not discuss MCP under `codex exec`, so that combination is **unverified** until the test runs.
- Streamable HTTP servers configured in `config.toml` (`[mcp_servers.<name>]`) with `url`, `bearer_token_env_var`, `http_headers`, `env_http_headers`, `http_headers_helper`; OAuth via `codex mcp login` with CIMD, DCR, or pre-registered client.
- Built on the official Rust SDK, pinned `rmcp = "=3.2.0"` (<https://github.com/openai/codex/blob/rust-v0.155.1/codex-rs/Cargo.toml>). `rmcp` 3.0 "adds support for MCP 2026-07-28" but the modern lifecycle is opt-in (<https://github.com/modelcontextprotocol/rust-sdk/releases/tag/rmcp-v3.0.0>).
- Codex's default is `McpProtocolMode::Legacy` = `ClientLifecycleMode::Initialize` at `ProtocolVersion::V_2025_06_18`; modern mode (`Auto`, preferring `2026-07-28`, falling back to `2025-06-18`) is gated by feature key `mcp_2026_07_28`, `stage: UnderDevelopment`, `default_enabled: false` (<https://github.com/openai/codex/blob/rust-v0.155.1/codex-rs/rmcp-client/src/protocol_mode.rs>, <https://github.com/openai/codex/blob/rust-v0.155.1/codex-rs/features/src/lib.rs>).
- Resources: the source tree has `list`/`read_mcp_resource` tool handlers (<https://github.com/openai/codex/tree/rust-v0.155.1/codex-rs/core/src/tools/handlers>); the user docs only mention tools and server instructions, so resource behaviour is source-verified but **not doc-verified**.

**Why this pair.** The value of a two-client test is coverage of differences, and these two differ on every axis that matters to a dual-era server: protocol era by default (modern `2026-07-28` vs legacy `2025-06-18`), SDK lineage (TypeScript SDK 2.0 vs Rust `rmcp`), vendor, and config format; while agreeing on what we need (Streamable HTTP, static bearer header, a headless mode, tools; resources to be confirmed by the test). Codex's feature flag also gives a third cell for free: a second independent *modern* implementation.

Rejected or deferred: the **MCP Inspector** and the **Python SDK `Client`** are tools, not agents: use them as the scripted harness, not as one of the two "real clients". **Claude Desktop / claude.ai connectors** reach the server from Anthropic's cloud and effectively require public HTTPS + OAuth, which a LAN-only self-hosted service should not need. **Gemini CLI, VS Code Copilot, Cursor** were not researched in depth (**unverified**); Gemini CLI and VS Code are reasonable alternates if Codex proves unsuitable, but several share the TypeScript SDK lineage with Claude Code, which reduces the independence of the pair.

## Two-client transport test plan

Fixture: a throwaway `MCPServer("pilot-transport-probe")` mounted in a FastAPI app, uvicorn single worker on `127.0.0.1`, Python 3.13, `mcp==2.2.0`. It exposes one tool `echo_inventory(name: str) -> InventoryModel` (Pydantic v2 structured output, `read_only_hint=True`), one static resource `pilot://probe/status`, one template `pilot://probe/items/{item_id}`, plus one FastAPI route `GET /api/health`. Static bearer middleware wraps the mount. `stateless_http=True`. Explicit `TransportSecuritySettings`. Server logs method, `MCP-Protocol-Version`, presence of `Mcp-Session-Id`, and client name for every request (never the token).

Record client versions (`claude --version`, `codex --version`) with the results.

**Step 0: scripted baseline (SDK `Client` + curl, in pytest, over a real socket).**

1. FastAPI mount works: `GET /api/health` is 200 and an MCP call succeeds in the same process; removing the lifespan hook reproduces `Task group is not initialized` (guards the known footgun).
2. `server/discover` returns `supported_versions` equal to the expected tuple for the pinned SDK (snapshot assertion).
3. `Client(url)` negotiates `2026-07-28`; `Client(url, mode="legacy")` negotiates `2025-11-25`; both list the tool, the resource and the template, call the tool, read both resources, and get identical payloads.
4. Legacy leg issues **no** `Mcp-Session-Id` (stateless); `GET` and `DELETE` on `/mcp` behave per SDK (record actual status codes).
5. Version errors: `MCP-Protocol-Version: 1900-01-01` gives `400` + `-32022` with a `supported` list; header/body mismatch gives `400` + `-32020`; unknown method gives `404` + `-32601`.
6. Auth: no token, wrong token, token in query string each give `401` with `WWW-Authenticate: Bearer` and no tool execution; correct token gives 200. The 401 body and logs contain no token material.
7. Transport security: `Host: evil.example` gives `421`; `Origin: https://evil.example` gives `403`; no `Origin` passes; allowed origin passes. Repeat with the server configured for a non-localhost hostname to prove the explicit allowlist is what protects us.
8. Limits: body over 4 MiB gives `413`; wrong `Content-Type` gives `400`.
9. Resource-not-found returns `-32602` on the modern leg; record what the legacy leg returns.

**Step 1: Claude Code.** Configure via `.mcp.json` (`"type": "http"`, `"headers": {"Authorization": "Bearer ${PILOT_MCP_TOKEN}"}`). Run headless (`claude -p`) with a prompt that requires the tool and a resource read.

- Pass: server connects; tool call and resource read succeed; server log shows which protocol version was used. Expected `2026-07-28` on a current build; if it shows legacy, re-run with `MCP_SDK_GENERATION=v2 MCP_PROTOCOL_NEGOTIATION=auto` and record both.
- Force the other era with `MCP_PROTOCOL_NEGOTIATION=legacy` and confirm the same results.
- Negative: wrong token. Record exactly what Claude Code does on a `401` that carries no `resource_metadata` (clean failure vs an OAuth discovery attempt); this decides whether our 401 shape needs adjusting.
- Record whether it opens a `subscriptions/listen` stream and how it behaves when the server offers no `listChanged` capability.

**Step 2: Codex CLI.** Configure `[mcp_servers.pilot]` with `url` and `bearer_token_env_var = "PILOT_MCP_TOKEN"`. Run headless (`codex exec`).

- Pass: connects with the `initialize` handshake; expected negotiated version `2025-06-18`; tool call succeeds; resource list/read succeeds (or record that the model-facing resource tools are absent, which would be a finding).
- Confirm the stateless legacy leg is acceptable to `rmcp` (no `Mcp-Session-Id` returned). If Codex requires a session, re-run with `stateless_http=False` and record it: that would change recommendation 3.
- Optional third cell: enable feature `mcp_2026_07_28` and confirm it lands on `2026-07-28` and still passes.
- Negative: wrong token; record behaviour.

**Step 3: write down the matrix.** Client x version x era negotiated x tools x resources x auth-failure behaviour, plus any SDK defaults we had to override. That table is the deliverable for the transport-test ticket (#14).

## Open questions

1. **Claude Code's reaction to a bare `401`** when a static header is configured is undocumented; it may start OAuth discovery. Test plan step 1 answers it.
2. **Does `rmcp` 3.2.0 in legacy mode tolerate a server that never issues `Mcp-Session-Id`?** Expected yes (sessions were always optional in the legacy transport), unverified.
3. **SDK 2.x defaults we did not read in source**: OpenTelemetry behaviour with no exporter; how `ttlMs`/`cacheScope` default on list/read results; exact `GET`/`DELETE` responses on the modern leg.
4. **SDK 2.2.0 under FastAPI specifically** (rather than bare Starlette) is inferred from FastAPI being a Starlette subclass and from FastMCP's FastAPI docs; not executed here.
5. **Upgrade path to real OAuth**: which self-hosted AS supports Client ID Metadata Documents today is not researched. DCR is deprecated in `2026-07-28` but still what many AS products offer; both target clients support DCR, CIMD and pre-registration, so this is not urgent.
6. **TLS story for LAN deployment** (self-signed vs internal CA vs reverse proxy) is a deployment decision outside this ticket; note that both clients are Node/Rust processes with their own trust-store behaviour, which should be exercised before promising `https://` on a private CA.
7. **SDK churn risk**: five 2.x releases in six weeks with behaviour-changing defaults, and a 3.0 already referenced in deprecation warnings. Mitigation is the `<3` pin plus the `supported_versions` snapshot test.
8. **Alternates for the second client** (Gemini CLI, VS Code, Cursor) were not verified; only needed if Codex is rejected for non-technical reasons.
