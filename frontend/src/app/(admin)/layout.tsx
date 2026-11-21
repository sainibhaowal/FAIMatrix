"use client";

/**
 * App Layout
 *
 * Wraps all protected app pages (dashboard, graph, monitor, etc.)
 * with the FaimShell sidebar and AuthGuard.
 */

import { FaimShell } from "@/components/layout/FaimShell";
import { AuthGuard, ErrorBoundary } from "@/components";
import { EmbeddingProviderProvider } from "@/contexts/EmbeddingProviderContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <EmbeddingProviderProvider>
        <FaimShell>
          <ErrorBoundary>{children}</ErrorBoundary>
        </FaimShell>
      </EmbeddingProviderProvider>
    </AuthGuard>
  );
}
