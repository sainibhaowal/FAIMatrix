# FAIM Python SDK & MCP Server

## 1. Remote MCP (SaaS: Automatic Browser Login)

Point your IDE or AI agent (Cursor, Claude Code, VS Code) to your FAIM `/mcp` endpoint:

```json
{
  "mcpServers": {
    "faim": {
      "url": "https://your-faim-domain.com/mcp"
    }
  }
}
```

When connecting, FAIM returns `401` with `WWW-Authenticate` pointing to `/.well-known/oauth-protected-resource`, triggering OAuth 2.1 + PKCE login in the browser tied to the user's FAIM account.

## 2. Offline / Local CLI & `stdio` MCP

```bash
pip install -e ./sdk/python

# Option A: Browser login (SaaS or local)
faim-mcp login --url http://localhost:8000
faim-mcp

# Option B: 100% Offline with API Key
FAIM_BASE_URL=http://localhost:8000 FAIM_TENANT_ID=default FAIM_API_KEY=... faim-mcp
```

## 3. Thin Python SDK

```python
from faim_sdk import FAIMClient

client = FAIMClient("http://localhost:8000", api_key="...", tenant_id="default")
client.memory_write("my-graph", "User prefers concise TypeScript examples.")
res = client.memory_search("my-graph", "TypeScript preferences", graph_max_hops=4)
```
