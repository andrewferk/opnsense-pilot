# Streamable HTTP transport test: results

Throwaway probe for the wayfinder ticket "Test Streamable HTTP MCP against two real clients" (#14). Run 2026-09-20 on macOS arm64, loopback only.

**Fixture:** `mcp==2.2.0` `MCPServer` mounted in FastAPI 0.141.1 (Starlette 1.6.0), uvicorn 0.53.0, Python 3.13.14, `stateless_http=True`, explicit `TransportSecuritySettings`, static bearer in pure-ASGI middleware, one tool (`echo_inventory`, `read_only_hint=True`, Pydantic structured output), one static resource, one resource template.

**Clients:** Claude Code 2.1.278, OpenAI Codex CLI 0.155.1 (`codex-mcp-client/0.155.1`). Both run headless, configured per invocation (`--mcp-config` / `-c mcp_servers.pilot.*`); no global config was edited.

## Matrix

| Client | Mode | Lifecycle | Negotiated | Tool call | Resources list / read | Templates listed | Session id | Streams opened |
|---|---|---|---|---|---|---|---|---|
| SDK `Client` | `auto` | `server/discover` | `2026-07-28` | ok | ok / ok | yes | none | none |
| SDK `Client` | `legacy` | `initialize` | `2025-11-25` | ok | ok / ok | yes | none | none |
| Claude Code | default | `server/discover` | `2026-07-28` | ok | ok / ok | **never requested** | none | `subscriptions/listen` (POST) |
| Claude Code | `MCP_PROTOCOL_NEGOTIATION=legacy` | `initialize` | `2025-11-25` | ok | ok / ok | **never requested** | none | standalone `GET /mcp` SSE (200) |
| Codex CLI | default | `initialize` | `2025-06-18` | ok | ok / ok | yes | none | none |
| Codex CLI | `--enable mcp_2026_07_28` | `server/discover` | `2026-07-28` | ok | ok / ok | yes | none | none |

Payloads were identical in every cell. Every prediction in the research's test plan held.

## Auth-failure behaviour (wrong token; server answers bare `401` + `WWW-Authenticate: Bearer`, no `resource_metadata`)

- **Claude Code:** two requests (one modern probe, one legacy attempt), both 401, then stops. Reports `AUTH_HEADER_REJECTED` and states "OAuth fallback is disabled when `headers.Authorization` is set". No `.well-known` discovery request reached the server. Session continues without the server's tools.
- **Codex CLI:** two `initialize` attempts, both 401, then `AuthRequired(www_authenticate_header: "Bearer")`; MCP startup fails, the run continues and each MCP tool call reports "Auth required". No OAuth discovery. Error text is noisy but unambiguous.
- Conclusion: the bare 401 shape needs no adjustment for either client.

## Scripted baseline (`test_baseline.py`, 17 tests, all pass)

- FastAPI route and MCP share one process; omitting `session_manager.run()` from the host lifespan reproduces `RuntimeError: Task group is not initialized` as HTTP 500.
- `server/discover` `supportedVersions == ["2026-07-28"]` (equals `MODERN_PROTOCOL_VERSIONS`); handshake-era versions are not advertised there, they are reached via `initialize`.
- Stateless legacy leg never emits `Mcp-Session-Id`. `GET`: 406 without `text/event-stream`, otherwise opens an SSE stream (legacy) / 405 (modern). `DELETE`: 405 in both eras.
- Version errors: unsupported version 400 + `-32022` with `data.supported`; header/body mismatch 400 + `-32020`; unknown method 404 + `-32601`.
- Auth: no token, wrong token, token in query string all 401 with `WWW-Authenticate: Bearer`, no token material in the body, no tool execution.
- Transport security: bad `Host` 421, bad `Origin` 403, absent or allowed `Origin` passes. With `allowed_hosts=["pilot.lan:*"]`, `127.0.0.1` itself is rejected (421): the explicit list is the control.
- Limits: body over 4 MiB 413; wrong `Content-Type` 400.
- Resource not found: `-32602` in **both** eras (HTTP 400 modern, HTTP 200 legacy); the legacy `-32002` is not used by this SDK.

## Findings that matter for the v1 plan

1. **Recommendation stands.** `mcp` 2.2.0, stateless, static bearer middleware, FastAPI mount: works with both clients in both eras. `stateless_http` stays `True`; `rmcp` does not need a session.
2. **Do not rely on resource templates for discoverability.** Claude Code never calls `resources/templates/list`; a templated resource is readable only if the model already knows the URI. Anything an agent must find should be a tool or a listed static resource.
3. **Resources are model-facing in both clients** via generic tools: Claude Code `ListMcpResourcesTool` / `ReadMcpResourceTool` (loaded through its tool search), Codex `list_mcp_resources` / `list_mcp_resource_templates` / `read_mcp_resource`.
4. **The SDK over-advertises capabilities by default:** `resources.subscribe: true` and `listChanged: true` for tools, resources and prompts, although the probe offers none. Claude Code responds by opening a long-lived stream in both eras (and calls `prompts/list`). Harmless here, but v1 should either trim advertised capabilities or accept one idle stream per Claude Code session.
5. **Era is visible per request:** modern requests carry client identity in `_meta` on every call; legacy only on `initialize`. With a stateless server, legacy requests after `initialize` cannot be attributed to a client name, only to a `User-Agent`.
6. **Defaults we had to set explicitly:** `stateless_http=True`, `TransportSecuritySettings` allowlists, host-app lifespan entering `session_manager.run()`, `Mount("/")` registered after FastAPI routes. Noted, not overridden: OpenTelemetry middleware is always installed (no-op without a provider); `MCPServer()` calls `logging.basicConfig` globally; cache hints default to `ttlMs: 0`, `cacheScope: "private"`.

## Not covered

TLS and private-CA trust in either client; non-loopback deployment; OAuth resource-server mode; interactive (non-headless) sessions; `list_changed` notifications actually firing.

## Reproduce

```sh
cd prototypes/mcp-transport-probe
mise exec uv@0.11.29 python@3.13.14 -- uv run pytest test_baseline.py -q
sh run_server.sh /some/state-dir          # terminal 1; writes token + requests.jsonl there
sh run_claude.sh /some/state-dir default good
sh run_claude.sh /some/state-dir legacy good MCP_PROTOCOL_NEGOTIATION=legacy
sh run_codex.sh  /some/state-dir codex-default good
sh run_codex.sh  /some/state-dir codex-modern good --enable mcp_2026_07_28
python3 summarize_log.py /some/state-dir/requests.jsonl
```
