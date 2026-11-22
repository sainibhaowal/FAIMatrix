"""FAIM-Native API: Remote MCP Server (Streamable HTTP / JSON-RPC 2.0).

Exposes FAIM memory & graph retrieval endpoints as MCP tools at /mcp.
Authenticated per-user via OAuth 2.1 Bearer JWT or X-Tenant-Id + X-Api-Key.
"""

from __future__ import annotations

import base64
import json
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.deps import FAIMContext, get_faim_context
from api.routers.graph import graph_surface
from api.routers.ingest import IngestRequest, ingest_file
from api.routers.memory import (
    MemorySearchRequest,
    MemoryWriteRequest,
    get_memory_item,
    memory_search,
    write_memory,
)
from api.routers.oauth import verify_and_touch_mcp_grant
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from orchestration.ingest_flow import FAIMProfile
from orchestration.query_flow import run_query

router = APIRouter(tags=["MCP"])

MCP_PROTOCOL_VERSION = "2025-03-26"
MCP_SERVER_INFO = {"name": "faim-mcp", "version": "0.10.0"}

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "faim_memory_write",
        "description": "Write text or memory content into a FAIM memory graph for the authenticated user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Target FAIM graph ID"},
                "text": {
                    "type": "string",
                    "description": "Memory text to store and index",
                },
                "filename": {
                    "type": "string",
                    "description": "Optional virtual filename",
                },
                "profile": {
                    "type": "string",
                    "enum": ["strict", "balanced", "relaxed", "fast"],
                    "default": "strict",
                },
                "persist_mode": {
                    "type": "string",
                    "enum": ["strict", "relaxed"],
                    "default": "relaxed",
                },
                "idempotency_key": {
                    "type": "string",
                    "description": "Optional deduplication key",
                },
            },
            "required": ["graph_id", "text"],
        },
    },
    {
        "name": "faim_memory_search",
        "description": "Search FAIM memory using multi-hop graph traversal, lexical, and semantic retrieval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Target FAIM graph ID"},
                "query_text": {"type": "string", "description": "Search query"},
                "k": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                "profile": {
                    "type": "string",
                    "enum": ["strict", "balanced", "relaxed", "fast"],
                    "default": "strict",
                },
                "graph_max_hops": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 24,
                    "description": "Optional hop depth (1-24, default 2)",
                },
                "return_explain": {"type": "boolean", "default": False},
            },
            "required": ["graph_id", "query_text"],
        },
    },
    {
        "name": "faim_query",
        "description": "Run a full FAIM retrieval query with optional temporal (as_of / historical) filtering and multi-hop depth.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Target FAIM graph ID"},
                "query_text": {"type": "string", "description": "Query text"},
                "k": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                "profile": {
                    "type": "string",
                    "enum": ["STRICT", "BALANCED", "RELAXED", "FAST"],
                    "default": "STRICT",
                },
                "graph_max_hops": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 24,
                    "description": "Optional hop depth (1-24, default 2)",
                },
                "include_historical": {"type": "boolean", "default": True},
                "as_of": {
                    "type": "string",
                    "description": "Optional ISO-8601 timestamp",
                },
                "return_explain": {"type": "boolean", "default": False},
            },
            "required": ["graph_id", "query_text"],
        },
    },
    {
        "name": "faim_ingest_text",
        "description": "Ingest a text document into a FAIM graph with full chunking, graph extraction, and provenance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Target FAIM graph ID"},
                "text": {"type": "string", "description": "Document text content"},
                "filename": {"type": "string", "default": "mcp-ingest.txt"},
                "content_type": {"type": "string", "default": "text/plain"},
                "profile": {
                    "type": "string",
                    "enum": ["strict", "fast", "relaxed"],
                    "default": "strict",
                },
                "persist_mode": {
                    "type": "string",
                    "enum": ["strict", "relaxed"],
                    "default": "relaxed",
                },
            },
            "required": ["graph_id", "text"],
        },
    },
    {
        "name": "faim_memory_get",
        "description": "Fetch a single FAIM memory node by its UUID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "Memory node UUID"},
            },
            "required": ["memory_id"],
        },
    },
    {
        "name": "faim_graph_surface",
        "description": "Inspect the graph surface (nodes, edges, version, hash) for a FAIM graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Target FAIM graph ID"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "default": 50,
                },
            },
            "required": ["graph_id"],
        },
    },
]

_WRITE_TOOLS = {"faim_memory_write", "faim_ingest_text"}


def _jsonrpc_result(req_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(
    req_id: Any, code: int, message: str, data: Any = None
) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _check_tool_scope(request: Request, tool_name: str) -> None:
    user = getattr(request.state, "user", None)
    # Only enforce OAuth scope when an OAuth scope claim is present
    raw_scope = getattr(request.state, "oauth_scope", None)
    if not raw_scope or user is None:
        return
    scopes = set(str(raw_scope).split())
    required = "mcp:write" if tool_name in _WRITE_TOOLS else "mcp:read"
    if required not in scopes and "mcp:write" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required OAuth scope: {required}",
        )


async def _execute_tool(
    name: str,
    args: Dict[str, Any],
    request: Request,
    ctx: FAIMContext,
) -> Any:
    _check_tool_scope(request, name)

    if name == "faim_memory_write":
        body = MemoryWriteRequest(
            graph_id=args["graph_id"],
            text=args["text"],
            filename=args.get("filename"),
            content_type=args.get("content_type") or "text/plain",
            profile=args.get("profile", "strict"),
            persist_mode=args.get("persist_mode", "relaxed"),
            idempotency_key=args.get("idempotency_key"),
        )
        return jsonable_encoder(await write_memory(body=body, ctx=ctx))

    if name == "faim_memory_search":
        body = MemorySearchRequest(
            graph_id=args["graph_id"],
            query_text=args["query_text"],
            k=args.get("k", 10),
            profile=args.get("profile", "strict"),
            return_explain=bool(args.get("return_explain", False)),
            graph_max_hops=args.get("graph_max_hops"),
        )
        return jsonable_encoder(await memory_search(body=body, ctx=ctx))

    if name == "faim_query":
        profile_raw = str(args.get("profile", "STRICT")).upper()
        try:
            profile = FAIMProfile(profile_raw.lower())
        except ValueError:
            profile = FAIMProfile.STRICT
        as_of_raw = args.get("as_of")
        as_of = (
            datetime.fromisoformat(as_of_raw.replace("Z", "+00:00"))
            if as_of_raw
            else None
        )
        result = run_query(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=args["graph_id"],
            query_text=args["query_text"],
            k=int(args.get("k", 10)),
            profile=profile,
            return_explain=bool(args.get("return_explain", False)),
            index=ctx.index if profile != FAIMProfile.STRICT else None,
            cache=ctx.cache,
            include_historical=bool(args.get("include_historical", True)),
            as_of=as_of,
            graph_max_hops=args.get("graph_max_hops"),
        )
        return jsonable_encoder(result)

    if name == "faim_ingest_text":
        encoded = base64.b64encode(str(args["text"]).encode("utf-8")).decode("ascii")
        req = IngestRequest(
            graph_id=args["graph_id"],
            filename=args.get("filename") or "mcp-ingest.txt",
            bytes_base64=encoded,
            content_type=args.get("content_type") or "text/plain",
            profile=args.get("profile", "strict"),
            persist_mode=args.get("persist_mode", "relaxed"),
        )
        return jsonable_encoder(await ingest_file(request=req, ctx=ctx))

    if name == "faim_memory_get":
        return jsonable_encoder(
            await get_memory_item(memory_id=args["memory_id"], ctx=ctx)
        )

    if name == "faim_graph_surface":
        return jsonable_encoder(
            await graph_surface(
                graph_id=args["graph_id"],
                limit=int(args.get("limit", 50)),
                ctx=ctx,
            )
        )

    raise KeyError(f"Unknown tool: {name}")


async def _handle_jsonrpc_message(
    msg: Dict[str, Any],
    request: Request,
    ctx: FAIMContext,
) -> Optional[Dict[str, Any]]:
    req_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    if not isinstance(method, str):
        return _jsonrpc_error(req_id, -32600, "Invalid Request: missing method")

    if method == "initialize":
        return _jsonrpc_result(
            req_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": MCP_SERVER_INFO,
            },
        )

    if method == "notifications/initialized":
        return None if req_id is None else _jsonrpc_result(req_id, {})

    if method == "ping":
        return _jsonrpc_result(req_id, {})

    if method == "tools/list":
        return _jsonrpc_result(req_id, {"tools": MCP_TOOLS})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(tool_name, str):
            return _jsonrpc_error(req_id, -32602, "Invalid params: missing tool name")
        try:
            payload = await _execute_tool(tool_name, arguments, request, ctx)
            return _jsonrpc_result(
                req_id,
                {
                    "content": [
                        {"type": "text", "text": json.dumps(payload, default=str)}
                    ],
                    "structuredContent": (
                        payload if isinstance(payload, dict) else {"result": payload}
                    ),
                    "isError": False,
                },
            )
        except KeyError as exc:
            return _jsonrpc_error(req_id, -32601, str(exc))
        except HTTPException as exc:
            return _jsonrpc_result(
                req_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {"error": exc.detail, "status_code": exc.status_code}
                            ),
                        }
                    ],
                    "isError": True,
                },
            )
        except Exception as exc:
            return _jsonrpc_result(
                req_id,
                {
                    "content": [
                        {"type": "text", "text": json.dumps({"error": str(exc)})}
                    ],
                    "isError": True,
                },
            )

    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


def _require_active_mcp_grant(request: Request, ctx: FAIMContext) -> None:
    grant_id = getattr(request.state, "oauth_grant_id", None)
    if not verify_and_touch_mcp_grant(ctx.tenant_id, grant_id, session=ctx.session):
        import os

        origin = (os.getenv("FAIM_PUBLIC_ORIGIN") or "").strip().rstrip("/") or str(
            request.base_url
        ).rstrip("/")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MCP session has been disconnected",
            headers={
                "WWW-Authenticate": (
                    f'Bearer resource_metadata="{origin}/.well-known/oauth-protected-resource", '
                    'scope="mcp:read mcp:write"'
                )
            },
        )


@router.get("/mcp")
async def mcp_info(
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    """Authenticated MCP endpoint metadata."""
    _require_active_mcp_grant(request, ctx)
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "serverInfo": MCP_SERVER_INFO,
        "tenant_id": ctx.tenant_id,
        "tools": [t["name"] for t in MCP_TOOLS],
    }


@router.post("/mcp")
async def mcp_rpc(
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Response:
    """MCP Streamable HTTP JSON-RPC 2.0 endpoint."""
    _require_active_mcp_grant(request, ctx)
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=_jsonrpc_error(None, -32700, "Parse error: invalid JSON"),
        )

    session_id = request.headers.get("Mcp-Session-Id") or secrets.token_urlsafe(16)
    headers = {"Mcp-Session-Id": session_id}

    if isinstance(payload, list):
        responses = []
        for item in payload:
            if isinstance(item, dict):
                res = await _handle_jsonrpc_message(item, request, ctx)
                if res is not None:
                    responses.append(res)
        if not responses:
            return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)
        return JSONResponse(content=responses, headers=headers)

    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400,
            content=_jsonrpc_error(None, -32600, "Invalid Request"),
            headers=headers,
        )

    res = await _handle_jsonrpc_message(payload, request, ctx)
    if res is None:
        return Response(status_code=status.HTTP_202_ACCEPTED, headers=headers)
    return JSONResponse(content=res, headers=headers)


@router.delete("/mcp", status_code=status.HTTP_204_NO_CONTENT)
async def mcp_close_session(
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Response:
    """Close an MCP session."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)
