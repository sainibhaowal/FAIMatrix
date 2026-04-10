/**
 * Provider Discovery Endpoint
 *
 * POST /api/provider/discover
 * Discovers available models from an LLM provider (local or cloud).
 *
 * Request:
 *   { baseUrl: string, apiKey?: string }
 *
 * Response:
 *   Success: { models: string[] }
 *   Error: { error: string, message: string }
 */

import { normalizeBaseUrl } from "@/lib/providers";

export const runtime = "nodejs";

interface DiscoverRequest {
  baseUrl: string;
  apiKey?: string;
}

interface DiscoverSuccess {
  models: string[];
}

interface DiscoverError {
  error: "offline" | "timeout" | "invalid_response" | "unauthorized" | "unknown";
  message: string;
}

export async function POST(req: Request): Promise<Response> {
  try {
    const body = (await req.json()) as DiscoverRequest;
    const { baseUrl, apiKey } = body;

    if (!baseUrl || typeof baseUrl !== "string") {
      return Response.json(
        { error: "unknown", message: "baseUrl is required" } as DiscoverError,
        { status: 400 }
      );
    }

    const normalizedUrl = normalizeBaseUrl(baseUrl);

    // GET {baseUrl}/models with 8-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    let response: globalThis.Response;
    try {
      response = await fetch(`${normalizedUrl}/models`, {
        method: "GET",
        headers: {
          ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
        },
        signal: controller.signal,
      });
    } catch (error: any) {
      clearTimeout(timeoutId);

      // Classify the error
      if (error.name === "AbortError") {
        return Response.json(
          { error: "timeout", message: "Provider did not respond within 8 seconds" } as DiscoverError,
          { status: 408 }
        );
      }

      if (error.code === "ECONNREFUSED" || error.message?.includes("ECONNREFUSED")) {
        return Response.json(
          {
            error: "offline",
            message: "Could not connect to provider. Is it running? (ECONNREFUSED)",
          } as DiscoverError,
          { status: 503 }
        );
      }

      if (error.code === "ENOTFOUND" || error.message?.includes("ENOTFOUND")) {
        return Response.json(
          { error: "offline", message: "Provider host not found (invalid URL)" } as DiscoverError,
          { status: 503 }
        );
      }

      return Response.json(
        { error: "unknown", message: `Network error: ${error.message}` } as DiscoverError,
        { status: 500 }
      );
    } finally {
      clearTimeout(timeoutId);
    }

    // Handle non-200 responses
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        return Response.json(
          { error: "unauthorized", message: "Invalid API key or unauthorized access" } as DiscoverError,
          { status: 401 }
        );
      }

      return Response.json(
        { error: "unknown", message: `HTTP ${response.status}: ${response.statusText}` } as DiscoverError,
        { status: response.status }
      );
    }

    // Parse response
    let data: any;
    try {
      data = await response.json();
    } catch {
      return Response.json(
        { error: "invalid_response", message: "Provider returned invalid JSON" } as DiscoverError,
        { status: 502 }
      );
    }

    // Extract model IDs from response
    // OpenAI-compatible format: { data: [{ id: "...", ... }] }
    const models = Array.isArray(data.data)
      ? data.data.map((m: any) => m.id || m.model || m.name).filter(Boolean)
      : Array.isArray(data)
      ? data
      : [];

    if (models.length === 0) {
      return Response.json(
        {
          error: "invalid_response",
          message: "Provider returned no models. Response format may not be OpenAI-compatible.",
        } as DiscoverError,
        { status: 502 }
      );
    }

    return Response.json({ models } as DiscoverSuccess, { status: 200 });
  } catch (error: any) {
    return Response.json(
      { error: "unknown", message: `Server error: ${error.message}` } as DiscoverError,
      { status: 500 }
    );
  }
}
