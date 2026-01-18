"use client";

/**
 * Marketing Landing Page
 * 
 * Streamlined landing page focusing on FAIM engine concepts.
 */

import {
  Hero,
  Features,
  DemoPreview,
  HowItWorks,
  CTA,
} from "@/components";

export default function LandingPage() {
  return (
    <>
      <Hero />
      <Features />
      <DemoPreview />
      <HowItWorks />
      <CTA />
    </>
  );
}
