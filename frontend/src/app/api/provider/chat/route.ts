/**
 * LLM Provider Chat Streaming Endpoint
 *
 * POST /api/provider/chat
 * Streams chat completions from an LLM provider (pass-through proxy).
 *
 * Request:
 *   {
 *     providerUrl: string,
 *     apiKey?: string,
 *     model: string,
 *     messages: Array<{ role: string, content: string }>,
 *     systemPrompt?: string
 *   }
 *
 * Response:
 *   text/event-stream (OpenAI-compatible SSE format)
 *   data: { "choices": [{ "delta": { "content": "token" } }] }
 */

export const runtime = "nodejs";

interface ChatRequest {
  providerUrl: string;
  apiKey?: string;
  model: string;
  messages: Array<{ role: string; content: string }>;
  systemPrompt?: string;
}

export async function POST(req: Request): Promise<Response> {
  try {
    const body = (await req.json()) as ChatRequest;
    const { providerUrl, apiKey, model, messages, systemPrompt } = body;

    // Validate required fields
    if (!providerUrl || !model || !Array.isArray(messages)) {
      return new Response(
        JSON.stringify({
          error: "invalid_request",
          message: "providerUrl, model, and messages are required",
        }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Inject system prompt at index 0 if provided
    const allMessages = systemPrompt
      ? [{ role: "system", content: systemPrompt }, ...messages]
      : messages;

    // Make request to upstream provider with 60-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60_000);

    let upstream: globalThis.Response;
    try {
      upstream = await fetch(`${providerUrl}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
        },
        body: JSON.stringify({
          model,
          messages: allMessages,
          stream: true,
        }),
        signal: controller.signal,
      });
    } catch (error: any) {
      clearTimeout(timeoutId);

      console.error("Upstream provider request failed:", error.message);

      return new Response(
        JSON.stringify({
          error: "provider_error",
          message: "Failed to connect to LLM provider",
        }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }

    clearTimeout(timeoutId);

    // Check for error responses from provider
    if (!upstream.ok) {
      const errorBody = await upstream.text();

      if (upstream.status === 401 || upstream.status === 403) {
        return new Response(
          JSON.stringify({
            error: "unauthorized",
            message: "Invalid API key or unauthorized access to provider",
          }),
          { status: 401, headers: { "Content-Type": "application/json" } }
        );
      }

      return new Response(
        JSON.stringify({
          error: "provider_error",
          message: `Provider returned HTTP ${upstream.status}`,
        }),
        { status: upstream.status, headers: { "Content-Type": "application/json" } }
      );
    }

    // Pass through the streaming response directly
    // Do not buffer — pipe the ReadableStream as-is
    return new Response(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error: any) {
    console.error("Chat route error:", error.message);

    return new Response(
      JSON.stringify({
        error: "server_error",
        message: "Internal server error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
