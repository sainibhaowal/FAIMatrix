"""Deterministic JSON-RPC, scope, and tool-dispatch coverage for MCP."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


def _request(*, user=None, scope=None, grant_id="grant-1", payload=None, headers=None):
    async def read_json():
        if isinstance(payload, BaseException):
            raise payload
        return payload

    return SimpleNamespace(
        state=SimpleNamespace(user=user, oauth_scope=scope, oauth_grant_id=grant_id),
        headers=headers or {},
        base_url="https://api.example.test/",
        json=read_json,
    )


def _ctx():
    return SimpleNamespace(
        tenant_id="tenant-1",
        session=object(),
        index=object(),
        cache=object(),
    )


def test_jsonrpc_helpers_and_scope_enforcement():
    from api.routers import mcp

    assert mcp._jsonrpc_result(1, {"ok": True}) == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"ok": True},
    }
    assert "data" not in mcp._jsonrpc_error(1, -1, "bad")
    assert mcp._jsonrpc_error(1, -1, "bad", {"field": "x"})["error"]["data"] == {
        "field": "x"
    }
    request = _request(user={"id": "u"}, scope="mcp:read")
    mcp._check_tool_scope(request, "faim_memory_search")
    with pytest.raises(mcp.HTTPException) as exc:
        mcp._check_tool_scope(request, "faim_memory_write")
    assert exc.value.status_code == 403
    mcp._check_tool_scope(
        _request(user={"id": "u"}, scope="mcp:write"), "faim_memory_write"
    )
    mcp._check_tool_scope(_request(user=None, scope="mcp:none"), "faim_memory_write")


@pytest.mark.asyncio
async def test_execute_tool_dispatches_all_tools(monkeypatch):
    from api.routers import mcp

    ctx = _ctx()
    request = _request(user={"id": "u"}, scope="mcp:write")
    captured = {}

    async def write_memory(body, ctx):
        captured["write"] = body
        return {"written": True}

    async def memory_search(body, ctx):
        captured["search"] = body
        return {"matches": []}

    async def ingest_file(request, ctx):
        captured["ingest"] = request
        return {"ingested": True}

    async def get_memory_item(memory_id, ctx):
        captured["get"] = memory_id
        return {"memory_id": memory_id}

    async def graph_surface(graph_id, limit, ctx):
        captured["graph"] = (graph_id, limit)
        return {"graph_id": graph_id}

    def run_query(**kwargs):
        captured["query"] = kwargs
        return {"results": []}

    monkeypatch.setattr(mcp, "write_memory", write_memory)
    monkeypatch.setattr(mcp, "memory_search", memory_search)
    monkeypatch.setattr(mcp, "ingest_file", ingest_file)
    monkeypatch.setattr(mcp, "get_memory_item", get_memory_item)
    monkeypatch.setattr(mcp, "graph_surface", graph_surface)
    monkeypatch.setattr(mcp, "run_query", run_query)

    assert await mcp._execute_tool(
        "faim_memory_write", {"graph_id": "g", "text": "hello"}, request, ctx
    ) == {"written": True}
    assert await mcp._execute_tool(
        "faim_memory_search", {"graph_id": "g", "query_text": "hello"}, request, ctx
    ) == {"matches": []}
    assert await mcp._execute_tool(
        "faim_query",
        {
            "graph_id": "g",
            "query_text": "hello",
            "profile": "invalid",
            "as_of": "2026-01-01T00:00:00Z",
        },
        request,
        ctx,
    ) == {"results": []}
    assert await mcp._execute_tool(
        "faim_ingest_text", {"graph_id": "g", "text": "hello"}, request, ctx
    ) == {"ingested": True}
    assert await mcp._execute_tool(
        "faim_memory_get", {"memory_id": "m"}, request, ctx
    ) == {"memory_id": "m"}
    assert await mcp._execute_tool(
        "faim_graph_surface", {"graph_id": "g", "limit": 5}, request, ctx
    ) == {"graph_id": "g"}
    assert captured["query"]["as_of"].tzinfo is not None
    with pytest.raises(KeyError):
        await mcp._execute_tool("unknown", {}, request, ctx)


@pytest.mark.asyncio
async def test_jsonrpc_message_methods_and_tool_error_shapes(monkeypatch):
    from api.routers import mcp

    request = _request(user={"id": "u"}, scope="mcp:read")
    ctx = _ctx()
    assert (await mcp._handle_jsonrpc_message({}, request, ctx))["error"][
        "code"
    ] == -32600
    init = await mcp._handle_jsonrpc_message(
        {"id": 1, "method": "initialize"}, request, ctx
    )
    assert init["result"]["protocolVersion"] == mcp.MCP_PROTOCOL_VERSION
    assert (
        await mcp._handle_jsonrpc_message(
            {"method": "notifications/initialized"}, request, ctx
        )
        is None
    )
    assert (
        await mcp._handle_jsonrpc_message(
            {"id": 2, "method": "notifications/initialized"}, request, ctx
        )
    )["result"] == {}
    assert (
        await mcp._handle_jsonrpc_message({"id": 3, "method": "ping"}, request, ctx)
    )["result"] == {}
    tools = await mcp._handle_jsonrpc_message(
        {"id": 4, "method": "tools/list"}, request, ctx
    )
    assert len(tools["result"]["tools"]) == len(mcp.MCP_TOOLS)
    missing_name = await mcp._handle_jsonrpc_message(
        {"id": 5, "method": "tools/call", "params": {}}, request, ctx
    )
    assert missing_name["error"]["code"] == -32602
    unknown = await mcp._handle_jsonrpc_message(
        {"id": 6, "method": "tools/call", "params": {"name": "nope"}}, request, ctx
    )
    assert unknown["error"]["code"] == -32601

    async def successful(*args, **kwargs):
        return {"answer": 42}

    monkeypatch.setattr(mcp, "_execute_tool", successful)
    called = await mcp._handle_jsonrpc_message(
        {"id": 10, "method": "tools/call", "params": {"name": "x"}}, request, ctx
    )
    assert called["result"]["isError"] is False
    assert called["result"]["structuredContent"] == {"answer": 42}

    async def forbidden(*args, **kwargs):
        raise mcp.HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr(mcp, "_execute_tool", forbidden)
    denied = await mcp._handle_jsonrpc_message(
        {"id": 7, "method": "tools/call", "params": {"name": "x"}}, request, ctx
    )
    assert denied["result"]["isError"] is True
    assert "forbidden" in denied["result"]["content"][0]["text"]

    async def broken(*args, **kwargs):
        raise RuntimeError("tool crashed")

    monkeypatch.setattr(mcp, "_execute_tool", broken)
    failed = await mcp._handle_jsonrpc_message(
        {"id": 8, "method": "tools/call", "params": {"name": "x"}}, request, ctx
    )
    assert "tool crashed" in failed["result"]["content"][0]["text"]
    assert (
        await mcp._handle_jsonrpc_message({"id": 9, "method": "nope"}, request, ctx)
    )["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_mcp_routes_grant_validation_and_payload_forms(monkeypatch):
    from api.routers import mcp

    ctx = _ctx()
    request = _request(
        user={"id": "u"}, scope="mcp:read", payload={"id": 1, "method": "ping"}
    )
    monkeypatch.setattr(mcp, "verify_and_touch_mcp_grant", lambda *args, **kwargs: True)
    info = await mcp.mcp_info(request, ctx)
    assert info["tenant_id"] == "tenant-1"
    response = await mcp.mcp_rpc(request, ctx)
    assert response.status_code == 200
    assert response.headers["mcp-session-id"]
    assert json.loads(response.body)["result"] == {}

    request.headers = {"Mcp-Session-Id": "existing"}
    request.json = lambda: None  # replaced below with a real async callable

    async def batch_json():
        return [
            {"id": 1, "method": "ping"},
            {"method": "notifications/initialized"},
        ]

    request.json = batch_json
    response = await mcp.mcp_rpc(request, ctx)
    assert response.headers["mcp-session-id"] == "existing"
    assert len(json.loads(response.body)) == 1

    async def empty_batch_json():
        return [{"method": "notifications/initialized"}, "not-a-message"]

    request.json = empty_batch_json
    response = await mcp.mcp_rpc(request, ctx)
    assert response.status_code == 202

    async def invalid_json():
        raise ValueError("bad json")

    request.json = invalid_json
    response = await mcp.mcp_rpc(request, ctx)
    assert response.status_code == 400
    assert json.loads(response.body)["error"]["code"] == -32700

    async def scalar_json():
        return "invalid"

    request.json = scalar_json
    response = await mcp.mcp_rpc(request, ctx)
    assert response.status_code == 400
    assert json.loads(response.body)["error"]["code"] == -32600

    async def notification_json():
        return {"method": "notifications/initialized"}

    request.json = notification_json
    response = await mcp.mcp_rpc(request, ctx)
    assert response.status_code == 202

    monkeypatch.setattr(
        mcp, "verify_and_touch_mcp_grant", lambda *args, **kwargs: False
    )
    with pytest.raises(mcp.HTTPException) as exc:
        await mcp.mcp_info(request, ctx)
    assert exc.value.status_code == 401
    assert "resource_metadata" in exc.value.headers["WWW-Authenticate"]
    with pytest.raises(mcp.HTTPException):
        await mcp.mcp_rpc(request, ctx)
    assert (await mcp.mcp_close_session(ctx)).status_code == 204
