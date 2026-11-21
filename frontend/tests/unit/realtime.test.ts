import { afterEach, describe, expect, it, vi } from "vitest";

import { startFaimStream } from "@/lib/realtime";

const waitForStream = () => new Promise((resolve) => setTimeout(resolve, 0));

afterEach(() => {
  vi.restoreAllMocks();
});

describe("FAIM realtime stream", () => {
  it("sends the universe URL and dispatches every supported event type", async () => {
    const contract = {
      universe: { graph_id: "U:resolved", label: "Universe" },
      galaxies: [],
      policy: {
        graph_id_is_user_universe: true,
        frontend_never_prompts_for_graph_id: true,
        galaxies_are_clusters_not_graphs: true,
      },
    };
    const payload = [
      `:comment\r\nid:1\r\nevent:contract\r\ndata:${JSON.stringify(contract)}\r\n\r\n`,
      `event:fig_delta\ndata:${JSON.stringify({ graph_id: "U:resolved", ts: 1, delta: { kind: "add" } })}\n\n`,
      `event:toast\ndata:${JSON.stringify({ graph_id: "U:resolved", ts: 1, level: "info", message: "ok" })}\n\n`,
      `event:metrics\ndata:${JSON.stringify({ nodes: 2 })}\n\n`,
      `event:bench_point\ndata:${JSON.stringify({ timestamp: "now", nodes: 2, cr: 1, redundancy: 0, drift: 0 })}\n\n`,
      `event:used_nodes\ndata:${JSON.stringify([{ id: "n1", score: 0.9 }])}\n\n`,
      "event:ping\ndata:\n\n",
      "event:unknown\ndata:{}\n\n",
    ].join("");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(payload));
            controller.close();
          },
        }),
        { headers: { "content-type": "text/event-stream" } },
      ),
    );
    const handlers = {
      onContract: vi.fn(),
      onFigDelta: vi.fn(),
      onToast: vi.fn(),
      onMetrics: vi.fn(),
      onBenchPoint: vi.fn(),
      onUsedNodes: vi.fn(),
      onPing: vi.fn(),
      onRaw: vi.fn(),
      onError: vi.fn(),
    };

    const stop = startFaimStream("U:provided", handlers, "token");
    await waitForStream();
    await waitForStream();
    stop();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/stream?graph_id=U%3Aprovided",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      headers: expect.objectContaining({ Authorization: "Bearer token" }),
    });
    expect(handlers.onContract).toHaveBeenCalledWith(contract);
    expect(handlers.onFigDelta).toHaveBeenCalledOnce();
    expect(handlers.onToast).toHaveBeenCalledOnce();
    expect(handlers.onMetrics).toHaveBeenCalledOnce();
    expect(handlers.onBenchPoint).toHaveBeenCalledOnce();
    expect(handlers.onUsedNodes).toHaveBeenCalledWith([
      { id: "n1", score: 0.9 },
    ]);
    expect(handlers.onPing).toHaveBeenCalledWith(
      expect.objectContaining({ graph_id: "U:resolved" }),
    );
    expect(handlers.onRaw.mock.calls.length).toBeGreaterThanOrEqual(7);
    expect(handlers.onError).not.toHaveBeenCalled();
  });

  it("reports authentication, body, and transport failures without throwing", async () => {
    const onError = vi.fn();
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("", { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 200 }))
      .mockRejectedValueOnce(new Error("offline"));

    startFaimStream(null, { onError });
    await waitForStream();
    startFaimStream(null, { onError });
    await waitForStream();
    startFaimStream(null, { onError });
    await waitForStream();

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(onError).toHaveBeenCalledTimes(3);
    expect(onError.mock.calls[0]?.[0]).toMatchObject({
      message: "SSE connect failed: missing API key",
    });
    expect(onError.mock.calls[1]?.[0]).toMatchObject({
      message: "SSE connect failed: no response body",
    });
    expect(onError.mock.calls[2]?.[0]).toMatchObject({ message: "offline" });
  });
});
