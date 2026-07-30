"use client";

import { Navbar, Footer } from "@/components";
import { usePathname } from "next/navigation";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isLandingPage = pathname === "/";

  return (
    <>
      {!isLandingPage && <Navbar />}
      <div className="flex-1">{children}</div>
      {!isLandingPage && <Footer />}
    </>
  );
}
