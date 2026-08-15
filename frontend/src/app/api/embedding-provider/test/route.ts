/**
 * Embedding Provider Test Endpoint
 *
 * POST /api/embedding-provider/test
 * Tests an embedding provider by encoding a test text.
 *
 * Request:
 *   { baseUrl: string, apiKey?: string, model?: string, dimension?: number, testText?: string }
 *
 * Response:
 *   Success: { success: true, dimension: number, latency_ms: number }
 *   Error: { success: false, message: string }
 */

import { normalizeBaseUrl } from "@/lib/embeddingProviders";

export const runtime = "nodejs";

function isRunningInDocker(): boolean {
  if (typeof window !== "undefined") return false;
  try {
    const fs = require("fs");
    return fs.existsSync("/.dockerenv");
  } catch {
    return false;
  }
}

function resolveLocalhostUrl(url: string): string {
  const inDocker = isRunningInDocker();
  if (!inDocker) return url;

  return url.replace(/^http:\/\/localhost(:\d+)?/, (match) => {
    const port = match.match(/:\d+/)?.[0] || "";
    return `http://host.docker.internal${port}`;
  });
}

interface TestRequest {
  baseUrl: string;
  apiKey?: string;
  model?: string;
  dimension?: number;
  testText?: string;
}

interface TestSuccess {
  success: true;
  dimension: number;
  latency_ms: number;
}

interface TestError {
  success: false;
  message: string;
}

export async function POST(req: Request): Promise<Response> {
  try {
    const body = (await req.json()) as TestRequest;
    const { baseUrl, apiKey, model, dimension: expectedDimension, testText = "FAIM embedding test" } = body;

    if (!baseUrl || typeof baseUrl !== "string") {
      return Response.json(
        { success: false, message: "baseUrl is required" } as TestError,
        { status: 400 },
      );
    }

    const normalizedUrl = normalizeBaseUrl(baseUrl);
    const resolvedUrl = resolveLocalhostUrl(normalizedUrl);
    const embeddingsUrl = `${resolvedUrl}/embeddings`;

    console.log(`[Embedding Provider Test] Normalized URL: ${normalizedUrl}`);
    if (resolvedUrl !== normalizedUrl) {
      console.log(`[Embedding Provider Test] Docker resolved to: ${resolvedUrl}`);
    }
    console.log(`[Embedding Provider Test] Testing embeddings at: ${embeddingsUrl}`);

    // Test with 10-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const startTime = performance.now();

    let response: globalThis.Response;
    try {
      response = await fetch(embeddingsUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
        },
        body: JSON.stringify({
          model: model || "text-embedding-3-small",
          input: testText,
        }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (error: any) {
      clearTimeout(timeoutId);
      console.error(`[Embedding Provider Test] Fetch error:`, {
        message: error.message,
        code: error.code,
      });

      if (error.name === "AbortError") {
        return Response.json(
          {
            success: false,
            message: `Timeout after 10 seconds trying to reach ${embeddingsUrl}. Is the server running?`,
          } as TestError,
          { status: 408 },
        );
      }

      if (
        error.code === "ECONNREFUSED" ||
        error.message?.includes("ECONNREFUSED")
      ) {
        return Response.json(
          {
            success: false,
            message: `Connection refused: ${embeddingsUrl}. Provider might not be running.`,
          } as TestError,
          { status: 503 },
        );
      }

      if (error.code === "ENOTFOUND" || error.message?.includes("ENOTFOUND")) {
        return Response.json(
          {
            success: false,
            message: `Host not found: ${embeddingsUrl}. Check the URL is correct.`,
          } as TestError,
          { status: 503 },
        );
      }

      return Response.json(
        {
          success: false,
          message: `Network error: ${error.message}`,
        } as TestError,
        { status: 500 },
      );
    }

    const latencyMs = Math.round(performance.now() - startTime);

    // Check response status
    if (!response.ok) {
      console.error(
        `[Embedding Provider Test] HTTP ${response.status} from ${embeddingsUrl}`,
      );
      const responseText = await response.text();
      console.error(
        `[Embedding Provider Test] Response:`,
        responseText.slice(0, 300),
      );

      if (response.status === 401 || response.status === 403) {
        return Response.json(
          {
            success: false,
            message: "Invalid API key or unauthorized access",
          } as TestError,
          { status: 401 },
        );
      }

      return Response.json(
        {
          success: false,
          message: `Server returned HTTP ${response.status}.`,
        } as TestError,
        { status: response.status },
      );
    }

    // Parse response
    let data: any;
    try {
      data = await response.json();
    } catch {
      return Response.json(
        {
          success: false,
          message: "Server returned invalid JSON.",
        } as TestError,
        { status: 502 },
      );
    }

    // Extract embedding and verify dimension
    let embedding: number[] | null = null;
    if (Array.isArray(data.data) && data.data.length > 0) {
      embedding = data.data[0].embedding;
    } else if (Array.isArray(data) && data.length > 0) {
      embedding = data[0].embedding;
    }

    if (!embedding || !Array.isArray(embedding)) {
      return Response.json(
        {
          success: false,
          message: "No embedding found in response.",
        } as TestError,
        { status: 502 },
      );
    }

    const actualDimension = embedding.length;
    const expectedDim = expectedDimension || 1024;

    if (actualDimension !== expectedDim) {
      console.warn(`[Embedding Provider Test] Dimension mismatch: expected ${expectedDim}, got ${actualDimension}`);
    }

    return Response.json(
      {
        success: true,
        dimension: actualDimension,
        latency_ms: latencyMs,
      } as TestSuccess,
      { status: 200 },
    );
  } catch (error: any) {
    console.error(`[Embedding Provider Test] Unexpected error:`, error);
    return Response.json(
      {
        success: false,
        message: `Server error: ${error.message}`,
      } as TestError,
      { status: 500 },
    );
  }
}