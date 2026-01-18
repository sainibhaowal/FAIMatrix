// src/shared/lib/api-client.ts
/**
 * Shared API Client
 * - Unified health, metrics, and graph operations.
 * - Handles user/graph identity and API headers.
 */

// Configuration
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_FAIM_API_BASE_URL || "/api/v1"
).replace(/\/+$/, "");

export function isRemoteApiBase(): boolean {
  return API_BASE_URL.startsWith("http");
}

export const DEFAULT_GRAPH_ID = (
  process.env.NEXT_PUBLIC_FAIM_DEFAULT_GRAPH_ID || ""
).trim();

// -----------------------------------------------------------------------------
// Identity & Persistence
// -----------------------------------------------------------------------------

function _stableBrowserId(storageKey: string): string {
  if (typeof window === "undefined") return "";
  const prev = window.localStorage.getItem(storageKey);
  if (prev) return prev;
  const next = crypto.randomUUID();
  window.localStorage.setItem(storageKey, next);
  return next;
}

export function getFaimUserId(): string {
  return _stableBrowserId("faim_user_id");
}

export function getFaimApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("faim_api_key");
}

export function getUniverseGraphId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("faim.universe_graph_id");
}

export function getUniverseIdFromStorage(): string | null {
  return getUniverseGraphId();
}

export async function resolveUniverseIdOnce(): Promise<string | null> {
  return getUniverseIdFromStorage();
}

export function resolveGraphId(input?: string): string {
  const raw = (input ?? "").trim();
  const fromStorage = getUniverseGraphId();
  if (raw && raw.startsWith("U:")) return raw;
  if (fromStorage && fromStorage.startsWith("U:")) return fromStorage;
  return DEFAULT_GRAPH_ID || "";
}

// -----------------------------------------------------------------------------
// HTTP Utilities
// -----------------------------------------------------------------------------

export function buildFaimHeaders(init?: HeadersInit): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-FAIM-USER": getFaimUserId(),
    ...init,
  };
}

async function _handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: buildFaimHeaders(),
  });
  return _handleResponse<T>(res);
}

export async function apiPost<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: buildFaimHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return _handleResponse<T>(res);
}
