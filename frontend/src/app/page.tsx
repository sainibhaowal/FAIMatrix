"use client";

/* =============================================================================
FAIMATRIX — LANDING PAGE (Production Edition)
------------------------------------------------------------------------------
A stunning, production-grade landing page showcasing FAIMATRIX features.
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
} from "@/components";
import { CookieConsent } from "@/components";

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
