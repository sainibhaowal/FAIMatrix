// src/app/dashboard/layout.tsx
"use client";

import { FaimShell } from "@/components/layout/FaimShell";
import { AuthGuard } from "@/components";
import { ErrorBoundary } from "@/components";

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
