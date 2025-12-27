'use client';

/* =============================================================================
FAIM LAB — HOME ROUTE (Golden Edition)
------------------------------------------------------------------------------
Purpose:
- Keep the root route ("/") clean and deterministic.
- Avoid duplicating Dashboard/Monitor logic here.
- Production behavior: boot users into the main dashboard.

Safety / Non-Goals:
- Do NOT fetch metrics here.
- Do NOT duplicate /dashboard UI here.
- Do NOT introduce new backend dependencies.
============================================================================= */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/* -----------------------------------------------------------------------------
HomePage
- Minimal shell: instant redirect to "/dashboard"
- Shows a small loading state for very slow clients.
----------------------------------------------------------------------------- */
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard');
  }, [router]);

  return (
    <main className="min-h-[60vh] flex items-center justify-center">
      <section className="rounded-2xl border border-slate-800 bg-slate-950/45 px-5 py-4">
        <p className="text-[10px] uppercase tracking-[0.18em] text-cyan-300/70">
          FAIM Lab
        </p>
        <h1 className="mt-1 text-sm font-semibold text-slate-100">
          Loading…
        </h1>
        <p className="mt-1 text-xs text-slate-400">
          Redirecting to Dashboard
        </p>
      </section>
    </main>
  );
}
