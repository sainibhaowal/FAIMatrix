// src/app/dashboard/layout.tsx
// Note: FaimShell is already provided by parent (app)/layout.tsx
// This layout just passes children through

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
