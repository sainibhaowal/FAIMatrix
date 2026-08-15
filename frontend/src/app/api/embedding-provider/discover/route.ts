/**
 * Embedding Provider Discovery Endpoint
 *
 * POST /api/embedding-provider/discover
 * Discovers available models from an embedding provider (local, OpenAI, custom).
 *
 * Request:
 *   { baseUrl: string, apiKey?: string }
 *
 * Response:
 *   Success: { models: string[], dimension?: number }
 *   Error: { error: string, message: string }
 */

import { normalizeBaseUrl } from "@/lib/embeddingProviders";

export const runtime = "nodejs";

/**
 * Check if running in Docker by looking for .dockerenv file
 */
function isRunningInDocker(): boolean {
  if (typeof window !== "undefined") return false;
  try {
    const fs = require("fs");
    return fs.existsSync("/.dockerenv");
  } catch {
    return false;
  }
}

/**
 * Convert localhost to host.docker.internal if in Docker
 */
function resolveLocalhostUrl(url: string): string {
  const inDocker = isRunningInDocker();
  if (!inDocker) return url;

  return url.replace(/^http:\/\/localhost(:\d+)?/, (match) => {
    const port = match.match(/:\d+/)?.[0] || "";
    return `http://host.docker.internal${port}`;
  });
}

interface DiscoverRequest {
  baseUrl: string;
  apiKey?: string;
}

interface DiscoverSuccess {
  models: string[];
  dimension?: number;
}

interface DiscoverError {
  error:
    | "offline"
    | "timeout"
    | "invalid_response"
    | "unauthorized"
    | "unknown";
  message: string;
}

export async function POST(req: Request): Promise<Response> {
  try {
    const body = (await req.json()) as DiscoverRequest;
    const { baseUrl, apiKey } = body;

    if (!baseUrl || typeof baseUrl !== "string") {
      return Response.json(
        { error: "unknown", message: "baseUrl is required" } as DiscoverError,
        { status: 400 },
      );
    }

    const normalizedUrl = normalizeBaseUrl(baseUrl);
    const resolvedUrl = resolveLocalhostUrl(normalizedUrl);
    const modelsUrl = `${resolvedUrl}/models`;

    console.log(`[Embedding Provider Discovery] Normalized URL: ${normalizedUrl}`);
    if (resolvedUrl !== normalizedUrl) {
      console.log(`[Embedding Provider Discovery] Docker resolved to: ${resolvedUrl}`);
    }
    console.log(`[Embedding Provider Discovery] Fetching models from: ${modelsUrl}`);

    // Fetch models with 8-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    let response: globalThis.Response;
    try {
      response = await fetch(modelsUrl, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
        },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (error: any) {
      clearTimeout(timeoutId);
      console.error(`[Embedding Provider Discovery] Fetch error:`, {
        message: error.message,
        code: error.code,
      });

      if (error.name === "AbortError") {
        return Response.json(
          {
            error: "timeout",
            message: `Timeout after 8 seconds trying to reach ${modelsUrl}. Is the server running?`,
          } as DiscoverError,
          { status: 408 },
        );
      }

      if (
        error.code === "ECONNREFUSED" ||
        error.message?.includes("ECONNREFUSED")
      ) {
        return Response.json(
          {
            error: "offline",
            message: `Connection refused: ${modelsUrl}. Provider might not be running. Check: (1) Is the provider server started? (2) Correct port? (3) Is CORS enabled?`,
          } as DiscoverError,
          { status: 503 },
        );
      }

      if (error.code === "ENOTFOUND" || error.message?.includes("ENOTFOUND")) {
        return Response.json(
          {
            error: "offline",
            message: `Host not found: ${modelsUrl}. Check the URL is correct.`,
          } as DiscoverError,
          { status: 503 },
        );
      }

      return Response.json(
        {
          error: "unknown",
          message: `Network error: ${error.message}`,
        } as DiscoverError,
        { status: 500 },
      );
    }

    // Check response status
    if (!response.ok) {
      console.error(
        `[Embedding Provider Discovery] HTTP ${response.status} from ${modelsUrl}`,
      );
      const responseText = await response.text();
      console.error(
        `[Embedding Provider Discovery] Response:`,
        responseText.slice(0, 300),
      );

      if (response.status === 401 || response.status === 403) {
        return Response.json(
          {
            error: "unauthorized",
            message: "Invalid API key or unauthorized access",
          } as DiscoverError,
          { status: 401 },
        );
      }

      return Response.json(
        {
          error: "invalid_response",
          message: `Server returned HTTP ${response.status}. Expected models list.`,
        } as DiscoverError,
        { status: response.status },
      );
    }

    // Parse response
    let data: any;
    try {
      data = await response.json();
      console.log(
        `[Embedding Provider Discovery] Got response:`,
        JSON.stringify(data).slice(0, 200),
      );
    } catch {
      return Response.json(
        {
          error: "invalid_response",
          message:
            "Server returned invalid JSON. Expected OpenAI-compatible models response.",
        } as DiscoverError,
        { status: 502 },
      );
    }

    // Extract models - handle both OpenAI format and plain array
    const models = Array.isArray(data.data)
      ? data.data.map((m: any) => m.id || m.model || m.name).filter(Boolean)
      : Array.isArray(data)
        ? data
            .map((m: any) =>
              typeof m === "string" ? m : m.id || m.model || m.name,
            )
            .filter(Boolean)
        : [];

    console.log(`[Embedding Provider Discovery] Found ${models.length} models:`, models);

    if (models.length === 0) {
      return Response.json(
        {
          error: "invalid_response",
          message: `No models found. Server returned: ${JSON.stringify(data).slice(0, 100)}`,
        } as DiscoverError,
        { status: 502 },
      );
    }

    // Try to detect dimension from model name or use default
    let dimension = 1024;
    if (models.length > 0) {
      const modelName = models[0].toLowerCase();
      if (modelName.includes("bge-m3")) dimension = 1024;
      else if (modelName.includes("text-embedding-3-large")) dimension = 3072;
      else if (modelName.includes("text-embedding-3-small")) dimension = 1536;
      else if (modelName.includes("text-embedding-ada-002")) dimension = 1536;
    }

    return Response.json({ models, dimension } as DiscoverSuccess, { status: 200 });
  } catch (error: any) {
    console.error(`[Embedding Provider Discovery] Unexpected error:`, error);
    return Response.json(
      {
        error: "unknown",
        message: `Server error: ${error.message}`,
      } as DiscoverError,
      { status: 500 },
    );
  }
}