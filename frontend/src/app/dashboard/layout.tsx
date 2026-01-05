// src/app/dashboard/layout.tsx
"use client";

import { FaimShell } from "@/components/shell/FaimShell";
import AuthGuard from "@/components/AuthGuard";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function DashboardLayout({
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
