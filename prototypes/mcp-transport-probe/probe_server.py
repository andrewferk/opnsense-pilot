"""THROWAWAY transport probe for wayfinder ticket #14. Not product code.

One dummy read-only tool, one static resource, one resource template, mounted
in a FastAPI app behind a static bearer check. Every MCP request is logged as
one JSON line (never the token) so the negotiated era per client is observable.
"""

from __future__ import annotations

import contextlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

CLIENT_INFO_META_KEY = "io.modelcontextprotocol/clientInfo"

LOCAL_HOSTS = ["127.0.0.1:*", "localhost:*"]
LOCAL_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*"]


class InventoryModel(BaseModel):
    name: str
    kind: str
    items: list[str]
    probe: bool = True


def build_mcp() -> MCPServer:
    mcp = MCPServer(
        "pilot-transport-probe",
        instructions="Throwaway transport probe. Read-only. Returns canned data.",
    )

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True))
    def echo_inventory(name: str) -> InventoryModel:
        """Return a canned inventory record echoing the given name. Read-only."""
        return InventoryModel(name=name, kind="probe", items=["alpha", "bravo"])

    @mcp.resource("pilot://probe/status", mime_type="application/json")
    def status() -> str:
        """Static probe status."""
        return json.dumps({"status": "ok", "marker": "PROBE-STATUS-7f3a"})

    @mcp.resource("pilot://probe/items/{item_id}", mime_type="application/json")
    def item(item_id: str) -> str:
        """One canned item by id."""
        return json.dumps({"item_id": item_id, "marker": f"PROBE-ITEM-{item_id}"})

    return mcp


class RequestLog:
    """Pure-ASGI logger: method, protocol version header, session header, client."""

    def __init__(self, app: Any, path: str | None) -> None:
        self.app = app
        self.path = path

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        body = bytearray()
        record: dict[str, Any] = {
            "t": round(time.time(), 3),
            "http": scope["method"],
            "path": scope["path"],
            "protocol_header": headers.get("mcp-protocol-version"),
            "mcp_method_header": headers.get("mcp-method"),
            "req_session_header": "mcp-session-id" in headers,
            "has_authorization": "authorization" in headers,
            "user_agent": headers.get("user-agent"),
            "accept": headers.get("accept"),
        }

        async def tee_receive() -> Any:
            message = await receive()
            if message["type"] == "http.request" and len(body) < 65536:
                body.extend(message.get("body", b""))
            return message

        async def tee_send(message: Any) -> None:
            if message["type"] == "http.response.start":
                resp = {k.decode().lower(): v.decode() for k, v in message["headers"]}
                record["status"] = message["status"]
                record["resp_session_header"] = "mcp-session-id" in resp
                record["resp_content_type"] = resp.get("content-type")
                record["www_authenticate"] = resp.get("www-authenticate")
                self._finish(record, bytes(body))
            await send(message)

        await self.app(scope, tee_receive, tee_send)

    def _finish(self, record: dict[str, Any], body: bytes) -> None:
        try:
            payload = json.loads(body) if body else None
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            params = payload.get("params") or {}
            meta = params.get("_meta") or {}
            record["rpc_method"] = payload.get("method")
            record["rpc_name"] = params.get("name") or params.get("uri")
            info = params.get("clientInfo") or meta.get(CLIENT_INFO_META_KEY) or {}
            record["client"] = f"{info.get('name')}/{info.get('version')}" if info else None
            if payload.get("method") == "initialize":
                record["initialize_requested_version"] = params.get("protocolVersion")
        if self.path:
            with open(self.path, "a") as fh:
                fh.write(json.dumps(record) + "\n")


class BearerAuth:
    """Pure-ASGI static bearer check. Header only; never query string."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied = dict(scope["headers"]).get(b"authorization", b"")
        if hmac.compare_digest(supplied, self.expected):
            await self.app(scope, receive, send)
            return
        body = b'{"error":"unauthorized"}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def create_app(
    token: str,
    *,
    allowed_hosts: list[str] | None = None,
    allowed_origins: list[str] | None = None,
    stateless: bool = True,
    enter_lifespan: bool = True,
    log_path: str | None = None,
) -> FastAPI:
    mcp = build_mcp()
    mcp_app = mcp.streamable_http_app(
        stateless_http=stateless,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts or LOCAL_HOSTS,
            allowed_origins=allowed_origins or LOCAL_ORIGINS,
        ),
    )

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        if not enter_lifespan:
            yield
            return
        async with mcp.session_manager.run():
            yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Mount last: Mount("/") swallows every path. The MCP app serves /mcp itself.
    app.mount("/", RequestLog(BearerAuth(mcp_app, token), log_path))
    return app


def from_env() -> FastAPI:
    return create_app(
        os.environ["PILOT_MCP_TOKEN"],
        stateless=os.environ.get("PROBE_STATELESS", "1") == "1",
        log_path=os.environ.get("PROBE_LOG"),
    )
