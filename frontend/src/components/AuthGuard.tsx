'use client';

/**
 * AuthGuard - Protects routes requiring authentication
 * 
 * NEW FILE - Redirects unauthenticated users to sign-in.
 */

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    // Only redirect if we're sure the user is unauthenticated
    if (status === 'unauthenticated') {
      router.push('/api/auth/signin?callbackUrl=/dashboard');
    }
  }, [status, router]);

  // Show loading state while checking auth
  if (status === 'loading') {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
          <p className="text-sm text-slate-400">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // If unauthenticated, show nothing (redirect will happen)
  if (status === 'unauthenticated') {
    return null;
  }

  // Authenticated - render children
  return <>{children}</>;
}
