"use client";

import { useEffect, useState } from "react";

import { Footer, Hero } from "@/components";
import LandingSectionDeck from "./LandingSectionDeck";
import ProjectStatusBanner from "./ProjectStatusBanner";

const VIEWS = new Set(["hero", "core", "platform", "proof", "ops", "scale", "footer"]);

function viewFromLocation() {
  const value = window.location.hash.slice(1).split("/")[0];
  return VIEWS.has(value) ? value : "hero";
}

export default function LandingWorkspace() {
  const [view, setView] = useState("hero");

  useEffect(() => {
    const syncView = () => setView(viewFromLocation());
    syncView();
    window.addEventListener("hashchange", syncView);
    return () => window.removeEventListener("hashchange", syncView);
  }, []);

  return (
    <main data-faim-view={view} className="faim-landing-workspace min-h-screen">
      {view === "hero" && (
        <div id="hero" className="min-h-screen">
          <div className="px-3 pt-6 sm:px-6 lg:px-10">
            <ProjectStatusBanner />
          </div>
          <Hero />
        </div>
      )}
      {VIEWS.has(view) && !["hero", "footer"].includes(view) && <LandingSectionDeck />}
      {view === "footer" && (
        <div className="min-h-screen px-3 pb-6 pt-24 sm:px-6 lg:px-10">
          <div className="mx-auto flex min-h-[calc(100svh-7rem)] max-w-[1480px] items-end">
            <Footer />
          </div>
        </div>
      )}
    </main>
  );
}
