"use client";

import { SessionProvider } from "next-auth/react";
import { UserProvider } from "@/contexts/UserContext";
import { ToastProvider } from "@/components/ui/Toast";
import { ScreenReaderAnnouncer } from "@/components/ui/ScreenReaderAnnouncer";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <UserProvider>
        <ToastProvider>
          <ScreenReaderAnnouncer>{children}</ScreenReaderAnnouncer>
        </ToastProvider>
      </UserProvider>
    </SessionProvider>
  );
}
