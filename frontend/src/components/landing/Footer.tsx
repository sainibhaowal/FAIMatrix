"use client";

import Link from "next/link";
import Image from "next/image";

const footerLinks = {
  product: [
    { label: "Core", href: "#core" },
    { label: "Proof", href: "#proof" },
    { label: "Documentation", href: "/docs" },
  ],
  company: [
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
  ],
  legal: [
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
  ],
};

export default function Footer() {
  return (
    <footer className="faim-public-footer w-full border-t border-white/[0.1] bg-[#060a13] px-5 py-10 sm:px-8 lg:px-12">
      <div className="mx-auto max-w-[1280px]">
        <div className="grid gap-10 border-b border-white/[0.08] pb-10 md:grid-cols-[1.4fr_repeat(3,minmax(0,0.7fr))]">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-3">
              <Image src="/logo-coded.svg" alt="FAIMATRIX" width={38} height={38} className="h-9 w-9 rounded-xl border border-cyan-300/25 bg-cyan-300/[0.04] p-1" />
              <div>
                <p className="text-sm font-semibold tracking-[0.18em] text-white">FAIMATRIX</p>
                <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">Public system atlas</p>
              </div>
            </div>
            <p className="mt-5 max-w-xs text-sm leading-6 text-slate-400">
              Transform your knowledge into intelligence with graph-native, deterministic memory.
            </p>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-200">Product</h4>
            <ul className="mt-4 space-y-2.5">
              {footerLinks.product.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-400 transition-colors hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-200">Company</h4>
            <ul className="mt-4 space-y-2.5">
              {footerLinks.company.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-400 transition-colors hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-200">Legal</h4>
            <ul className="mt-4 space-y-2.5">
              {footerLinks.legal.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-400 transition-colors hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="flex flex-col items-start justify-between gap-3 pt-5 text-xs sm:flex-row sm:items-center">
          <p className="text-slate-500">
            © 2026 FAIMATRIX. All rights reserved.
          </p>
          <div className="flex items-center gap-2 text-slate-500">
            <span>Built with</span>
            <span className="text-red-400">♥</span>
            <span>by</span>
            <span className="text-cyan-400 font-medium">Ravinder Singh</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
