"use client";

import {
  Check,
  Copy,
  KeyRound,
  Plug,
  RefreshCw,
  ShieldCheck,
  Terminal,
  Trash2,
  Unplug,
  Wrench,
} from "lucide-react";
import { getSession } from "next-auth/react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge, Button, useToast } from "@/components/ui";
import { GlassHeader } from "@/components/layout/GlassHeader";

type McpGrantItem = {
  grant_id: string;
  tenant_id: string;
  user_id: string;
  client_id: string;
  client_name: string;
  scopes: string[];
  created_at?: string | null;
  last_used_at?: string | null;
};

type McpGrantListResponse = {
  items: McpGrantItem[];
  total: number;
};

type ClientTab = "cursor" | "claude" | "vscode" | "offline";

const TAB_GUIDES: Record<ClientTab, { title: string; steps: string[] }> = {
  cursor: {
    title: "How to connect in Cursor",
    steps: [
      "Open Cursor Settings -> Tools & MCP -> Add Custom MCP (or create .cursor/mcp.json in your project).",
      "Paste the JSON config below and save.",
      "Click Connect / Needs Authentication -> your browser opens FAIM Login -> click Authorize FAIM.",
      'Ask Cursor: "Save this decision to FAIM memory" or "Search FAIM memory for ...".',
    ],
  },
  claude: {
    title: "How to connect in Claude Code / Claude Desktop",
    steps: [
      "For Claude Code CLI: run the `claude mcp add` command below in your terminal.",
      "For Claude Desktop: open Settings -> Connectors (or claude_desktop_config.json) and add the MCP URL.",
      "When prompted, sign into your FAIM account in the browser and click Authorize FAIM.",
      "Claude can now read, write, and search your FAIM graphs automatically.",
    ],
  },
  vscode: {
    title: "How to connect in VS Code",
    steps: [
      'Press Ctrl+Shift+P (Cmd+Shift+P on Mac) and run "MCP: Add Server", or create .vscode/mcp.json.',
      "Paste the JSON config below and save.",
      "VS Code will prompt you to sign in -> log into your FAIM account in the browser and click Authorize.",
      "Use Copilot Chat in Agent mode and ask it to search or store memory in FAIM.",
    ],
  },
  offline: {
    title: "Any AI App, Python SDK, or 100% Offline Setup",
    steps: [
      "For any HTTP-capable MCP app (Windsurf, OpenCode, Antigravity, custom agents): point it to the Remote MCP URL above.",
      "For local/stdio-only apps or 100% offline use: install the Python SDK & CLI with `pip install -e ./sdk/python`.",
      "Run `faim-mcp login --url <your-faim-url>` to connect via browser, OR pass `FAIM_API_KEY` from the API Keys page for headless/offline access.",
      "Your connected sessions appear below so you can inspect or disconnect them anytime.",
    ],
  },
};

const MCP_TOOLS = [
  {
    name: "faim_memory_write",
    desc: "Write text or memory into a FAIM graph for the authenticated user.",
  },
  {
    name: "faim_memory_search",
    desc: "Search FAIM memory with multi-hop graph traversal and semantic retrieval.",
  },
  {
    name: "faim_query",
    desc: "Run a full FAIM query with temporal (as_of) filtering and graph_max_hops.",
  },
  {
    name: "faim_ingest_text",
    desc: "Ingest documents into a FAIM graph with chunking and provenance.",
  },
  {
    name: "faim_memory_get",
    desc: "Fetch a single FAIM memory node by UUID.",
  },
  {
    name: "faim_graph_surface",
    desc: "Inspect graph surface stats, nodes, and edges.",
  },
] as const;

async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const base: Record<string, string> = {};
  if (token) base.Authorization = `Bearer ${token}`;
  if (!extra) return base;
  return { ...base, ...(extra as Record<string, string>) };
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await authHeaders(init?.headers);
  const resp = await fetch(path, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!resp.ok) {
    let message = `Request failed (${resp.status})`;
    try {
      const payload = (await resp.json()) as {
        detail?: string;
        error?: string;
      };
      message = payload.detail || payload.error || message;
    } catch {
      // ignore parse errors
    }
    throw new Error(message);
  }
  return (await resp.json()) as T;
}

function formatDateTime(value?: string | null): string {
  if (!value) return "Never";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "—";
  return dt.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function McpDashboardPage() {
  const { toast } = useToast();

  const [grants, setGrants] = useState<McpGrantItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<ClientTab>("cursor");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [disconnectTarget, setDisconnectTarget] = useState<
    McpGrantItem | "all" | null
  >(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [origin, setOrigin] = useState("http://localhost:8000");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const publicApi = process.env.NEXT_PUBLIC_FAIM_PUBLIC_ORIGIN;
      setOrigin((publicApi || window.location.origin).replace(/\/+$/, ""));
    }
  }, []);

  const mcpEndpoint = `${origin}/mcp`;

  const loadGrants = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiRequest<McpGrantListResponse>(
        "/api/v1/oauth/grants",
      );
      setGrants(data.items || []);
    } catch (err) {
      toast.error(
        "Failed to load MCP sessions",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void loadGrants();
  }, [loadGrants]);

  const snippet = useMemo(() => {
    if (activeTab === "claude") {
      return `# Claude Code CLI:\nclaude mcp add --transport http faim ${mcpEndpoint}\n\n# Or claude_desktop_config.json:\n${JSON.stringify(
        {
          mcpServers: {
            faim: {
              url: mcpEndpoint,
            },
          },
        },
        null,
        2,
      )}`;
    }
    if (activeTab === "cursor") {
      return JSON.stringify(
        {
          mcpServers: {
            faim: {
              url: mcpEndpoint,
            },
          },
        },
        null,
        2,
      );
    }
    if (activeTab === "vscode") {
      return JSON.stringify(
        {
          servers: {
            faim: {
              type: "http",
              url: mcpEndpoint,
            },
          },
        },
        null,
        2,
      );
    }
    return `# 1. Install FAIM MCP CLI\npip install -e ./sdk/python\n\n# 2. Browser login (connects to your FAIM account)\nfaim-mcp login --url ${origin}\nfaim-mcp\n\n# Or 100% offline with an API key from API Keys:\nFAIM_BASE_URL=${origin} FAIM_TENANT_ID=default FAIM_API_KEY=<your-key> faim-mcp`;
  }, [activeTab, mcpEndpoint, origin]);

  async function handleCopy(label: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(label);
      toast.success(`Copied ${label}`);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  }

  async function handleConfirmDisconnect() {
    if (!disconnectTarget) return;
    setDisconnecting(true);
    try {
      if (disconnectTarget === "all") {
        await apiRequest("/api/v1/oauth/grants", { method: "DELETE" });
        setGrants([]);
        toast.success("Disconnected all MCP agents");
      } else {
        await apiRequest(
          `/api/v1/oauth/grants/${encodeURIComponent(disconnectTarget.grant_id)}`,
          { method: "DELETE" },
        );
        setGrants((prev) =>
          prev.filter((g) => g.grant_id !== disconnectTarget.grant_id),
        );
        toast.success(`Disconnected ${disconnectTarget.client_name}`);
      }
      setDisconnectTarget(null);
    } catch (err) {
      toast.error(
        "Failed to disconnect MCP session",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setDisconnecting(false);
    }
  }

  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />
      <GlassHeader
        title="MCP Connections"
        subtitle="Connect external AI agents via OAuth 2.1 + PKCE and manage active sessions"
        icon={Plug}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void loadGrants()}
              disabled={loading}
              className="gap-1.5"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
            {grants.length > 0 && (
              <button
                type="button"
                onClick={() => setDisconnectTarget("all")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/15 px-3 py-1.5 text-xs font-medium text-rose-200 transition hover:bg-rose-500/25"
              >
                <Unplug className="h-3.5 w-3.5" />
                Disconnect all
              </button>
            )}
          </div>
        }
      />

      <div className="w-full space-y-4">
        {/* Summary Strip */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-cyan-500/80 via-cyan-400/40 to-transparent" />
            <div className="pointer-events-none absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Connected Agents
                </p>
                <p className="mt-1 text-2xl font-semibold text-cyan-300">
                  {grants.length}
                </p>
              </div>
              <Plug className="h-5 w-5 text-cyan-400/70" />
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-emerald-500/80 via-emerald-400/40 to-transparent" />
            <div className="pointer-events-none absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Exposed MCP Tools
                </p>
                <p className="mt-1 text-2xl font-semibold text-emerald-300">
                  {MCP_TOOLS.length}
                </p>
              </div>
              <Wrench className="h-5 w-5 text-emerald-400/70" />
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-amber-500/80 via-amber-400/40 to-transparent" />
            <div className="pointer-events-none absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Authentication
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-200">
                  OAuth 2.1 + PKCE &amp; API Key
                </p>
              </div>
              <ShieldCheck className="h-5 w-5 text-amber-400/70" />
            </div>
          </div>
        </div>

        {/* Quick Connect Card */}
        <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
          <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-cyan-500/80 via-cyan-400/40 to-transparent" />
          <div className="space-y-4 p-5">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <h2 className="text-sm font-semibold text-slate-100">
                  Quick Connect
                </h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  Add this endpoint to your IDE or agent. First connection opens
                  FAIM login in your browser automatically.
                </p>
              </div>
              <div className="flex items-center gap-2 rounded-xl border border-cyan-500/25 bg-[#070b14] px-3 py-1.5">
                <code className="font-mono text-xs text-cyan-300">
                  {mcpEndpoint}
                </code>
                <button
                  type="button"
                  onClick={() => void handleCopy("endpoint", mcpEndpoint)}
                  className="rounded p-1 text-slate-400 hover:bg-white/10 hover:text-slate-100"
                  title="Copy MCP URL"
                >
                  {copiedKey === "endpoint" ? (
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3">
              {(
                [
                  { id: "cursor", label: "Cursor" },
                  { id: "claude", label: "Claude" },
                  { id: "vscode", label: "VS Code" },
                  { id: "offline", label: "Any App / Offline CLI" },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                    activeTab === tab.id
                      ? "border-cyan-400/50 bg-cyan-500/15 text-cyan-200"
                      : "border-white/10 bg-white/5 text-slate-400 hover:bg-white/10"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div className="mb-2 text-xs font-semibold text-slate-200">
                {TAB_GUIDES[activeTab].title}
              </div>
              <ol className="list-decimal space-y-1.5 pl-4 text-xs text-slate-400">
                {TAB_GUIDES[activeTab].steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>

            <div className="relative rounded-xl border border-white/10 bg-[#070b14] p-4">
              <button
                type="button"
                onClick={() => void handleCopy("config", snippet)}
                className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-300 hover:bg-white/10"
              >
                {copiedKey === "config" ? (
                  <Check className="h-3 w-3 text-emerald-400" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
                {copiedKey === "config" ? "Copied" : "Copy"}
              </button>
              <pre className="overflow-x-auto pr-20 font-mono text-xs leading-relaxed text-slate-200">
                {snippet}
              </pre>
            </div>
          </div>
        </div>

        {/* Connected MCP Sessions */}
        <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
          <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-purple-500/80 via-purple-400/40 to-transparent" />
          <div className="p-0">
            <div className="border-b border-white/8 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-100">
                Connected MCP Sessions
              </h2>
              <p className="mt-0.5 text-xs text-slate-400">
                External AI agents authorized via browser login. Disconnecting a
                session immediately revokes its access.
              </p>
            </div>

            {loading && grants.length === 0 ? (
              <div className="px-6 py-10 text-center text-sm text-slate-400">
                Loading MCP sessions...
              </div>
            ) : grants.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
                <div className="rounded-full border border-cyan-500/20 bg-cyan-500/10 p-3">
                  <Terminal className="h-5 w-5 text-cyan-400" />
                </div>
                <p className="text-sm font-medium text-slate-200">
                  No active MCP logins
                </p>
                <p className="max-w-md text-xs text-slate-400">
                  Connect Cursor, Claude, VS Code, or run{" "}
                  <code className="font-mono text-cyan-300">
                    faim-mcp login
                  </code>{" "}
                  above. Once authorized, your connected agent will appear here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-[11px] uppercase tracking-wider text-slate-400">
                      <th className="px-5 py-3 font-medium">Client</th>
                      <th className="px-5 py-3 font-medium">Permissions</th>
                      <th className="px-5 py-3 font-medium">Connected</th>
                      <th className="px-5 py-3 font-medium">Last Used</th>
                      <th className="px-5 py-3 text-right font-medium">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {grants.map((grant) => (
                      <tr
                        key={grant.grant_id}
                        className="hover:bg-white/[0.02]"
                      >
                        <td className="px-5 py-3.5">
                          <div className="font-medium text-slate-100">
                            {grant.client_name || "MCP Client"}
                          </div>
                          <div className="font-mono text-[11px] text-slate-500">
                            {grant.client_id}
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex flex-wrap gap-1">
                            {(grant.scopes || []).map((scope) => (
                              <Badge key={scope} variant="default">
                                {scope}
                              </Badge>
                            ))}
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-slate-400">
                          {formatDateTime(grant.created_at)}
                        </td>
                        <td className="px-5 py-3.5 text-slate-400">
                          {formatDateTime(grant.last_used_at)}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <button
                            type="button"
                            onClick={() => setDisconnectTarget(grant)}
                            className="inline-flex items-center gap-1 rounded-lg border border-rose-500/20 bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-300 transition hover:bg-rose-500/20"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Disconnect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Available MCP Tools */}
        <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
          <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-emerald-500/80 via-emerald-400/40 to-transparent" />
          <div className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-100">
                  Available MCP Tools
                </h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  Every tool call runs strictly inside your authenticated FAIM
                  account.
                </p>
              </div>
              <KeyRound className="h-4 w-4 text-slate-500" />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {MCP_TOOLS.map((tool) => (
                <div
                  key={tool.name}
                  className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.02] p-3.5"
                >
                  <div className="pointer-events-none absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/75 via-cyan-400/25 to-transparent" />
                  <div className="font-mono text-xs font-semibold text-cyan-300">
                    {tool.name}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">
                    {tool.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Disconnect Confirmation Modal */}
      {disconnectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm space-y-4 rounded-2xl border border-white/15 bg-[#0d1424] p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-slate-100">
              {disconnectTarget === "all"
                ? "Disconnect all MCP agents?"
                : "Disconnect MCP agent?"}
            </h3>
            <p className="text-xs leading-relaxed text-slate-400">
              {disconnectTarget === "all"
                ? "All connected IDEs and CLI agents will immediately lose MCP access and must log in again."
                : `${disconnectTarget.client_name} will immediately lose MCP access and must log in again to reconnect.`}
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setDisconnectTarget(null)}
                disabled={disconnecting}
              >
                Cancel
              </Button>
              <button
                type="button"
                onClick={() => void handleConfirmDisconnect()}
                disabled={disconnecting}
                className="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
              >
                {disconnecting ? "Disconnecting..." : "Disconnect"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
