// src/app/dashboard/layout.tsx
'use client';

import { FaimShell } from '@/components/shell/FaimShell';
import AuthGuard from '@/components/AuthGuard';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <FaimShell>{children}</FaimShell>
    </AuthGuard>
  );
}
