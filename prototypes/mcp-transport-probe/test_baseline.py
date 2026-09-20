"""Step 0 of the transport test plan: scripted baseline over a real socket."""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Iterator

import anyio
import httpx2
import pytest
import uvicorn

from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.types.version import MODERN_PROTOCOL_VERSIONS

from probe_server import create_app

TOKEN = "probe-token-not-a-secret-5b1e9c"
PV = "io.modelcontextprotocol/protocolVersion"
CAPS = "io.modelcontextprotocol/clientCapabilities"
MODERN = "2026-07-28"


def _serve(app) -> Iterator[str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def base(tmp_path_factory) -> Iterator[str]:
    log = tmp_path_factory.mktemp("log") / "requests.jsonl"
    yield from _serve(create_app(TOKEN, log_path=str(log)))


AUTH = {"Authorization": f"Bearer {TOKEN}"}


def modern_headers(method: str, name: str | None = None, version: str = MODERN) -> dict[str, str]:
    headers = {
        **AUTH,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": version,
        "Mcp-Method": method,
    }
    if name:
        headers["Mcp-Name"] = name
    return headers


def modern_body(method: str, params: dict | None = None, version: str = MODERN) -> dict:
    params = dict(params or {})
    params["_meta"] = {PV: version, CAPS: {}}
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}


def rpc(response: httpx2.Response) -> dict:
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:])
    return response.json()


async def exercise(url: str, mode: str) -> dict:
    async with create_mcp_http_client(headers=AUTH) as http:
        async with Client(streamable_http_client(url, http_client=http), mode=mode) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            templates = await client.list_resource_templates()
            called = await client.call_tool("echo_inventory", {"name": "fw1"})
            status = await client.read_resource("pilot://probe/status")
            item = await client.read_resource("pilot://probe/items/42")
            return {
                "version": client.protocol_version,
                "tools": [t.name for t in tools.tools],
                "read_only": [t.annotations.read_only_hint for t in tools.tools],
                "resources": [str(r.uri) for r in resources.resources],
                "templates": [t.uri_template for t in templates.resource_templates],
                "structured": called.structured_content,
                "status": status.contents[0].text,
                "item": item.contents[0].text,
            }


# 1. FastAPI mount
def test_fastapi_route_and_mcp_share_a_process(base):
    assert httpx2.get(f"{base}/api/health").json() == {"status": "ok"}
    result = anyio.run(exercise, f"{base}/mcp", "auto")
    assert result["tools"] == ["echo_inventory"]


def test_missing_lifespan_hook_fails():
    gen = _serve(create_app(TOKEN, enter_lifespan=False))
    url = next(gen)
    try:
        response = httpx2.post(
            f"{url}/mcp",
            headers=modern_headers("tools/list"),
            json=modern_body("tools/list"),
        )
        print("NO-LIFESPAN:", response.status_code, response.text[:300])
        assert response.status_code >= 500
    finally:
        next(gen, None)


# 2. discover snapshot
def test_discover_supported_versions_snapshot(base):
    response = httpx2.post(
        f"{base}/mcp",
        headers=modern_headers("server/discover"),
        json=modern_body("server/discover"),
    )
    assert response.status_code == 200
    result = rpc(response)["result"]
    print("DISCOVER:", json.dumps(result))
    assert result["supportedVersions"] == ["2026-07-28"]
    assert tuple(result["supportedVersions"]) == MODERN_PROTOCOL_VERSIONS


# 3. both eras, identical payloads
def test_both_eras_agree(base):
    auto = anyio.run(exercise, f"{base}/mcp", "auto")
    legacy = anyio.run(exercise, f"{base}/mcp", "legacy")
    print("AUTO:", auto["version"], "LEGACY:", legacy["version"])
    assert auto["version"] == "2026-07-28"
    assert legacy["version"] == "2025-11-25"
    assert {k: v for k, v in auto.items() if k != "version"} == {
        k: v for k, v in legacy.items() if k != "version"
    }
    assert auto["read_only"] == [True]
    assert auto["resources"] == ["pilot://probe/status"]
    assert auto["templates"] == ["pilot://probe/items/{item_id}"]
    assert auto["structured"]["name"] == "fw1"


# 4. stateless legacy leg
def legacy_initialize(base: str, extra: dict | None = None) -> httpx2.Response:
    return httpx2.post(
        f"{base}/mcp",
        headers={
            **AUTH,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **(extra or {}),
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "raw-probe", "version": "0"},
            },
        },
    )


def test_legacy_leg_issues_no_session_id(base):
    response = legacy_initialize(base)
    assert response.status_code == 200
    assert "mcp-session-id" not in response.headers
    assert rpc(response)["result"]["protocolVersion"] == "2025-06-18"


def test_get_and_delete_status_codes(base):
    seen = {}
    for label, headers in {
        "legacy": {**AUTH, "Accept": "application/json"},
        "modern": {**AUTH, "Accept": "application/json", "MCP-Protocol-Version": MODERN},
    }.items():
        for verb in ("GET", "DELETE"):
            seen[f"{label} {verb}"] = httpx2.request(verb, f"{base}/mcp", headers=headers).status_code
    print("GET/DELETE:", seen)
    assert seen["modern GET"] == 405 and seen["modern DELETE"] == 405
    assert seen["legacy DELETE"] == 405


# 5. version errors
def test_unsupported_version(base):
    response = httpx2.post(
        f"{base}/mcp",
        headers=modern_headers("tools/list", version="1900-01-01"),
        json=modern_body("tools/list", version="1900-01-01"),
    )
    error = rpc(response)["error"]
    print("UNSUPPORTED:", response.status_code, error)
    assert response.status_code == 400 and error["code"] == -32022
    assert error["data"]["supported"] == ["2026-07-28"]


def test_header_body_mismatch(base):
    response = httpx2.post(
        f"{base}/mcp",
        headers=modern_headers("tools/list"),
        json=modern_body("resources/list"),
    )
    assert response.status_code == 400 and rpc(response)["error"]["code"] == -32020


def test_unknown_method(base):
    response = httpx2.post(
        f"{base}/mcp",
        headers=modern_headers("nope/nothing"),
        json=modern_body("nope/nothing"),
    )
    assert response.status_code == 404 and rpc(response)["error"]["code"] == -32601


# 6. auth
@pytest.mark.parametrize(
    "headers,query",
    [({}, ""), ({"Authorization": "Bearer wrong"}, ""), ({}, f"?token={TOKEN}&access_token={TOKEN}")],
    ids=["no-token", "wrong-token", "query-token"],
)
def test_auth_rejections(base, headers, query):
    sent = {k: v for k, v in modern_headers("tools/call", "echo_inventory").items() if k != "Authorization"}
    response = httpx2.post(
        f"{base}/mcp{query}",
        headers={**sent, **headers},
        json=modern_body("tools/call", {"name": "echo_inventory", "arguments": {"name": "x"}}),
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert TOKEN not in response.text and "wrong" not in response.text
    assert "result" not in response.text


def test_health_needs_no_token_but_mcp_does(base):
    assert httpx2.get(f"{base}/api/health").status_code == 200


# 7. transport security
def test_host_and_origin(base):
    def post(extra: dict) -> int:
        return httpx2.post(
            f"{base}/mcp",
            headers={**modern_headers("tools/list"), **extra},
            json=modern_body("tools/list"),
        ).status_code

    assert post({"Host": "evil.example"}) == 421
    assert post({"Origin": "https://evil.example"}) == 403
    assert post({}) == 200
    assert post({"Origin": "http://localhost:3000"}) == 200


def test_explicit_allowlist_protects_non_localhost_name():
    gen = _serve(
        create_app(
            TOKEN,
            allowed_hosts=["pilot.lan:*"],
            allowed_origins=["https://pilot.lan"],
        )
    )
    url = next(gen)
    try:
        def post(extra: dict) -> int:
            return httpx2.post(
                f"{url}/mcp",
                headers={**modern_headers("tools/list"), **extra},
                json=modern_body("tools/list"),
            ).status_code

        assert post({"Host": "pilot.lan:8443"}) == 200
        assert post({"Host": "evil.example"}) == 421
        assert post({}) == 421  # 127.0.0.1 is no longer allowed: the list is what protects
        assert post({"Host": "pilot.lan:8443", "Origin": "https://evil.example"}) == 403
    finally:
        next(gen, None)


# 8. limits
def test_body_cap_and_content_type(base):
    big = b'{"pad":"' + b"a" * (4 * 1024 * 1024 + 16) + b'"}'
    response = httpx2.post(f"{base}/mcp", headers=modern_headers("tools/list"), content=big)
    assert response.status_code == 413
    headers = {**modern_headers("tools/list"), "Content-Type": "text/plain"}
    response = httpx2.post(f"{base}/mcp", headers=headers, content=json.dumps(modern_body("tools/list")))
    assert response.status_code == 400


# 9. resource not found, both eras
def test_resource_not_found(base):
    uri = "pilot://probe/nothing-here"
    modern = httpx2.post(
        f"{base}/mcp",
        headers=modern_headers("resources/read", uri),
        json=modern_body("resources/read", {"uri": uri}),
    )
    legacy = httpx2.post(
        f"{base}/mcp",
        headers={
            **AUTH,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-06-18",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": uri}},
    )
    print("NOT-FOUND modern:", modern.status_code, rpc(modern)["error"]["code"])
    print("NOT-FOUND legacy:", legacy.status_code, rpc(legacy)["error"]["code"])
    assert rpc(modern)["error"]["code"] == -32602
