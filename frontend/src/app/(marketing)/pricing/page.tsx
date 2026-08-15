"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import Pricing from "@/components/landing/Pricing";

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <nav className="sticky top-0 z-50 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            href="/"
            className="text-sm text-slate-300 hover:text-white flex items-center gap-2 font-mono"
          >
            <ArrowLeft size={14} />
            Back to Home
          </Link>
          <Link
            href="/docs"
            className="text-sm text-slate-300 hover:text-white font-mono"
          >
            Documentation
          </Link>
        </div>
      </nav>
      <Pricing />
    </main>
  );
}
