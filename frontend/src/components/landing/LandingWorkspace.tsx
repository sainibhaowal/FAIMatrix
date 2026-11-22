"use client";

import { Footer, Hero } from "@/components";
import LandingSectionDeck from "./LandingSectionDeck";
import ProjectStatusBanner from "./ProjectStatusBanner";

export default function LandingWorkspace() {
  return (
    <main className="faim-landing-workspace min-h-screen">
      <section
        id="hero"
        data-faim-section="hero"
        className="min-h-screen scroll-mt-6"
      >
        <div className="px-3 pt-6 sm:px-6 lg:px-10">
          <ProjectStatusBanner />
        </div>
        <Hero />
      </section>

      <LandingSectionDeck />

      <footer id="footer" className="px-3 pb-8 pt-16 sm:px-6 lg:px-10">
        <div className="mx-auto max-w-[1440px]">
          <Footer />
        </div>
      </footer>
    </main>
  );
}
