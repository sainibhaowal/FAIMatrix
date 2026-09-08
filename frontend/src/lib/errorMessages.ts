export type ApiValidationIssue = {
  type?: string;
  loc?: Array<string | number>;
  msg?: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
};

export function normalizeApiErrorMessage(
  detail: unknown,
  fallback = "Request failed"
): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (!item || typeof item !== "object") return "";
        const issue = item as ApiValidationIssue;
        return issue.msg || "";
      })
      .filter(Boolean);
    if (messages.length > 0) {
      return messages.join(", ");
    }
  }

  if (detail && typeof detail === "object") {
    const maybeDetail = (detail as { detail?: unknown }).detail;
    if (maybeDetail && maybeDetail !== detail) {
      return normalizeApiErrorMessage(maybeDetail, fallback);
    }
    const maybeMsg = (detail as { msg?: unknown }).msg;
    if (typeof maybeMsg === "string" && maybeMsg.trim()) {
      return maybeMsg;
    }
  }

  return fallback;
}
