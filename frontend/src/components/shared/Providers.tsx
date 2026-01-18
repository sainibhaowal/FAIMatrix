"use client";

import { SessionProvider } from "next-auth/react";
import { UserProvider } from "@/contexts/UserContext";
import { ToastProvider } from "@/components/ui/Toast";
import { ScreenReaderAnnouncer } from "@/components/ui/ScreenReaderAnnouncer";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider session={{
      user: { name: "Dev User", email: "dev@faimlab.com", id: "dev-user-id" },
      expires: "2099-01-01T00:00:00.000Z",
      graphId: "U:dev-universe"
    } as any}>
      <UserProvider>
        <ToastProvider>
          <ScreenReaderAnnouncer>{children}</ScreenReaderAnnouncer>
        </ToastProvider>
      </UserProvider>
    </SessionProvider>
  );
}
