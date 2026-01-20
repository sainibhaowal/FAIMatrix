"use client";

/**
 * AuthGuard - Protects routes requiring authentication
 *
 * NEW FILE - Redirects unauthenticated users to sign-in.
 */

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loader2 } from "lucide-react";

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    // If we've finished checking and there's no session, redirect to login
    if (status === "unauthenticated") {
      router.replace("/auth/login");
    }
  }, [status, router]);

  // Handle loading state
  if (status === "loading") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--bg-deep)] text-[var(--text-primary)]">
        <Loader2 className="animate-spin text-[var(--accent-primary)] mb-4" size={40} />
        <p className="text-sm font-medium tracking-widest uppercase opacity-50">
          Initializing Neural Session...
        </p>
      </div>
    );
  }

  // If unauthenticated, show nothing while redirecting
  if (status === "unauthenticated") {
    return null;
  }

  // If authenticated, render protected children
  return <>{children}</>;
}
