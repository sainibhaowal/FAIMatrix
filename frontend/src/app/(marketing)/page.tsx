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
      <h1 className="sr-only">FAIM Landing Page Loaded</h1>
      <Hero />
      <Features />
      <DemoPreview />
      <HowItWorks />
      <CTA />
    </>
  );
}
