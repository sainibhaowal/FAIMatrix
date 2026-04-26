"use client";

/**
 * App Layout
 *
 * Wraps all protected app pages (dashboard, graph, monitor, etc.)
 * with the FaimShell sidebar and AuthGuard.
 */

import { FaimShell } from "@/components/layout/FaimShell";
import { AuthGuard, ErrorBoundary } from "@/components";
import { ProviderProvider } from "@/contexts/ProviderContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ProviderProvider>
        <FaimShell>
          <ErrorBoundary>{children}</ErrorBoundary>
        </FaimShell>
      </ProviderProvider>
    </AuthGuard>
  );
}
