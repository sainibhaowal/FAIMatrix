"use client";

/* =============================================================================
FAIM LAB — LANDING PAGE (Production Edition)
------------------------------------------------------------------------------
A stunning, production-grade landing page showcasing FAIM Lab features.
Includes navigation, hero, features, demo preview, testimonials, pricing, FAQ.
============================================================================= */

import {
  Navbar,
  Hero,
  TrustedBy,
  Features,
  DemoPreview,
  HowItWorks,
  Testimonials,
  Pricing,
  FAQ,
  CTA,
  Footer,
} from "@/components/landing";
import { CookieConsent } from "@/components/common";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-slate-950">
      <Navbar />
      <Hero />
      <TrustedBy />
      <Features />
      <DemoPreview />
      <HowItWorks />
      <Testimonials />
      <Pricing />
      <FAQ />
      <CTA />
      <Footer />
      <CookieConsent />
    </main>
  );
}
