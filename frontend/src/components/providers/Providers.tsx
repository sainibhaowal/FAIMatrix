"use client";

import { SessionProvider } from "next-auth/react";
import { UserProvider } from "@/contexts/UserContext";
import { ToastProvider } from "@/components/ui/Toast";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <UserProvider>
        <ToastProvider>{children}</ToastProvider>
      </UserProvider>
    </SessionProvider>
  );
}
