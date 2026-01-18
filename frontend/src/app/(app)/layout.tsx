"use client";

/**
 * App Layout
 * 
 * Wraps all protected app pages (dashboard, graph, monitor, etc.)
 * with the FaimShell sidebar and AuthGuard.
 */

import { FaimShell } from "@/components/layout/FaimShell";
import { AuthGuard, ErrorBoundary } from "@/components";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <FaimShell>
        <ErrorBoundary>{children}</ErrorBoundary>
      </FaimShell>
    </AuthGuard>
  );
}
