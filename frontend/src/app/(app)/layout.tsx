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
import { EmbeddingProviderProvider } from "@/contexts/EmbeddingProviderContext";
import { ChatProvider } from "@/contexts/ChatContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ProviderProvider>
        <EmbeddingProviderProvider>
          <ChatProvider>
            <FaimShell>
              <ErrorBoundary>{children}</ErrorBoundary>
            </FaimShell>
          </ChatProvider>
        </EmbeddingProviderProvider>
      </ProviderProvider>
    </AuthGuard>
  );
}
