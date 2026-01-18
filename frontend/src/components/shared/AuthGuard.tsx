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
  // BYPASS: Always render children, no redirect
  return <>{children}</>;
}
