// src/app/dashboard/layout.tsx
import { FaimShell } from '@/components/shell/FaimShell';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <FaimShell>{children}</FaimShell>;
}
