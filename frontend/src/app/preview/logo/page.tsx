'use client';

import React from 'react';
import Logo from '@/components/brand/Logo';

export default function Page() {
  return (
    <div className="min-h-screen bg-[#050b14] text-white flex flex-col items-center justify-center gap-8 p-10">
      <div className="text-center">
        <div className="text-xl font-semibold">Logo.tsx (UI component)</div>
        <div className="text-white/60 text-sm">small / medium / large</div>
      </div>

      <div className="flex items-center gap-10">
        <div className="flex flex-col items-center gap-2">
          <Logo size="small" />
          <div className="text-xs text-white/60">small</div>
        </div>

        <div className="flex flex-col items-center gap-2">
          <Logo size="medium" />
          <div className="text-xs text-white/60">medium</div>
        </div>

        <div className="flex flex-col items-center gap-2">
          <Logo size="large" />
          <div className="text-xs text-white/60">large</div>
        </div>
      </div>
    </div>
  );
}
