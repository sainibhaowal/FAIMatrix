"use client";

/**
 * Marketing Layout
 * 
 * Wraps all public marketing pages (landing, about, contact, etc.)
 * with the Navbar and Footer.
 */

import { Navbar, Footer, CookieConsent } from "@/components";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
      <CookieConsent />
    </div>
  );
}
