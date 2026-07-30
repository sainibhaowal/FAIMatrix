/**
 * Playwright global setup — real backend, no mocks.
 *
 * Seeds the E2E test graph (e2e-graph-001) for user e2e-test-user using the
 * live FAIM backend. All writes are idempotent (idempotency_key per entry).
 *
 * Subsequent tests use the real graph surface, neighborhood, and event APIs
 * without any HTTP mocking.
 */

import { E2E_BACKEND_URL, E2E_GRAPH_ID } from "../playwright.config";

const E2E_JWT =
  process.env.PLAYWRIGHT_E2E_JWT ??
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlMmUtdGVzdC11c2VyIiwiZW1haWwiOiJlMmVAdGVzdC5mYWltIiwidXNlcklkIjoiZTJlLXRlc3QtdXNlciIsImdyYXBoSWQiOiJlMmUtZ3JhcGgtMDAxIiwibmFtZSI6IkUyRSBUZXN0IFVzZXIiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTc3NjM2Mjk0Nn0.OP_HzPsqIA4Fd67MRRJZDtfRv1vit93e5OgjKblKcRQ";

function authHeaders(): Record<string, string> {
  return {
    Authorization: `Bearer ${E2E_JWT}`,
    "Content-Type": "application/json",
  };
}

async function backendFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const resp = await fetch(`${E2E_BACKEND_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
  });
  return resp;
}

async function writeMemory(
  idempotencyKey: string,
  text: string,
): Promise<void> {
  const resp = await backendFetch("/api/v1/memory/write", {
    method: "POST",
    body: JSON.stringify({
      graph_id: E2E_GRAPH_ID,
      text,
      profile: "strict",
      persist_mode: "relaxed",
      idempotency_key: idempotencyKey,
    }),
  });
  if (resp.status === 409) {
    // Idempotency key already used — data already exists, skip silently
    console.log(
      `[e2e-setup] ${idempotencyKey}: already seeded (409), skipping`,
    );
    return;
  }
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(
      `memory/write failed (${resp.status}): ${body.slice(0, 200)}`,
    );
  }
  const data = (await resp.json()) as { nodes_written: number };
  console.log(
    `[e2e-setup] ${idempotencyKey}: nodes_written=${data.nodes_written}`,
  );
}

export default async function globalSetup(): Promise<void> {
  console.log("[e2e-setup] Verifying backend health…");

  // 1. Backend health check
  const health = await fetch(`${E2E_BACKEND_URL}/health`);
  if (!health.ok) {
    throw new Error(
      `Backend not healthy at ${E2E_BACKEND_URL} (${health.status})`,
    );
  }
  console.log("[e2e-setup] Backend healthy ✓");

  // 2. Verify JWT auth works
  const surfaceCheck = await backendFetch(
    `/api/v1/graph/surface?graph_id=${E2E_GRAPH_ID}`,
  );
  if (!surfaceCheck.ok) {
    throw new Error(
      `JWT auth failed (${surfaceCheck.status}) — check NEXTAUTH_SECRET`,
    );
  }
  console.log("[e2e-setup] JWT auth verified ✓");

  // 3. Seed test entries (idempotent — safe to re-run)
  const entries: [string, string][] = [
    [
      "e2e-node-seed-001",
      "FAIM is a memory graph system. It stores knowledge as nodes and edges.",
    ],
    [
      "e2e-node-seed-002",
      "Graph nodes represent atomic units of knowledge. Each node has a vector hash and display state.",
    ],
    [
      "e2e-node-seed-003",
      "Edges connect related nodes. Inheritance edges flow from parent to child knowledge units.",
    ],
    [
      "e2e-node-seed-004",
      "Opposition edges link contradictory facts and are used by the retrieval system to suppress conflicts.",
    ],
    [
      "e2e-node-seed-005",
      "The FIG view renders the graph as an interactive force-directed visualization for exploration.",
    ],
  ];

  for (const [key, text] of entries) {
    await writeMemory(key, text);
  }

  // 4. Verify final surface has nodes
  const surfaceResp = await backendFetch(
    `/api/v1/graph/surface?graph_id=${E2E_GRAPH_ID}`,
  );
  const surface = (await surfaceResp.json()) as {
    nodes: { node_id: string; display: { title: string } }[];
    edges: unknown[];
  };

  if (surface.nodes.length === 0) {
    throw new Error(
      "E2E graph has 0 nodes after seeding — check memory/write pipeline",
    );
  }

  // 5. Verify neighborhood endpoint
  const seedNode = surface.nodes[0]!;
  const nbhdResp = await backendFetch(
    `/api/v1/graph/neighborhood?graph_id=${E2E_GRAPH_ID}&node_id=${seedNode.node_id}&depth=1`,
  );
  if (!nbhdResp.ok) {
    throw new Error(`Neighborhood endpoint failed (${nbhdResp.status})`);
  }

  // 6. Verify events endpoint
  const evResp = await backendFetch(
    `/api/v1/events/latest?graph_id=${E2E_GRAPH_ID}`,
  );
  if (!evResp.ok) {
    throw new Error(`Events/latest endpoint failed (${evResp.status})`);
  }
  const ev = (await evResp.json()) as {
    last_seq: number;
    last_kind: string | null;
  };

  console.log(
    `[e2e-setup] Graph ready: ${surface.nodes.length} nodes, ${
      (surface.edges as unknown[]).length
    } edges, last_seq=${ev.last_seq} ✓`,
  );
  console.log("[e2e-setup] Global setup complete ✓");
}
