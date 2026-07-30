/**
 * Marketing Landing Page
 *
 * Shows FAIM's real capabilities while keeping the public page compact.
 * The landing content is now grouped into switchable studio sections so the
 * page does not grow endlessly down the screen.
 */

import { SectionTracker } from "@/components";
import LandingWorkspace from "@/components/landing/LandingWorkspace";

export default function LandingPage() {
  return (
    <>
      <h1 className="sr-only">
        FAIMATRIX — Deterministic Memory, Retrieval, and Answer Engine
      </h1>
      <SectionTracker />
      <LandingWorkspace />
    </>
  );
}
