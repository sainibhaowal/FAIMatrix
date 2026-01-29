"use client";

import { Navbar, Footer, CookieConsent } from "@/components";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Navbar />
      <div className="flex-1">
        {children}
      </div>
      <Footer />
      <CookieConsent />
    </>
  );
}
